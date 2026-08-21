
-- PASO 1 - Crear tabla FACT de ventas: F_NPS_VENTAS_TV

-- (Opcional) Limpia si ya existiera
-- DROP TABLE DLAB_GEC.F_NPS_VENTAS_TV;

CREATE MULTISET TABLE DLAB_GEC.F_NPS_VENTAS_TV
, FALLBACK
, NO BEFORE JOURNAL
, NO AFTER JOURNAL
, CHECKSUM = DEFAULT
, DEFAULT MERGEBLOCKRATIO
, MAP = TD_MAP1
(
    PERIODO      VARCHAR(6)   CHARACTER SET LATIN NOT CASESPECIFIC, -- AAAAMM
    FECHA_VENTA  DATE,
    REGISTRO     VARCHAR(255) CHARACTER SET LATIN NOT CASESPECIFIC, -- CODPROMOT / REGISTRO / etc.
    CODIGO       VARCHAR(255) CHARACTER SET LATIN NOT CASESPECIFIC, -- PERIODO || '_' || REGISTRO
    PRODUCTO     VARCHAR(255) CHARACTER SET LATIN NOT CASESPECIFIC, -- alineado con SUB_EQUIPO
    ORIGEN       VARCHAR(50)  CHARACTER SET LATIN NOT CASESPECIFIC  -- alineado con EQUIPO
)
PRIMARY INDEX ( CODIGO );



-- PASO 2 - Proceso de carga mensual de ventas

-- ===========================
-- CARGA DE VENTAS NPS TV
-- ===========================
-- Parámetro lógico de periodo: 'AAAAMM'
-- Reemplazar en TODO el script '202601' por el periodo requerido.

DELETE FROM DLAB_GEC.F_NPS_VENTAS_TV
WHERE PERIODO = '202601';

