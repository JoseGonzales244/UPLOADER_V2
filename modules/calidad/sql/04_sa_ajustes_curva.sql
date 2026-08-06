-- =====================================================================
-- 04_SA_AJUSTES_CURVA.SQL
-- Aplica los pesos de la Maestra de Speech Analytics, calcula puntajes,
-- carga la tabla de detalle y ejecuta las curvas de ajuste y topes.
-- =====================================================================

-- 1. Cruce en memoria con la Maestra de Pesos SA, limpieza de espacios y cálculo de puntajes para FLAG=0
CREATE VOLATILE TABLE VT_EXP_CALIDAD_PESOS_SA_PROCESSED AS (
    SELECT
        s.PERIODO,
        TRIM(s.PRODUCTO) AS PRODUCTO,
        s.REG_EV,
        TRIM(s.CATEGORIA) AS CATEGORIA,
        COALESCE(s.OBTENIDO, 0.0) AS OBTENIDO,
        s.NEVALUACION,
        m.ESPERADO,
        m.PESO_CATEGORIA,
        m.PESO_GRUPO,
        CASE
            WHEN m.FLAG = 0 THEN
                CASE
                    WHEN m.ESPERADO IS NULL OR m.ESPERADO = 0 THEN 0.0
                    WHEN COALESCE(s.OBTENIDO, 0.0) >= m.ESPERADO THEN m.PESO_CATEGORIA
                    ELSE (COALESCE(s.OBTENIDO, 0.0) / m.ESPERADO) * m.PESO_CATEGORIA
                END
            ELSE CAST(NULL AS FLOAT)
        END AS PUNTAJE,
        m.FLAG,
        TRIM(m.GRUPO_CATEGORIA) AS GRUPO_CATEGORIA,
        s.CODIGO
    FROM VT_EXP_CALIDAD_PESOS_SA s
    INNER JOIN DLAB_GEC.M_EXP_MAESTRA_PESOS_SA m
        ON TRIM(s.CATEGORIA) = TRIM(m.CATEGORIA)
       AND TRIM(s.PRODUCTO)  = TRIM(m.PRODUCTO)
) WITH DATA PRIMARY INDEX (PERIODO, PRODUCTO, REG_EV, NEVALUACION) ON COMMIT PRESERVE ROWS;


-- 2. Calcular factores para categorías a nivel de grupo (FLAG = 1)
CREATE VOLATILE TABLE VT_FACTORES_GRUPO AS (
    SELECT
        PRODUCTO,
        GRUPO_CATEGORIA,
        CASE
            WHEN SUM(CASE WHEN OBTENIDO IS NULL THEN 1 ELSE 0 END) > 0 THEN 0.90
            WHEN SUM(CASE WHEN OBTENIDO < ESPERADO THEN 1 ELSE 0 END) > 0 THEN 0.95
            WHEN SUM(CASE WHEN OBTENIDO >= ESPERADO THEN 1 ELSE 0 END) > 0 THEN 1.00
            ELSE NULL
        END AS FACTOR
    FROM VT_EXP_CALIDAD_PESOS_SA_PROCESSED
    WHERE FLAG = 1
    GROUP BY 1,2
) WITH DATA PRIMARY INDEX (PRODUCTO, GRUPO_CATEGORIA) ON COMMIT PRESERVE ROWS;


-- 3. Generar dataset final integrando factores de grupo
CREATE VOLATILE TABLE VT_EXP_CALIDAD_PESOS_SA_FINAL AS (
    SELECT
        p.PERIODO,
        p.PRODUCTO,
        p.REG_EV,
        p.CATEGORIA,
        p.OBTENIDO,
        p.NEVALUACION,
        p.ESPERADO,
        p.PESO_CATEGORIA,
        p.PESO_GRUPO,
        CASE
            WHEN p.FLAG = 1 AND f.FACTOR IS NOT NULL THEN f.FACTOR * p.PESO_CATEGORIA
            ELSE p.PUNTAJE
        END AS PUNTAJE,
        p.FLAG,
        p.GRUPO_CATEGORIA,
        p.CODIGO
    FROM VT_EXP_CALIDAD_PESOS_SA_PROCESSED p
    LEFT JOIN VT_FACTORES_GRUPO f
        ON p.PRODUCTO = f.PRODUCTO
       AND p.GRUPO_CATEGORIA = f.GRUPO_CATEGORIA
) WITH DATA PRIMARY INDEX (PERIODO, PRODUCTO, REG_EV, NEVALUACION) ON COMMIT PRESERVE ROWS;


-- Eliminar tablas volátiles intermedias
DROP TABLE VT_FACTORES_GRUPO;
DROP TABLE VT_EXP_CALIDAD_PESOS_SA_PROCESSED;

-- Limpiar tabla física de detalle de Speech Analytics
DELETE FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS ALL;

-- Poblar la tabla de detalle desde la tabla volátil final
INSERT INTO DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS
SELECT * FROM VT_EXP_CALIDAD_PESOS_SA_FINAL;

DROP TABLE VT_EXP_CALIDAD_PESOS_SA_FINAL;


-- Aplicar suavizado de curvas para categorías de campañas tipo mixto
UPDATE det_sa
FROM   DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS AS det_sa,
       (
           SELECT
               sa.CODIGO,
               sa.NEVALUACION,
               CASE
                   WHEN SUM(sa.PUNTAJE) >= 0.59 THEN 1.0
                   WHEN SUM(sa.PUNTAJE) =  0.00 THEN 1.0
                   WHEN SUM(sa.PUNTAJE) <  0.45 THEN (0.56 / SUM(sa.PUNTAJE))
                   WHEN SUM(sa.PUNTAJE) <  0.52 THEN (0.57 / SUM(sa.PUNTAJE))
                   ELSE                          (0.58 / SUM(sa.PUNTAJE))
               END AS FACTOR_AJUSTE
           FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS AS sa
           INNER JOIN DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS AS eje
               ON eje.REG_EJECUTIVO = SUBSTR(sa.CODIGO, 8)
           WHERE TRIM(eje.SUB_EQUIPO) IN ('BNB','BNC','CD','CONV_TLV','EC','PP','HIP','R_CO','R_MULTI','SEG','TC')
           GROUP BY 1,2
           HAVING SUM(sa.PUNTAJE) > 0.0
              AND SUM(sa.PUNTAJE) < 0.59
       ) AS fac
SET
    PUNTAJE = det_sa.PUNTAJE * fac.FACTOR_AJUSTE
WHERE det_sa.CODIGO      = fac.CODIGO
  AND det_sa.NEVALUACION = fac.NEVALUACION;

-- Aplicar tope final (máximo 0.6) a las puntuaciones SA en campañas tipo mixto
UPDATE det_sa
FROM   DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS AS det_sa,
       (
           SELECT
               sa.CODIGO,
               sa.NEVALUACION,
               (0.6 / SUM(sa.PUNTAJE)) AS FACTOR_CAP
           FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS AS sa
           INNER JOIN DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS AS eje
               ON eje.REG_EJECUTIVO = SUBSTR(sa.CODIGO, 8)
           WHERE TRIM(eje.SUB_EQUIPO) IN ('BNB','BNC','CD','CONV_TLV','EC','PP','HIP','R_CO','R_MULTI','SEG','TC')
           GROUP BY 1,2
           HAVING SUM(sa.PUNTAJE) > 0.6
       ) AS cap
SET
    PUNTAJE = det_sa.PUNTAJE * cap.FACTOR_CAP
WHERE det_sa.CODIGO      = cap.CODIGO
  AND det_sa.NEVALUACION = cap.NEVALUACION;
