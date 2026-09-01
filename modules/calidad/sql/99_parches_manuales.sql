-- =====================================================================
-- 99_PARCHES_MANUALES.SQL
-- Plantillas de consultas SQL para realizar parches manuales.
-- Copia, edita los parámetros indicados y ejecuta en tu cliente SQL.
-- =====================================================================

-- =====================================================================
-- PLANTILLA 1: PARCHE MANUAL DE NOTAS EN SPEECH ANALYTICS
-- Copia la evaluación de un ejecutivo base (correcto) a otro nuevo (incorrecto/0).
-- =====================================================================

-- 1. [CONFIGURACIÓN] Define tus parámetros de entrada:
--    @NUEVO_REGISTRO:  Registro del ejecutivo a parchar (ej. 'B12345')
--    @BASE_REGISTRO:   Registro del ejecutivo con la nota correcta (ej. 'B99999')
--    @PERIODO:         Período a parchar (ej. '202606')
--    @PRODUCTO:        Producto/sala de la evaluación (ej. 'PP')
--    @NEVALUACION:     Número de evaluación (ej. 1 o 2)

-- 2. [EJECUCIÓN] Ejecutar bloque de consultas:

-- PASO A: Eliminar la evaluación anterior del ejecutivo a parchar para evitar duplicados
DELETE FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS
WHERE PERIODO = '202606'                -- <-- REEMPLAZAR PERIODO
  AND PRODUCTO = 'PP'                   -- <-- REEMPLAZAR PRODUCTO
  AND REG_EV = 'B12345'                 -- <-- REEMPLAZAR NUEVO_REGISTRO
  AND NEVALUACION = 1;                  -- <-- REEMPLAZAR NEVALUACION


-- PASO B: Copiar la evaluación del caso base al ejecutivo destino
INSERT INTO DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS
(
    PERIODO,
    PRODUCTO,
    REG_EV,
    CATEGORIA,
    OBTENIDO,
    NEVALUACION,
    ESPERADO,
    PESO_CATEGORIA,
    PESO_GRUPO,
    PUNTAJE,
    FLAG,
    GRUPO_CATEGORIA,
    CODIGO
)
SELECT
    PERIODO,
    PRODUCTO,
    'B12345' AS REG_EV,                 -- <-- REEMPLAZAR NUEVO_REGISTRO
    CATEGORIA,
    OBTENIDO,
    1 AS NEVALUACION,                   -- <-- REEMPLAZAR NEVALUACION
    ESPERADO,
    PESO_CATEGORIA,
    PESO_GRUPO,
    PUNTAJE,
    FLAG,
    GRUPO_CATEGORIA,
    PERIODO || '_' || 'B12345' AS CODIGO -- <-- REEMPLAZAR NUEVO_REGISTRO
FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS
WHERE PERIODO = '202606'                -- <-- REEMPLAZAR PERIODO
  AND PRODUCTO = 'PP'                   -- <-- REEMPLAZAR PRODUCTO
  AND REG_EV = 'B99999'                 -- <-- REEMPLAZAR BASE_REGISTRO
  AND NEVALUACION = 1;                  -- <-- REEMPLAZAR NEVALUACION


-- =====================================================================
-- PLANTILLA 2: CORRECCIÓN DE RESPUESTA EN PURE CLOUD (TABLA PRE)
-- Modifica la respuesta original en base a la información de errores (Excel).
-- =====================================================================

-- [CONFIGURACIÓN Y EJECUCIÓN] Reemplaza los filtros e indica la respuesta correcta (Debe Decir):
UPDATE DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE
SET answerText = 'SI'                   -- <-- REEMPLAZAR POR EL "DEBE DECIR" (ej. 'SI', 'NO')
WHERE TRIM(conversationId) = '22d085d1-1557-41cf-b328-23c2500dd2cc' -- <-- REEMPLAZAR ConID
  AND OREPLACE(OREPLACE(questionGroupName, CHR(13), ''), CHR(10), '') = 'REGISTRO' -- <-- REEMPLAZAR GRUPO
  -- Puedes buscar la pregunta por texto exacto (ITEM) quitando saltos de línea:
  AND OREPLACE(OREPLACE(questionText, CHR(13), ''), CHR(10), '') LIKE '%Cuota%'; -- <-- REEMPLAZAR COINCIDENCIA DE PREGUNTA/ITEM


