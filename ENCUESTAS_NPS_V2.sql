-- =============================================================================
-- SCRIPT PARAMETRIZADO: ENCUESTAS NPS TELEVENTAS (V2.1 TOTALMENTE DINÁMICO)
-- Motor: Teradata Database (DLAB_GEC / E_DW_VIEWS_DLAB)
-- Parámetro dinámico esperado: {PERIODO} (Ejemplo: '202608' o '202601')
-- CERO HARDCODEO: Listo para ejecución directa o desde el orquestador Python.
-- =============================================================================


-- =============================================================================
-- PASO 1 - Crear tabla FACT de ventas: F_NPS_VENTAS_TV
-- =============================================================================

-- (Opcional si se requiere recrear):
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
    REGISTRO     VARCHAR(255) CHARACTER SET LATIN NOT CASESPECIFIC, -- CODPROMOT / REGISTRO
    CODIGO       VARCHAR(255) CHARACTER SET LATIN NOT CASESPECIFIC, -- PERIODO || '_' || REGISTRO
    PRODUCTO     VARCHAR(255) CHARACTER SET LATIN NOT CASESPECIFIC, -- Alineado con SUB_EQUIPO
    ORIGEN       VARCHAR(50)  CHARACTER SET LATIN NOT CASESPECIFIC  -- Alineado con EQUIPO
)
PRIMARY INDEX ( CODIGO )
PARTITION BY RANGE_N(PERIODO BETWEEN '202001' AND '203512' EACH 1);



-- =============================================================================
-- PASO 2 - Proceso de carga mensual de ventas (100% Parametrizado con {PERIODO})
-- =============================================================================

DELETE FROM DLAB_GEC.F_NPS_VENTAS_TV
WHERE PERIODO = '{PERIODO}';

