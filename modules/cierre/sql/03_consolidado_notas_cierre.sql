-- =====================================================================
-- 03_CONSOLIDADO_NOTAS_CIERRE.SQL
-- Cierre del proceso de calidad: Consolidación final de notas de cierre
-- e inyección de estructura organizativa para el período {PERIODO}.
-- =====================================================================

-- -------------------------------------------------------------
-- PASO 1: LIMPIEZA PREVIA (Garantiza idempotencia en re-ejecuciones)
-- -------------------------------------------------------------
DELETE FROM DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE
WHERE MES = '{PERIODO}';

-- -------------------------------------------------------------
-- PASO 2: INSERCIÓN DE NOTAS FINALES
-- -------------------------------------------------------------
INSERT INTO DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE (
    MES,
    NOM_SUBGERENCIA,
    NEGOCIO,
    EQUIPO,
    SUB_EQUIPO,
    REG_JEFE,
    NOM_JEFE,
    REG_SUPERVISOR,
    NOMBRE_SUPERVISOR,
    REG_EV,
    NOM_EJECUTIVO,
    NOTA_FINAL,
    NUM_EVALUACION
)
SELECT 
    PERIODO AS MES,
    NULL AS NOM_SUBGERENCIA,
    NULL AS NEGOCIO,
    NULL AS EQUIPO,
    NULL AS SUB_EQUIPO,
    NULL AS REG_JEFE,
    NULL AS NOM_JEFE,
    NULL AS REG_SUPERVISOR,
    NULL AS NOMBRE_SUPERVISOR,
    REG_EJECUTIVO AS REG_EV,
    NULL AS NOM_EJECUTIVO,
    NOTA_FINAL,
    NUM_EVALUACION
FROM DLAB_GEC.M_EXP_CALIDAD_NOTA_FINAL
WHERE PERIODO = '{PERIODO}'
  AND NOTA_FINAL IS NOT NULL;

-- -------------------------------------------------------------
-- PASO 3: ACTUALIZACIÓN DE JERARQUÍAS ORGANIZATIVAS Y EJECUTIVOS
-- -------------------------------------------------------------
UPDATE A 
FROM DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE A, 
     DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED B
SET NOM_EJECUTIVO     = B.NOM_EJECUTIVO, 
    REG_SUPERVISOR    = B.REG_SUPERVISOR,
    NOMBRE_SUPERVISOR = B.NOM_SUPERVISOR,
    REG_JEFE          = B.REG_JEFE,
    NOM_JEFE          = B.NOM_JEFE,
    NOM_SUBGERENCIA   = B.SUBGERENTE,
    SUB_EQUIPO        = B.SUB_EQUIPO,
    EQUIPO            = B.EQUIPO
WHERE A.REG_EV = B.REG_EJECUTIVO
  AND A.MES = '{PERIODO}'
  AND B.PERIODO = '{PERIODO}';