INSERT INTO DLAB_GEC.F_NPS_VENTAS_TV
    (
    PERIODO,
    FECHA_VENTA,
    REGISTRO,
    CODIGO,
    PRODUCTO,
    ORIGEN
    ) -- 1. TARJETA DE CRÉDITO (TC)
    
    SELECT
        MESDESEMBOLSO                            AS PERIODO,
        CAST(FECDESEMB AS DATE)                 AS FECHA_VENTA,
        CODPROMOT                                AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'TLV TC'                    AS PRODUCTO,
        'TC'                                    AS ORIGEN
        FROM DLAB_GEC.M_EXP_VENTAS_TC
        WHERE MESDESEMBOLSO = '202601'
    UNION ALL -- 2. PRÉSTAMO PERSONAL (PP)
    
    SELECT
        MESDESEMBOLSO                            AS PERIODO,
        CAST(FECDESEMB AS DATE)                 AS FECHA_VENTA,
        CODPROMOT                                AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'TLV CASH'                     AS PRODUCTO,
        'PP'                                    AS ORIGEN
        FROM DLAB_GEC.M_EXP_VENTAS_PP
        WHERE MESDESEMBOLSO = '202601'
    UNION ALL -- 3. EXTRACASH (EC)
    
    SELECT
        MESDESEMBOLSO                            AS PERIODO,
        CAST(FECDESEMB AS DATE)                 AS FECHA_VENTA,
        CODPROMOT                                AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'TLV CASH'                             AS PRODUCTO,
        'EC'                                    AS ORIGEN
        FROM DLAB_GEC.M_EXP_VENTAS_EC
        WHERE MESDESEMBOLSO = '202601'
    UNION ALL -- 4. COMPRA DE DEUDA (CD)
    
    SELECT
        MESDESEMBOLSO                            AS PERIODO,
        CAST(FECDESEMBOLSO AS DATE)            AS FECHA_VENTA,
        CODPROMOT                                AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'TLV CASH'                       AS PRODUCTO,
        'CD'                                    AS ORIGEN
        FROM DLAB_GEC.M_EXP_VENTAS_CD
        WHERE MESDESEMBOLSO = '202601'
    UNION ALL -- 5. CREDITO POR CONVENIO (CON)
    
    SELECT
        MESDESEMBOLSO                            AS PERIODO,
        CAST(FECDESEMB AS DATE)                 AS FECHA_VENTA,
        CODPROMOT                                AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'CONVENIOS'                  AS PRODUCTO,
        'CONV_TLV'                                   AS ORIGEN
        FROM DLAB_GEC.M_EXP_VENTAS_CON
        WHERE MESDESEMBOLSO = '202601'
    
    UNION ALL -- 9. RETENCION CONVENIOS (RET_CON)
    
    SELECT
        CAST(MES AS VARCHAR(6))                 AS PERIODO,
        CAST(FECHA AS DATE)                     AS FECHA_VENTA,
        PRIMER_REGISTRO                         AS REGISTRO,
        CAST(MES AS VARCHAR(6)) || '_' || PRIMER_REGISTRO AS CODIGO,
        'RET. CONV'                   AS PRODUCTO,
        'R_CO'                               AS ORIGEN
        FROM E_DW_VIEWS_DLAB.V_CNV_VISTA_RETENCION_BT
        WHERE CAST( MES AS VARCHAR(6)) = '202601'
            AND  RETENCION_FLG = 1
    UNION ALL -- 10. RETENCION TARJETAS (RET_TC)
    
    SELECT
        CAST(TO_CHAR(FECHA_ALTA, 'YYYYMM') AS VARCHAR(6)) AS PERIODO,
        CAST(FECHA_ALTA AS DATE)                          AS FECHA_VENTA,
        REG_ASESOR_RET                                    AS REGISTRO,
        CAST(TO_CHAR(FECHA_ALTA, 'YYYYMM') AS VARCHAR(6)) || '_' || REG_ASESOR_RET AS CODIGO,
        'RET. MULTI'                              AS PRODUCTO,
        'R_MULTI'                                          AS ORIGEN
        FROM DLAB_GEC.T_RETENCION_BASE_CALIDAD_GIRU
        WHERE CAST( TO_CHAR(FECHA_ALTA, 'YYYYMM') AS VARCHAR(6)) = '202601'
            AND  REG_ASESOR_RET IS NOT NULL
    UNION ALL -- 11. SEGUROS (SEG)
    
    SELECT
        MESVENTA                                        AS PERIODO,
        
        CASE
            WHEN FECVENTA IS NOT NULL AND REGEXP_SIMILAR(TRIM(FECVENTA), '^[0-9]{8}$') = 1 
        THEN CAST(CAST(TRIM(FECVENTA) AS CHAR(8)) AS DATE FORMAT 'YYYYMMDD')
            WHEN FECVENTA IS NOT NULL AND REGEXP_SIMILAR(TRIM(FECVENTA), '^[0-9]{4}-[0-9]{2}-[0-9]{2}$') = 1 
        THEN CAST(TRIM(FECVENTA) AS DATE)
            WHEN FECVENTA IS NOT NULL AND REGEXP_SIMILAR(TRIM(FECVENTA), '^[0-9]{2}/[0-9]{2}/[0-9]{4}$') = 1 
        THEN CAST(
        SUBSTRING(TRIM(FECVENTA)
        FROM 7 FOR 4) ||
        SUBSTRING(TRIM(FECVENTA)
        FROM 4 FOR 2) ||
        SUBSTRING(TRIM(FECVENTA)
        FROM 1 FOR 2)
        AS DATE FORMAT 'YYYYMMDD')
        ELSE NULL
        END                                           AS FECHA_VENTA,
            CODPROMOT                                     AS REGISTRO,
            MESVENTA || '_' || CODPROMOT                  AS CODIGO,
            'GDP'                                     AS PRODUCTO,
            'SEG'                                         AS ORIGEN
        FROM DLAB_GEC.T_CALIDAD_SEGUROS_PRT
        WHERE MESVENTA = '202601'
    UNION ALL -- 12. BANCA NEGOCIO (BNB)
    
    SELECT
        CAST(TO_CHAR(FECHA_DESEMBOLSADO, 'YYYYMM') AS VARCHAR(6)) AS PERIODO,
        CAST(FECHA_DESEMBOLSADO AS DATE)                     AS FECHA_VENTA,
        REGISTRO                                             AS REGISTRO,
        CAST(TO_CHAR(FECHA_DESEMBOLSADO, 'YYYYMM') AS VARCHAR(6)) || '_' || REGISTRO AS CODIGO,
        'BANCA NEGOCIOS'                                      AS PRODUCTO,
        'BNB'                                                AS ORIGEN
        FROM DLAB_GEC.T_VENTAS_BPE_MARKET
        WHERE CAST( TO_CHAR(FECHA_DESEMBOLSADO, 'YYYYMM') AS VARCHAR(6)) = '202601'
        UNION ALL  -- 13. BANCA NEGOCIO (BNC)
        
     SELECT
        CAST(TO_CHAR(FEC_LLAMADA, 'YYYYMM') AS VARCHAR(6)) AS PERIODO,
        CAST(FEC_LLAMADA AS DATE)                     AS FECHA_VENTA,
        REG_EJECUTIVO                                 AS REGISTRO,
        CAST(TO_CHAR(FEC_LLAMADA, 'YYYYMM') AS VARCHAR(6)) || '_' || REGISTRO AS CODIGO,
        'BANCA NEGOCIOS'                                      AS PRODUCTO,
        'BNC'                                                AS ORIGEN
        FROM DLAB_GEC.V_GESTION_BNC
        WHERE CAST( TO_CHAR(FEC_LLAMADA, 'YYYYMM') AS VARCHAR(6)) = '202601'
        ;
       
  
        
 -- PASO 3 - Vista de encuestas NPS con grano diario
 
        
 REPLACE VIEW DLAB_GEC.V_NPS_ENCUESTAS_IVR_RES_DIA AS
