-- =====================================================================
-- QUERY_REPORTE_RETENCION_CONVENIOS_TERADATA.SQL
-- Migrado y optimizado para Teradata (TDT).
--
-- Características principales de esta versión:
-- 1. Unificación en una sola consulta estructurada usando tablas volátiles.
-- 2. Inserción explícita por columnas en el orden exacto de REPORTE_RETENCION_CONVENIOS.
-- 3. Uso de TO_CHAR y EXTRACT para fechas compatible con Teradata.
-- 4. Eliminación de sentencias UPDATE secuenciales que consumen excesiva I/O.
-- 5. Parámetro dinámico {PERIODO} compatible con el orquestador.
-- =====================================================================

-- -------------------------------------------------------------
-- PASO 1: LIMPIEZA Y CRUCES DE INFORMACIÓN (Tabla Volátil)
-- -------------------------------------------------------------
CREATE VOLATILE TABLE VT_RETENCION_STEP1 AS (
    SELECT 
        s.RET_CONVENIOS_COBRANZAS,
        s.RET_CONVENIOS_COMPRA_DE_DEUDA,
        s.RET_CONVENIOS_CONSULTAS_GENERALES,
        s.RET_CONVENIOS_DEVOLUCION_CUOTAS,
        s.RET_CONVENIOS_INFO_CAMPANAS,
        s.RET_CONVENIOS_MAYOR_IMPORTE,
        s.RET_CONVENIOS_MEDIOS_PROPIOS,
        s.RET_CONVENIOS_OFF_MAVERICK,
        s.RET_CONVENIOS_PEDIDOS_RECLAMOS,
        s.RET_CONVENIOS_RET_AMPLIACION,
        s.RET_CONVENIOS_RET_BAJA_TASA,
        s.RET_CONVENIOS_SOL_CANCELACION,
        s.RET_CONVENIOS_SOL_CRONOGRAMA,
        s.RET_CONVENIOS_SOL_DEUDA_TOTAL,
        s.RET_CONVENIOS_SOL_TASA_INTERES,
        s.RET_CONVENIOS_TASA_INTERES,
        s.RET_CONVENIOS_PLAZA_VEA,
        s.RET_CONVENIOS_UTP,
        s.TiempoLlamada,
        s.TIEMPO_SILENCIO,
        s.DniCliente,
        s.RegistroAgente,
        s.FechaLlamada,
        s.NUM_TELEF,
        s.DNIS,
        s.conID,
        s.Tipificacion,
        s.IDContacto,
        s.cti_BT_Segmento,
        s.Area,

        -- Período dinámico basado en la fecha de la llamada
        TO_CHAR(s.FechaLlamada, 'YYYYMM') AS Periodo,
        
        -- Cálculo de duraciones en formato de fracción de día
        CAST(s.TIEMPO_SILENCIO AS FLOAT) / (24.0 * 3600.0) AS TIEMPO_SILENCIO_HH_MM_SS,
        CAST(s.TiempoLlamada AS FLOAT) / (24.0 * 3600.0) AS TIEMPO_LLAMADA_HH_MM_SS,
        CAST((s.TiempoLlamada - s.TIEMPO_SILENCIO) AS FLOAT) / (24.0 * 3600.0) AS TIEMPO_HABLADO_HH_MM_SS,
        
        -- Determinación del flujo de llamada según el Área
        CASE  
            WHEN s.Area IN ('A_BE_CONVENIOS', 'C_CONVENIOS', 'C_CONVENIOS_PRV') THEN 'Entrante'
            WHEN s.Area IN ('TLV_CON_RET') THEN 'Saliente'
            ELSE NULL 
        END AS FLUJO,
        m.NOM_EJECUTIVO AS Empleado,
        
        -- Información de la vista de retención V_CNV_VISTA_RETENCION_BT
        b.SEGMENTO AS SEGMENTO,
        b.FAMILIA AS FAMILIA,
        b.MOTIVO_DSC AS MOTIVO,
        b.respuesta_val AS RESPUESTA,
        b.GESTION AS GESTION,
        b.PLAZA_TIENDA_CANCELACION_DSC AS PLAZA,
        
        -- Inicialización de banderas de retención
        CASE WHEN b.TIPO_RETEN = 'TASA' THEN 1 ELSE 0 END AS AC_TASA,
        CASE WHEN b.TIPO_RETEN = 'VENTA' THEN 1 ELSE 0 END AS AC_AMPLIACION,
        CASE WHEN b.TIPO_RETEN IN ('TASA', 'VENTA') THEN 1 ELSE 0 END AS TOTAL_RETENCIONES,
        CASE WHEN b.CAMP_RETEN = 1 THEN 1 ELSE NULL END AS CLIENTE_GESTIONABLE,
        CASE WHEN b.CANCELACION_FLG = 1 THEN 1 ELSE NULL END AS CANCELACIONES_EFECTIVAS,
        CASE WHEN b.FLG_XTASA = 1 THEN 1 ELSE NULL END AS RETENCION_TASA,
        CASE WHEN b.FLG_XMONTO = 1 THEN 1 ELSE NULL END AS RETENCION_MONTO
        
    FROM DLAB_GEC.DATA_RET_CONVENIOS_SA s
    
    -- Cruce con EJECUTIVOS para obtener el nombre del empleado
    LEFT JOIN (
        SELECT DISTINCT PERIODO, REG_EJECUTIVO, NOM_EJECUTIVO 
        FROM DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED
    ) m ON s.RegistroAgente = m.REG_EJECUTIVO AND TO_CHAR(s.FechaLlamada, 'YYYYMM') = m.PERIODO
    
    -- Cruce con la vista histórica de retención
    LEFT JOIN E_DW_VIEWS_DLAB.V_CNV_VISTA_RETENCION_BT b
        ON s.DniCliente = b.nro_documento
        AND s.RegistroAgente = b.primer_registro
        AND TO_CHAR(s.FechaLlamada, 'YYYYMM') = b.mes

    WHERE TO_CHAR(s.FechaLlamada, 'YYYYMM') = '{PERIODO}'
) WITH DATA PRIMARY INDEX (conID) ON COMMIT PRESERVE ROWS;

