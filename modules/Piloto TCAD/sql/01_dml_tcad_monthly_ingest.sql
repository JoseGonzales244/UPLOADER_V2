-- =============================================================================
-- INGESTA INCREMENTAL IDEMPOTENTE TCAD
-- Parametros esperados: {PERIODO}, {FECHA_INICIO}, {FECHA_FIN}
-- =============================================================================

-- 1. Eliminar datos existentes del periodo activo en la tabla historica SA
DELETE FROM DLAB_GEC.M_EXP_DATA_TCAD_SA
WHERE FECHA_LLAMADA >= TIMESTAMP '{FECHA_INICIO}'
  AND FECHA_LLAMADA < TIMESTAMP '{FECHA_FIN}';

-- 2. Insertar transformando al vuelo sin hacer UPDATE en la tabla PRE
INSERT INTO DLAB_GEC.M_EXP_DATA_TCAD_SA
SELECT 
    TCAD_A,
    TCAD_B,
    LTRIM(RTRIM(
        CASE 
            WHEN LENGTH(TELEF_IN) > 19 THEN TELEF_OUT
            ELSE SUBSTR(TELEF_IN, 8)
        END
    )) AS TELEF_IN,
    COLA,
    LPAD(TRIM(DNI), 8, '0') AS DNI,
    REG_EV,
    NOM_EV,
    SUPERVISOR,
    TIPIFICACION,
    DIRECCION,
    TELEF_OUT,
    DURACION,
    FECHA_LLAMADA,
    CONID,
    CODIGO,
    VENTA_TC,
    VENTA_TCAD,
    PERIODO,
    OFRE_TCAD
FROM DLAB_GEC.M_EXP_DATA_TCAD_SA_PRE;

-- 3. Actualizar campo CODIGO en M_EXP_CROSS_TCAD
UPDATE DLAB_GEC.M_EXP_CROSS_TCAD
SET CODIGO = TRIM(PERIODO) || '_' || TRIM(REG_EJECUTIVO);