INSERT INTO DLAB_GEC.F_NPS_VENTAS_TV
(
    PERIODO,
    FECHA_VENTA,
    REGISTRO,
    CODIGO,
    PRODUCTO,
    ORIGEN
)
    -- 1. TARJETA DE CRÉDITO (TC)
    SELECT
        MESDESEMBOLSO                           AS PERIODO,
        CAST(FECDESEMB AS DATE)                 AS FECHA_VENTA,
        CODPROMOT                               AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'TLV TC'                                AS PRODUCTO,
        'TC'                                    AS ORIGEN
    FROM DLAB_GEC.M_EXP_VENTAS_TC
    WHERE MESDESEMBOLSO = '{PERIODO}'

    UNION ALL

    -- 2. PRÉSTAMO PERSONAL (PP)
    SELECT
        MESDESEMBOLSO                           AS PERIODO,
        CAST(FECDESEMB AS DATE)                 AS FECHA_VENTA,
        CODPROMOT                               AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'TLV CASH'                              AS PRODUCTO,
        'PP'                                    AS ORIGEN
    FROM DLAB_GEC.M_EXP_VENTAS_PP
    WHERE MESDESEMBOLSO = '{PERIODO}'

    UNION ALL

    -- 3. EXTRACASH (EC)
    SELECT
        MESDESEMBOLSO                           AS PERIODO,
        CAST(FECDESEMB AS DATE)                 AS FECHA_VENTA,
        CODPROMOT                               AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'TLV CASH'                              AS PRODUCTO,
        'EC'                                    AS ORIGEN
    FROM DLAB_GEC.M_EXP_VENTAS_EC
    WHERE MESDESEMBOLSO = '{PERIODO}'

    UNION ALL

    -- 4. COMPRA DE DEUDA (CD)
    SELECT
        MESDESEMBOLSO                           AS PERIODO,
        CAST(FECDESEMBOLSO AS DATE)             AS FECHA_VENTA,
        CODPROMOT                               AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'TLV CASH'                              AS PRODUCTO,
        'CD'                                    AS ORIGEN
    FROM DLAB_GEC.M_EXP_VENTAS_CD
    WHERE MESDESEMBOLSO = '{PERIODO}'

    UNION ALL

    -- 5. CRÉDITO POR CONVENIO (CON)
    SELECT
        MESDESEMBOLSO                           AS PERIODO,
        CAST(FECDESEMB AS DATE)                 AS FECHA_VENTA,
        CODPROMOT                               AS REGISTRO,
        MESDESEMBOLSO || '_' || CODPROMOT       AS CODIGO,
        'CONVENIOS'                             AS PRODUCTO,
        'CONV_TLV'                              AS ORIGEN
    FROM DLAB_GEC.M_EXP_VENTAS_CON
    WHERE MESDESEMBOLSO = '{PERIODO}'

    UNION ALL

    -- 9. RETENCIÓN CONVENIOS (RET_CON)
    SELECT
        CAST(MES AS VARCHAR(6))                            AS PERIODO,
        CAST(FECHA AS DATE)                                AS FECHA_VENTA,
        PRIMER_REGISTRO                                    AS REGISTRO,
        CAST(MES AS VARCHAR(6)) || '_' || PRIMER_REGISTRO  AS CODIGO,
        'RET. CONV'                                        AS PRODUCTO,
        'R_CO'                                             AS ORIGEN
    FROM E_DW_VIEWS_DLAB.V_CNV_VISTA_RETENCION_BT
    WHERE CAST(MES AS VARCHAR(6)) = '{PERIODO}'
      AND RETENCION_FLG = 1

    UNION ALL

    -- 10. RETENCIÓN TARJETAS (RET_TC) - Rango Sargable
    SELECT
        '{PERIODO}'                                        AS PERIODO,
        CAST(FECHA_ALTA AS DATE)                           AS FECHA_VENTA,
        REG_ASESOR_RET                                     AS REGISTRO,
        '{PERIODO}_' || REG_ASESOR_RET                     AS CODIGO,
        'RET. MULTI'                                       AS PRODUCTO,
        'R_MULTI'                                          AS ORIGEN
    FROM DLAB_GEC.T_RETENCION_BASE_CALIDAD_GIRU
    WHERE FECHA_ALTA BETWEEN CAST('{PERIODO}01' AS DATE FORMAT 'YYYYMMDD') 
                         AND LAST_DAY(CAST('{PERIODO}01' AS DATE FORMAT 'YYYYMMDD'))
      AND REG_ASESOR_RET IS NOT NULL

    UNION ALL

    -- 11. SEGUROS (SEG) - Parsing optimizado
    SELECT
        MESVENTA                                           AS PERIODO,
        CASE
            WHEN FECVENTA IS NULL OR TRIM(FECVENTA) = '' THEN NULL
            WHEN CHARACTER_LENGTH(TRIM(FECVENTA)) = 8 
                 AND POSITION('-' IN FECVENTA) = 0 
                 AND POSITION('/' IN FECVENTA) = 0
            THEN CAST(TRIM(FECVENTA) AS DATE FORMAT 'YYYYMMDD')
            WHEN POSITION('-' IN FECVENTA) = 5 
            THEN CAST(TRIM(FECVENTA) AS DATE)
            WHEN POSITION('/' IN FECVENTA) = 3 
            THEN CAST(
                SUBSTRING(TRIM(FECVENTA) FROM 7 FOR 4) ||
                SUBSTRING(TRIM(FECVENTA) FROM 4 FOR 2) ||
                SUBSTRING(TRIM(FECVENTA) FROM 1 FOR 2)
                AS DATE FORMAT 'YYYYMMDD')
            ELSE NULL
        END                                                AS FECHA_VENTA,
        CODPROMOT                                          AS REGISTRO,
        MESVENTA || '_' || CODPROMOT                       AS CODIGO,
        'GDP'                                              AS PRODUCTO,
        'SEG'                                              AS ORIGEN
    FROM DLAB_GEC.T_CALIDAD_SEGUROS_PRT
    WHERE MESVENTA = '{PERIODO}'

    UNION ALL

    -- 12. BANCA NEGOCIOS (BNB) - Rango Sargable
    SELECT
        '{PERIODO}'                                        AS PERIODO,
        CAST(FECHA_DESEMBOLSADO AS DATE)                   AS FECHA_VENTA,
        REGISTRO                                           AS REGISTRO,
        '{PERIODO}_' || REGISTRO                           AS CODIGO,
        'BANCA NEGOCIOS'                                   AS PRODUCTO,
        'BNB'                                              AS ORIGEN
    FROM DLAB_GEC.T_VENTAS_BPE_MARKET
    WHERE FECHA_DESEMBOLSADO BETWEEN CAST('{PERIODO}01' AS DATE FORMAT 'YYYYMMDD') 
                                 AND LAST_DAY(CAST('{PERIODO}01' AS DATE FORMAT 'YYYYMMDD'))

    UNION ALL

    -- 13. BANCA NEGOCIOS (BNC) - Rango Sargable
    SELECT
        '{PERIODO}'                                        AS PERIODO,
        CAST(FEC_LLAMADA AS DATE)                          AS FECHA_VENTA,
        REG_EJECUTIVO                                      AS REGISTRO,
        '{PERIODO}_' || REG_EJECUTIVO                      AS CODIGO,
        'BANCA NEGOCIOS'                                   AS PRODUCTO,
        'BNC'                                              AS ORIGEN
    FROM DLAB_GEC.V_GESTION_BNC
    WHERE FEC_LLAMADA BETWEEN CAST('{PERIODO}01' AS DATE FORMAT 'YYYYMMDD') 
                          AND LAST_DAY(CAST('{PERIODO}01' AS DATE FORMAT 'YYYYMMDD'))
;



-- =============================================================================
-- PASO 3 - Vista de encuestas NPS con grano diario
-- =============================================================================