-- -------------------------------------------------------------
-- PASO 2: CÁLCULOS CONDICIONALES FINALES (Tabla Volátil)
-- -------------------------------------------------------------
CREATE VOLATILE TABLE VT_RETENCION_FINAL AS (
    SELECT
        t.RET_CONVENIOS_COBRANZAS,
        t.RET_CONVENIOS_COMPRA_DE_DEUDA,
        t.RET_CONVENIOS_CONSULTAS_GENERALES,
        t.RET_CONVENIOS_DEVOLUCION_CUOTAS,
        t.RET_CONVENIOS_INFO_CAMPANAS,
        t.RET_CONVENIOS_MAYOR_IMPORTE,
        t.RET_CONVENIOS_MEDIOS_PROPIOS,
        t.RET_CONVENIOS_OFF_MAVERICK,
        t.RET_CONVENIOS_PEDIDOS_RECLAMOS,
        t.RET_CONVENIOS_RET_AMPLIACION,
        t.RET_CONVENIOS_RET_BAJA_TASA,
        t.RET_CONVENIOS_SOL_CANCELACION,
        t.RET_CONVENIOS_SOL_CRONOGRAMA,
        t.RET_CONVENIOS_SOL_DEUDA_TOTAL,
        t.RET_CONVENIOS_SOL_TASA_INTERES,
        t.RET_CONVENIOS_TASA_INTERES,
        t.RET_CONVENIOS_PLAZA_VEA,
        t.RET_CONVENIOS_UTP,
        t.TiempoLlamada,
        t.TIEMPO_SILENCIO,
        t.DniCliente,
        t.RegistroAgente,
        t.FechaLlamada,
        t.NUM_TELEF,
        t.DNIS,
        t.conID,
        t.Tipificacion,
        t.IDContacto,
        t.cti_BT_Segmento,
        t.Area,
        t.Periodo,
        t.TIEMPO_SILENCIO_HH_MM_SS,
        t.TIEMPO_LLAMADA_HH_MM_SS,
        t.TIEMPO_HABLADO_HH_MM_SS,
        t.FLUJO,
        t.Empleado,
        t.SEGMENTO,
        t.FAMILIA,
        t.MOTIVO,
        t.RESPUESTA,
        t.GESTION,
        t.PLAZA,
        t.AC_TASA,
        t.AC_AMPLIACION,
        t.TOTAL_RETENCIONES,
        t.CLIENTE_GESTIONABLE,
        t.CANCELACIONES_EFECTIVAS,
        t.RETENCION_TASA,
        t.RETENCION_MONTO,

        -- Clasificación de llamada según rango de duración
        CASE  
            WHEN t.TiempoLlamada BETWEEN 0 AND 180 THEN 'MENORES 3 MIN'
            WHEN t.TiempoLlamada BETWEEN 180 AND 360 THEN 'ENTRE 3 MIN Y 6 MIN'
            WHEN t.TiempoLlamada BETWEEN 360 AND 600 THEN 'ENTRE 6 MIN Y 10 MIN'
            WHEN t.TiempoLlamada > 600 THEN 'MAYORES A 10 MIN'
            ELSE '-' 
        END AS RANGO_LLAMADA,
        
        -- Duración y silencios específicos para gestiones de retención
        CASE WHEN (t.RET_CONVENIOS_SOL_CANCELACION = 1 OR t.RET_CONVENIOS_SOL_CRONOGRAMA = 1 OR t.RET_CONVENIOS_SOL_DEUDA_TOTAL = 1 OR t.RET_CONVENIOS_SOL_TASA_INTERES = 1) THEN t.TIEMPO_LLAMADA_HH_MM_SS ELSE NULL END AS TiempoLlamada_retenciones,
        CASE WHEN (t.RET_CONVENIOS_SOL_CANCELACION = 1 OR t.RET_CONVENIOS_SOL_CRONOGRAMA = 1 OR t.RET_CONVENIOS_SOL_DEUDA_TOTAL = 1 OR t.RET_CONVENIOS_SOL_TASA_INTERES = 1) THEN t.TIEMPO_SILENCIO_HH_MM_SS ELSE NULL END AS Tiemposilencio_retenciones,
        CASE WHEN (t.RET_CONVENIOS_SOL_CANCELACION = 1 OR t.RET_CONVENIOS_SOL_CRONOGRAMA = 1 OR t.RET_CONVENIOS_SOL_DEUDA_TOTAL = 1 OR t.RET_CONVENIOS_SOL_TASA_INTERES = 1) THEN t.TIEMPO_HABLADO_HH_MM_SS ELSE NULL END AS Tiempohablado_retenciones,
        
        -- Métrica agrupada de motivos de anulación
        t.RET_CONVENIOS_COMPRA_DE_DEUDA + t.RET_CONVENIOS_TASA_INTERES + t.RET_CONVENIOS_MAYOR_IMPORTE + t.RET_CONVENIOS_MEDIOS_PROPIOS AS TOTAL_MOTIVOS_ANULACION,
        
        -- Duración y silencios específicos para ofrecimiento
        CASE WHEN (t.RET_CONVENIOS_RET_AMPLIACION = 1 OR t.RET_CONVENIOS_RET_BAJA_TASA = 1) THEN t.TIEMPO_LLAMADA_HH_MM_SS ELSE NULL END AS TiempoLlamada_ofrecimiento,
        CASE WHEN (t.RET_CONVENIOS_RET_AMPLIACION = 1 OR t.RET_CONVENIOS_RET_BAJA_TASA = 1) THEN t.TIEMPO_SILENCIO_HH_MM_SS ELSE NULL END AS Tiemposilencio_ofrecimiento,
        CASE WHEN (t.RET_CONVENIOS_RET_AMPLIACION = 1 OR t.RET_CONVENIOS_RET_BAJA_TASA = 1) THEN t.TIEMPO_HABLADO_HH_MM_SS ELSE NULL END AS Tiempohablado_ofrecimiento,
        
        -- Duración y silencios específicos para post-venta
        CASE WHEN (t.RET_CONVENIOS_INFO_CAMPANAS = 1 OR t.RET_CONVENIOS_CONSULTAS_GENERALES = 1 OR t.RET_CONVENIOS_DEVOLUCION_CUOTAS = 1 OR t.RET_CONVENIOS_COBRANZAS = 1 OR t.RET_CONVENIOS_PEDIDOS_RECLAMOS = 1) THEN t.TIEMPO_LLAMADA_HH_MM_SS ELSE NULL END AS TiempoLlamada_POST_VENTA,
        CASE WHEN (t.RET_CONVENIOS_INFO_CAMPANAS = 1 OR t.RET_CONVENIOS_CONSULTAS_GENERALES = 1 OR t.RET_CONVENIOS_DEVOLUCION_CUOTAS = 1 OR t.RET_CONVENIOS_COBRANZAS = 1 OR t.RET_CONVENIOS_PEDIDOS_RECLAMOS = 1) THEN t.TIEMPO_SILENCIO_HH_MM_SS ELSE NULL END AS Tiemposilencio_POST_VENTA,
        CASE WHEN (t.RET_CONVENIOS_INFO_CAMPANAS = 1 OR t.RET_CONVENIOS_CONSULTAS_GENERALES = 1 OR t.RET_CONVENIOS_DEVOLUCION_CUOTAS = 1 OR t.RET_CONVENIOS_COBRANZAS = 1 OR t.RET_CONVENIOS_PEDIDOS_RECLAMOS = 1) THEN t.TIEMPO_HABLADO_HH_MM_SS ELSE NULL END AS Tiempohablado_POST_VENTA,
        
        -- Duración y silencios específicos para cancelaciones
        CASE WHEN (t.RET_CONVENIOS_COMPRA_DE_DEUDA = 1 OR t.RET_CONVENIOS_TASA_INTERES = 1 OR t.RET_CONVENIOS_MAYOR_IMPORTE = 1 OR t.RET_CONVENIOS_MEDIOS_PROPIOS = 1) THEN t.TIEMPO_LLAMADA_HH_MM_SS ELSE NULL END AS TiempoLlamada_cancelaciones,
        CASE WHEN (t.RET_CONVENIOS_COMPRA_DE_DEUDA = 1 OR t.RET_CONVENIOS_TASA_INTERES = 1 OR t.RET_CONVENIOS_MAYOR_IMPORTE = 1 OR t.RET_CONVENIOS_MEDIOS_PROPIOS = 1) THEN t.TIEMPO_SILENCIO_HH_MM_SS ELSE NULL END AS Tiemposilencio_cancelaciones,
        CASE WHEN (t.RET_CONVENIOS_COMPRA_DE_DEUDA = 1 OR t.RET_CONVENIOS_TASA_INTERES = 1 OR t.RET_CONVENIOS_MAYOR_IMPORTE = 1 OR t.RET_CONVENIOS_MEDIOS_PROPIOS = 1) THEN t.TIEMPO_HABLADO_HH_MM_SS ELSE NULL END AS Tiempohablado_cancelaciones,
        
        -- Matriz de alertas de retención basada en prioridades
        CASE 
            WHEN t.RET_CONVENIOS_SOL_CRONOGRAMA = 1
                THEN 'SOLICITUD DE CRONOGRAMA DE PAGOS'
            WHEN t.RET_CONVENIOS_SOL_CANCELACION = 1
                THEN 'SOLICITUD DE CANCELACION'
            WHEN t.RET_CONVENIOS_SOL_DEUDA_TOTAL = 1
                THEN 'SOLICITUD DE DEUDA TOTAL'
            WHEN t.RET_CONVENIOS_SOL_TASA_INTERES = 1
                THEN 'SOLICITUD DE TASA DE INTERES'
            WHEN t.GESTION = '2.Solicita cancelación'
                THEN 'SOLICITUD DE CANCELACION'
            WHEN t.GESTION = '5.Deuda Total al día'
                THEN 'SOLICITUD DE DEUDA TOTAL'
            WHEN t.GESTION = '6.Baja de Tasa - P'
                THEN 'SOLICITUD DE TASA DE INTERES'
            WHEN t.GESTION IN ('1.Liquidación de Deuda - P','3.Retención Derivada Gestor CxC')
                THEN 'SOLICITUD DE DEUDA TOTAL'
            ELSE NULL 
        END AS ALERTAS_RETENCIONES
    FROM VT_RETENCION_STEP1 t
) WITH DATA PRIMARY INDEX (conID) ON COMMIT PRESERVE ROWS;