(
    SELECT
        e.PERIODO,
        /* FECHA viene como 'YYYY/MM/DD', se convierte a DATE */
        CAST(
            SUBSTRING(e.FECHA FROM 1 FOR 4) ||
            SUBSTRING(e.FECHA FROM 6 FOR 2) ||
            SUBSTRING(e.FECHA FROM 9 FOR 2)
            AS DATE FORMAT 'YYYYMMDD'
        )                                      AS FECHA_ENCUESTA,
        e.REG_EV                               AS REGISTRO,
        eg.CODIGO,
        eg.SUB_EQUIPO                          AS PRODUCTO,
        
        /* Total de encuestas enviadas (incluye respondidas y no respondidas) */
        COUNT(*)                               AS CANT_ENCUESTAS_ENVIADAS,
        
        /* Encuestas con RESP_1 informada */
        SUM(
            CASE 
                WHEN e.RESP_1 IS NOT NULL 
                 AND TRIM(e.RESP_1) <> '' 
                THEN 1 
                ELSE 0 
            END
        )                                      AS CANT_ENCUESTAS_RESPONDIDAS,
        
        /* Promotores y detractores con base en NOTA */
        SUM(
            CASE 
                WHEN e.NOTA = 1 THEN 1 
                ELSE 0 
            END
        )                                      AS CANT_PROMOTORES,
        
        SUM(
            CASE 
                WHEN e.NOTA = -1 THEN 1 
                ELSE 0 
            END
        )                                      AS CANT_DETRACTORES,
        
        /* NPS diario */
        CASE 
            WHEN SUM(
                     CASE 
                         WHEN e.RESP_1 IS NOT NULL 
                          AND TRIM(e.RESP_1) <> '' 
                         THEN 1 
                         ELSE 0 
                     END
                 ) = 0 
              THEN NULL
            ELSE
                (
                    1.0 * (
                        SUM(CASE WHEN e.NOTA = 1  THEN 1 ELSE 0 END)
                      - SUM(CASE WHEN e.NOTA = -1 THEN 1 ELSE 0 END)
                    )
                    /
                    NULLIFZERO(
                        SUM(
                            CASE 
                                WHEN e.RESP_1 IS NOT NULL 
                                 AND TRIM(e.RESP_1) <> '' 
                                THEN 1 
                                ELSE 0 
                            END
                        )
                    )
                )
        END                                   AS NPS
    FROM DLAB_GEC.M_NPS_ENCUESTAS_IVR e
    LEFT JOIN DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED eg
      ON eg.PERIODO       = e.PERIODO
     AND eg.REG_EJECUTIVO = e.REG_EV
    GROUP BY
        e.PERIODO,
        FECHA_ENCUESTA,
        e.REG_EV,
        eg.CODIGO,
        eg.SUB_EQUIPO
);       



--PASO 4 - Vista de encuestas NPS agregada mensual