-- =====================================================================
-- PLANTILLA 3: DUPLICACIÓN / PARCHE MANUAL DE NOTA EN PURE CLOUD
-- Copia la evaluación manual de un ejecutivo base (origen) a otro ejecutivo destino.
-- Tabla objetivo: DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD
-- =====================================================================

-- 1. [CONFIGURACIÓN] Define tus parámetros de entrada:
--    @NUEVO_REGISTRO:  Registro del ejecutivo a parchar (ej. 'B12345')
--    @BASE_REGISTRO:   Registro del ejecutivo con la evaluación base (ej. 'B99999')
--    @PERIODO:         Período a parchar (ej. '202606')
--    @NUM_EVALUACION:  Número de evaluación (ej. 1 o 2)

-- 2. [EJECUCIÓN] Ejecutar bloque de consultas:

-- PASO A: Eliminar la evaluación anterior del ejecutivo a parchar para evitar duplicados
DELETE FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD
WHERE PERIODO = '202606'                -- <-- REEMPLAZAR PERIODO
  AND REG_EJECUTIVO = 'B12345'          -- <-- REEMPLAZAR NUEVO_REGISTRO (Destino)
  AND NUM_EVALUACION = 1;               -- <-- REEMPLAZAR NUM_EVALUACION


-- PASO B: Copiar todas las preguntas y pesos de la evaluación base al ejecutivo destino
INSERT INTO DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD
(
    CODIGO,
    PERIODO,
    CONID,
    FECHA_CREADO,
    FECHA_MODIFICADO,
    FECHA_PUBLICADO,
    FECHA_VENTA,
    COLA,
    REG_EJECUTIVO,
    DNI,
    PLANTILLA,
    NUM_EVALUACION,
    REG_EVALUADOR,
    AGRUPACION,
    GRUPO_PREGUNTAS,
    PREGUNTA,
    ID_PREGUNTA,
    RESPUESTA,
    ID_RESPUESTA,
    CANT_PREGUNTAS,
    CANT_RESPUESTAS,
    PESO_GRUPO,
    PESO_GRUPO_OBT,
    PESO_PREGUNTA,
    PESO_PREGUNTA_OBT,
    PREG_VALIDA,
    PREG_CRITICA,
    ES_ERROR,
    COMENTARIO
)
SELECT
    PERIODO || '_' || 'B12345' AS CODIGO, -- <-- REEMPLAZAR NUEVO_REGISTRO
    PERIODO,
    CONID,
    FECHA_CREADO,
    FECHA_MODIFICADO,
    FECHA_PUBLICADO,
    FECHA_VENTA,
    COLA,
    'B12345' AS REG_EJECUTIVO,            -- <-- REEMPLAZAR NUEVO_REGISTRO
    DNI,
    PLANTILLA,
    1 AS NUM_EVALUACION,                  -- <-- REEMPLAZAR NUM_EVALUACION
    REG_EVALUADOR,
    AGRUPACION,
    GRUPO_PREGUNTAS,
    PREGUNTA,
    ID_PREGUNTA,
    RESPUESTA,
    ID_RESPUESTA,
    CANT_PREGUNTAS,
    CANT_RESPUESTAS,
    PESO_GRUPO,
    PESO_GRUPO_OBT,
    PESO_PREGUNTA,
    PESO_PREGUNTA_OBT,
    PREG_VALIDA,
    PREG_CRITICA,
    ES_ERROR,
    COMENTARIO
FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD
WHERE PERIODO = '202606'                -- <-- REEMPLAZAR PERIODO
  AND REG_EJECUTIVO = 'B99999'          -- <-- REEMPLAZAR BASE_REGISTRO (Origen)
  AND NUM_EVALUACION = 1;               -- <-- REEMPLAZAR NUM_EVALUACION


-- NOTA POST-PARCHE:
-- Luego de aplicar el parche manual en Pure Cloud (o Speech Analytics),
-- se debe re-ejecutar el script '05_consolidacion_nota_final.sql' para
-- recalcular las notas finales consolidadas antes de proceder al cierre mensual.
