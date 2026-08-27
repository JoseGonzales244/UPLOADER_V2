-- =====================================================================
-- 01_EXTRACT_CONID_TC.SQL
-- Extrae las interacciones de TC evaluadas desde PureCloud
-- =====================================================================
SELECT DISTINCT 
    TRIM(CONID) AS CONID,
    'TC' AS PRODUCTO,
    CAST(FECHA_VENTA AS DATE) AS FECHA_LLAMADA,
    TRIM(DNI) AS DNI,
    TRIM(REG_EJECUTIVO) AS REGISTRO
FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD
WHERE PLANTILLA = 'Exp. Compra - TC'
  AND CONID IS NOT NULL
  AND CONID <> '';