REPLACE VIEW DLAB_GEC.V_NPS_ENCUESTAS_IVR_RES_MES AS
(
    SELECT
        PERIODO,
        REGISTRO,
        CODIGO,
        PRODUCTO,
        SUM(CANT_ENCUESTAS_ENVIADAS)     AS CANT_ENCUESTAS_ENVIADAS,
        SUM(CANT_ENCUESTAS_RESPONDIDAS)  AS CANT_ENCUESTAS_RESPONDIDAS,
        SUM(CANT_PROMOTORES)             AS CANT_PROMOTORES,
        SUM(CANT_DETRACTORES)            AS CANT_DETRACTORES,
        CASE 
            WHEN SUM(CANT_ENCUESTAS_RESPONDIDAS) = 0 THEN NULL
            ELSE 
                1.0 * (SUM(CANT_PROMOTORES) - SUM(CANT_DETRACTORES))
                    / NULLIFZERO(SUM(CANT_ENCUESTAS_RESPONDIDAS))
        END                              AS NPS
    FROM DLAB_GEC.V_NPS_ENCUESTAS_IVR_RES_DIA
    GROUP BY
        PERIODO,
        REGISTRO,
        CODIGO,
        PRODUCTO
);


-- PASO 5 - Vista Ejecutiva final: V_NPS_EJECUTIVOS_PRODUCTO (ajustada)

REPLACE VIEW DLAB_GEC.V_NPS_EJECUTIVOS_PRODUCTO AS
(
    SELECT
        eg.PERIODO,
        eg.CODIGO,
        eg.REG_EJECUTIVO                            AS REGISTRO,
        eg.NOM_EJECUTIVO,
        eg.REG_SUPERVISOR,
        eg.NOM_SUPERVISOR,
        eg.REG_JEFE,
        eg.NOM_JEFE,
        eg.SUBGERENTE,
        eg.EQUIPO,
        eg.SUB_EQUIPO                               AS PRODUCTO,
        
        /* Métricas de VENTAS */
        COALESCE(v.CANT_VENTAS, 0)                  AS CANT_VENTAS,
        
        /* Métricas de ENCUESTAS */
        COALESCE(e.CANT_ENCUESTAS_ENVIADAS, 0)      AS CANT_ENCUESTAS_ENVIADAS,
        COALESCE(e.CANT_ENCUESTAS_RESPONDIDAS, 0)   AS CANT_ENCUESTAS_RESPONDIDAS,
        COALESCE(e.CANT_PROMOTORES, 0)              AS CANT_PROMOTORES,
        COALESCE(e.CANT_DETRACTORES, 0)             AS CANT_DETRACTORES,
        
        /* % ENVÍO: encuestas enviadas / ventas */
        CASE 
          WHEN COALESCE(v.CANT_VENTAS, 0) = 0 
            THEN NULL
          ELSE
            1.0 * COALESCE(e.CANT_ENCUESTAS_ENVIADAS, 0) 
                / v.CANT_VENTAS
        END                                         AS PORC_ENVIO,
        
        /* % RESPUESTA: encuestas respondidas / encuestas enviadas */
        CASE 
          WHEN COALESCE(e.CANT_ENCUESTAS_ENVIADAS, 0) = 0 
            THEN NULL
          ELSE
            1.0 * COALESCE(e.CANT_ENCUESTAS_RESPONDIDAS, 0)
                / e.CANT_ENCUESTAS_ENVIADAS
        END                                         AS PORC_RESPUESTA,
        
        /* NPS mensual ya calculado en la vista de encuestas */
        e.NPS                                       AS NPS
        
    FROM DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED eg
    
    /* Ventas agregadas por periodo, código, producto */
    LEFT JOIN
    (
        SELECT
            PERIODO,
            CODIGO,
            PRODUCTO,
            COUNT(*) AS CANT_VENTAS
        FROM DLAB_GEC.F_NPS_VENTAS_TV
        GROUP BY PERIODO, CODIGO, PRODUCTO
    ) v
      ON v.PERIODO  = eg.PERIODO
     AND v.CODIGO   = eg.CODIGO
     AND v.PRODUCTO = eg.SUB_EQUIPO
    
    /* Encuestas mensuales por periodo, código, producto */
    LEFT JOIN DLAB_GEC.V_NPS_ENCUESTAS_IVR_RES_MES e
      ON e.PERIODO  = eg.PERIODO
     AND e.CODIGO   = eg.CODIGO
     AND e.PRODUCTO = eg.SUB_EQUIPO
);