-- -------------------------------------------------------------
-- PASO 3: PERSISTENCIA TRANSACCIONAL (Consolidación)
-- -------------------------------------------------------------

-- 3.1 Limpiar registros del período para permitir reprocesos limpios
DELETE FROM DLAB_GEC.REPORTE_RETENCION_CONVENIOS 
WHERE Periodo = '{PERIODO}';

-- 3.2 Insertar los nuevos registros procesados del mes de forma detallada y ordenada
INSERT INTO DLAB_GEC.REPORTE_RETENCION_CONVENIOS (
    RET_CONVENIOS_COBRANZAS,
    RET_CONVENIOS_COMPRA_DE_DEUDA,
    RET_CONVENIOS_CONSULTAS_GENERALES,
    RET_CONVENIOS_DEVOLUCION_CUOTAS,
    RET_CONVENIOS_INFO_CAMPANAS,
    RET_CONVENIOS_MAYOR_IMPORTE,
    RET_CONVENIOS_MEDIOS_PROPIOS,
    RET_CONVENIOS_OFF_MAVERICK,
    RET_CONVENIOS_PEDIDOS_RECLAMOS,
    RET_CONVENIOS_RET_AMPLIACION,
    RET_CONVENIOS_RET_BAJA_TASA,
    RET_CONVENIOS_SOL_CANCELACION,
    RET_CONVENIOS_SOL_CRONOGRAMA,
    RET_CONVENIOS_SOL_DEUDA_TOTAL,
    RET_CONVENIOS_SOL_TASA_INTERES,
    RET_CONVENIOS_TASA_INTERES,
    RET_CONVENIOS_PLAZA_VEA,
    RET_CONVENIOS_UTP,
    TiempoLlamada,
    TIEMPO_SILENCIO,
    DniCliente,
    RegistroAgente,
    FechaLlamada,
    NUM_TELEF,
    DNIS,
    conID,
    Tipificacion,
    IDContacto,
    cti_BT_Segmento,
    Area,
    Periodo,
    TIEMPO_SILENCIO_HH_MM_SS,
    TIEMPO_LLAMADA_HH_MM_SS,
    TIEMPO_HABLADO_HH_MM_SS,
    FLUJO,
    Empleado,
    SEGMENTO,
    FAMILIA,
    MOTIVO,
    RESPUESTA,
    GESTION,
    PLAZA,
    AC_TASA,
    AC_AMPLIACION,
    TOTAL_RETENCIONES,
    CLIENTE_GESTIONABLE,
    CANCELACIONES_EFECTIVAS,
    RETENCION_TASA,
    RETENCION_MONTO,
    RANGO_LLAMADA,
    TiempoLlamada_retenciones,
    Tiemposilencio_retenciones,
    Tiempohablado_retenciones,
    TOTAL_MOTIVOS_ANULACION,
    TiempoLlamada_ofrecimiento,
    Tiemposilencio_ofrecimiento,
    Tiempohablado_ofrecimiento,
    TiempoLlamada_POST_VENTA,
    Tiemposilencio_POST_VENTA,
    Tiempohablado_POST_VENTA,
    TiempoLlamada_cancelaciones,
    Tiemposilencio_cancelaciones,
    Tiempohablado_cancelaciones,
    ALERTAS_RETENCIONES
)
SELECT 
    RET_CONVENIOS_COBRANZAS,
    RET_CONVENIOS_COMPRA_DE_DEUDA,
    RET_CONVENIOS_CONSULTAS_GENERALES,
    RET_CONVENIOS_DEVOLUCION_CUOTAS,
    RET_CONVENIOS_INFO_CAMPANAS,
    RET_CONVENIOS_MAYOR_IMPORTE,
    RET_CONVENIOS_MEDIOS_PROPIOS,
    RET_CONVENIOS_OFF_MAVERICK,
    RET_CONVENIOS_PEDIDOS_RECLAMOS,
    RET_CONVENIOS_RET_AMPLIACION,
    RET_CONVENIOS_RET_BAJA_TASA,
    RET_CONVENIOS_SOL_CANCELACION,
    RET_CONVENIOS_SOL_CRONOGRAMA,
    RET_CONVENIOS_SOL_DEUDA_TOTAL,
    RET_CONVENIOS_SOL_TASA_INTERES,
    RET_CONVENIOS_TASA_INTERES,
    RET_CONVENIOS_PLAZA_VEA,
    RET_CONVENIOS_UTP,
    TiempoLlamada,
    TIEMPO_SILENCIO,
    DniCliente,
    RegistroAgente,
    FechaLlamada,
    NUM_TELEF,
    DNIS,
    conID,
    Tipificacion,
    IDContacto,
    cti_BT_Segmento,
    Area,
    Periodo,
    TIEMPO_SILENCIO_HH_MM_SS,
    TIEMPO_LLAMADA_HH_MM_SS,
    TIEMPO_HABLADO_HH_MM_SS,
    FLUJO,
    Empleado,
    SEGMENTO,
    FAMILIA,
    MOTIVO,
    RESPUESTA,
    GESTION,
    PLAZA,
    AC_TASA,
    AC_AMPLIACION,
    TOTAL_RETENCIONES,
    CLIENTE_GESTIONABLE,
    CANCELACIONES_EFECTIVAS,
    RETENCION_TASA,
    RETENCION_MONTO,
    RANGO_LLAMADA,
    TiempoLlamada_retenciones,
    Tiemposilencio_retenciones,
    Tiempohablado_retenciones,
    TOTAL_MOTIVOS_ANULACION,
    TiempoLlamada_ofrecimiento,
    Tiemposilencio_ofrecimiento,
    Tiempohablado_ofrecimiento,
    TiempoLlamada_POST_VENTA,
    Tiemposilencio_POST_VENTA,
    Tiempohablado_POST_VENTA,
    TiempoLlamada_cancelaciones,
    Tiemposilencio_cancelaciones,
    Tiempohablado_cancelaciones,
    ALERTAS_RETENCIONES
FROM VT_RETENCION_FINAL
WHERE ALERTAS_RETENCIONES IS NOT NULL
AND FLUJO IS NOT NULL;