REPLACE VIEW DLAB_GEC.V_NPS_ENCUESTAS_IVR_RES_DIA AS
(
    SELECT
        e.PERIODO,
        CAST(OREPLACE(e.FECHA, '/', '') AS DATE FORMAT 'YYYYMMDD') AS FECHA_ENCUESTA,
        e.REG_EV                                                    AS REGISTRO,
        eg.CODIGO,
        eg.SUB_EQUIPO                                               AS PRODUCTO,
        
        COUNT(*)                                                    AS CANT_ENCUESTAS_ENVIADAS,
        
        SUM(
            CASE 
                WHEN e.RESP_1 IS NOT NULL AND TRIM(e.RESP_1) <> '' 
                THEN 1 
                ELSE 0 
            END
        )                                                           AS CANT_ENCUESTAS_RESPONDIDAS,
        
        SUM(CASE WHEN e.NOTA = 1  THEN 1 ELSE 0 END)                AS CANT_PROMOTORES,
        SUM(CASE WHEN e.NOTA = -1 THEN 1 ELSE 0 END)                AS CANT_DETRACTORES,
        
        CASE 
            WHEN SUM(CASE WHEN e.RESP_1 IS NOT NULL AND TRIM(e.RESP_1) <> '' THEN 1 ELSE 0 END) = 0 
            THEN NULL
            ELSE
                (
                    1.0 * (
                        SUM(CASE WHEN e.NOTA = 1  THEN 1 ELSE 0 END)
                      - SUM(CASE WHEN e.NOTA = -1 THEN 1 ELSE 0 END)
                    )
                    /
                    NULLIFZERO(
                        SUM(CASE WHEN e.RESP_1 IS NOT NULL AND TRIM(e.RESP_1) <> '' THEN 1 ELSE 0 END)
                    )
                )
        END                                                         AS NPS
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



-- =============================================================================
-- PASO 4 - Vista de encuestas NPS agregada mensual
-- =============================================================================

REPLACE VIEW DLAB_GEC.V_NPS_ENCUESTAS_IVR_RES_MES AS
(
    SELECT
        PERIODO,
        REGISTRO,
        CODIGO,
        PRODUCTO,
        SUM(CANT_ENCUESTAS_ENVIADAS)                                AS CANT_ENCUESTAS_ENVIADAS,
        SUM(CANT_ENCUESTAS_RESPONDIDAS)                             AS CANT_ENCUESTAS_RESPONDIDAS,
        SUM(CANT_PROMOTORES)                                        AS CANT_PROMOTORES,
        SUM(CANT_DETRACTORES)                                       AS CANT_DETRACTORES,
        CASE 
            WHEN SUM(CANT_ENCUESTAS_RESPONDIDAS) = 0 THEN NULL
            ELSE 
                1.0 * (SUM(CANT_PROMOTORES) - SUM(CANT_DETRACTORES))
                    / NULLIFZERO(SUM(CANT_ENCUESTAS_RESPONDIDAS))
        END                                                         AS NPS
    FROM DLAB_GEC.V_NPS_ENCUESTAS_IVR_RES_DIA
    GROUP BY
        PERIODO,
        REGISTRO,
        CODIGO,
        PRODUCTO
);



-- =============================================================================
-- PASO 5 - Vista Ejecutiva final: V_NPS_EJECUTIVOS_PRODUCTO
-- =============================================================================

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
        
        COALESCE(v.CANT_VENTAS, 0)                  AS CANT_VENTAS,
        COALESCE(e.CANT_ENCUESTAS_ENVIADAS, 0)      AS CANT_ENCUESTAS_ENVIADAS,
        COALESCE(e.CANT_ENCUESTAS_RESPONDIDAS, 0)   AS CANT_ENCUESTAS_RESPONDIDAS,
        COALESCE(e.CANT_PROMOTORES, 0)              AS CANT_PROMOTORES,
        COALESCE(e.CANT_DETRACTORES, 0)             AS CANT_DETRACTORES,
        
        1.0 * ZEROIFNULL(e.CANT_ENCUESTAS_ENVIADAS) 
            / NULLIFZERO(v.CANT_VENTAS)             AS PORC_ENVIO,
        
        1.0 * ZEROIFNULL(e.CANT_ENCUESTAS_RESPONDIDAS) 
            / NULLIFZERO(e.CANT_ENCUESTAS_ENVIADAS) AS PORC_RESPUESTA,
        
        e.NPS                                       AS NPS
        
    FROM DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED eg
    
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
    
    LEFT JOIN DLAB_GEC.V_NPS_ENCUESTAS_IVR_RES_MES e
      ON e.PERIODO  = eg.PERIODO
     AND e.CODIGO   = eg.CODIGO
     AND e.PRODUCTO = eg.SUB_EQUIPO
);
