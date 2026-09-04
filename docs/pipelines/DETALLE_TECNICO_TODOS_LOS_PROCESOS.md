# Plataforma Calidad Televentas — Detalle Técnico de Todos los Procesos
> Referencia técnica completa. Para frecuencias y contexto de negocio, ver `GESTION_OPERATIVA.md`.  
> Stack: Python · FastAPI · Polars · Teradata (`DLAB_GEC`) · SQL Server (`DB_SPEECH`) · React 18 SPA

---

## ÍNDICE

1. [Calidad NTD — Pipeline 5 Fases](#1-calidad-ntd--pipeline-5-fases)
2. [Consumo Base — Pipeline 5 Fases](#2-consumo-base--pipeline-5-fases)
3. [Dotación — Pipeline 4 Fases + Licencias SA](#3-dotaci%C3%B3n--pipeline-4-fases--licencias-sa)
4. [Cierre Mensual](#4-cierre-mensual)
5. [Auditoría PA-TC con Gemini](#5-auditor%C3%ADa-pa-tc-con-gemini)
6. [Auditoría WhatsApp con Gemini](#6-auditor%C3%ADa-whatsapp-con-gemini)
7. [Transcripciones Verint](#7-transcripciones-verint)
8. [Pipeline Speech — Teradata → SQL Server](#8-pipeline-speech--teradata--sql-server)
9. [Genesys — Audio y Outlook](#9-genesys--audio-y-outlook)
10. [Pilotos](#10-pilotos)
11. [Convenios](#11-convenios)
12. [Diccionario de Tablas DLAB_GEC](#12-diccionario-de-tablas-dlab_gec)

---

## 1. Calidad NTD — Pipeline 5 Fases

**Orquestador:** [quality_orchestrator.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/use_cases/quality_orchestrator.py)  
**Cómo ejecutar:** UI → Sección *Calidad* → Botón *Ejecutar Pipeline Completo* (o fases individuales)

### 1.1 Diagrama End-to-End de Calidad NTD

```mermaid
flowchart TD
    subgraph S_ING ["1. Fases de Ingesta (Fases 1 a 3)"]
        IN1["Insight Cloud\n(Query: EVALUATIONS)"] -->|"phase1_ingest_insight.py\nPlantilla P008"| T1[("DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE\n(Evaluaciones Manuales)")]
        IN2["Verint WFO SA\n(Export_Calidad_*.xlsx)"] -->|"phase2_ingest_verint.py\nPlantilla P001"| T2[("DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS\n(Evaluaciones Speech Analytics)")]
        IN3["SharePoint Calidad\n(ACCION_TOMADA.xlsx)"] -->|"phase3_ingest_accion_tomada.py\nPlantilla P004"| T3[("DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE\n(Observaciones y Severidad)")]
    end

    subgraph S_SQL ["2. Pipeline de Transformación SQL (Fase 4)"]
        T1 --> SQL1["01_evaluacion_manual_pc.sql\nHomologaciones y cálculo de pesos PC"]
        SQL1 --> D1[("DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD")]

        T2 --> SQL2["02_sa_marcacion_ventas_lpdp.sql\nMarcación ventas TC/PP/LPDP"]
        SQL2 --> SQL3["03_sa_calculo_pesos_unpivot.sql\nUnpivot categorías SA"]
        SQL3 --> SQL4["04_sa_ajustes_curva.sql\nPesos x Maestra SA + Curvas y Topes"]
        SQL4 --> SQL4b["04_b_sa_parche_nota_cero.sql\nParche automáticos mixtos nota 0"]
        SQL4b --> D2[("DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS")]

        D1 --> SQL5["05_consolidacion_nota_final.sql\nPonderación PC + SA y Topes"]
        D2 --> SQL5
        SQL5 --> NF[("DLAB_GEC.M_EXP_CALIDAD_NOTA_FINAL")]
        NF --> VNF["VIEW: DLAB_GEC.V_EXP_CALIDAD_NOTA_FINAL"]
    end

    subgraph S_NTD ["3. Proceso No Te Dejes - NTD (Fase 5)"]
        T1 --> SQL6["06_carga_ntd.sql\nCruce con Observaciones"]
        T3 --> SQL6
        SQL6 --> NTD_TAB[("DLAB_GEC.M_EXP_NOT_TO_DO\n(Histórico acumulado)")]
        SQL6 --> NTD_NEW[("DLAB_GEC.M_EXP_NTD_OBSERVACIONES_NEW")]
    end

    style T1 fill:#e1f5fe,stroke:#0288d1
    style T2 fill:#e1f5fe,stroke:#0288d1
    style T3 fill:#e1f5fe,stroke:#0288d1
    style D1 fill:#dff0d8,stroke:#4caf50
    style D2 fill:#dff0d8,stroke:#4caf50
    style NF fill:#fff9c4,stroke:#fbc02d
    style VNF fill:#fff9c4,stroke:#fbc02d
    style NTD_TAB fill:#fce4ec,stroke:#e91e63
    style NTD_NEW fill:#fce4ec,stroke:#e91e63
```

**Archivos SQL:**

| Script | Qué hace |
|---|---|
| [00_setup_homologaciones.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/00_setup_homologaciones.sql) | Crea tablas de homologación (setup único) |
| [01_evaluacion_manual_pc.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/01_evaluacion_manual_pc.sql) | `DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE` → `DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD` |
| [02_sa_marcacion_ventas_lpdp.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/02_sa_marcacion_ventas_lpdp.sql) | SA + marcación ventas TC/PP/LPDP |
| [03_sa_calculo_pesos_unpivot.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/03_sa_calculo_pesos_unpivot.sql) | Unpivot categorías SA, promedios |
| [04_sa_ajustes_curva.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/04_sa_ajustes_curva.sql) | Pesos × `DLAB_GEC.M_EXP_CALIDAD_MAESTRA_SA` + curvas + topes |
| [04_b_sa_parche_nota_cero.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/04_b_sa_parche_nota_cero.sql) | Parche automático SA mixtos nota=0 |
| [05_consolidacion_nota_final.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/05_consolidacion_nota_final.sql) | PC + SA → `DLAB_GEC.M_EXP_CALIDAD_NOTA_FINAL` |
| [06_carga_ntd.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/06_carga_ntd.sql) | `DLAB_GEC.M_EXP_NOT_TO_DO` + `DLAB_GEC.M_EXP_NTD_OBSERVACIONES_NEW` |
| [99_parches_manuales.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/sql/99_parches_manuales.sql) | Correcciones puntuales post-cierre |

---

## 2. Consumo Base — Pipeline 5 Fases

**Orquestador:** [consumo_orchestrator.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/consumo/use_cases/consumo_orchestrator.py)

```mermaid
flowchart LR
    F1["Fase 1\nInsight Cloud\nDescarga 7 queries\nphase1_insight_ingest.py"] --> TD1[("Teradata\nTablas staging consumo")]
    F2["Fase 2\nCD40K_NEW.xlsx\n(SharePoint refresh)\nphase2_cd40k.py"] --> TD2[("DLAB_GEC.T_SP_CD40K")]
    F3["Fase 3\nSQL Server Market\nBN_DESEMBOLSOS_GENERAL\nphase3_desembolsos.py"] --> TD3[("DLAB_GEC.T_VENTAS_BPE_MARKET")]
    
    TD1 --> F4["Fase 4\nSQL Pipeline Consumo\n(Transformaciones y cruces)\nphase4_sql_scripts.py"]
    TD2 --> F4
    TD3 --> F4
    F4 --> F5["Fase 5\nConsolidado Selección\nphase5_selection.py"]
```

**Notas técnicas:**
- Fase 1: itera sobre `consumo_insumos_config` en `config.json` — cada entrada define una query de Insight y su tabla destino.
- Fase 2: acepta `CD40K_NEW.xlsx` o `CD40K.xlsx`; hace auto-refresh de SharePoint vía COM.
- Fase 3: se omite silenciosamente si `SQLSERVER_SERVER` no está en `.env`.
- Fase 5: llama `run_selection_transformation` del `sql_executor.py`.

---

## 3. Dotación — Pipeline 4 Fases + Licencias SA

**Orquestador:** [dotacion_orchestrator.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/dotacion/use_cases/dotacion_orchestrator.py)  
**Config:** [dotacion_config.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/dotacion/dotacion_config.py)  
**Cómo ejecutar:** UI → Sección *Dotación* → Botón *Ejecutar Pipeline Dotación* (o *Ejecutar Licencias SA*)

```mermaid
flowchart TD
    subgraph INSUMOS ["Insumos de Entrada (OneDrive / Local)"]
        I1["INPUT_WORKBOOK\n(Mes Anterior)"]
        I2["Consolidado Planilla\nausentismo YYYYMM.xlsx"]
        I3["Dotación Ausencias Select\n(SELECT_DOTACION_FILE)"]
        I4["Gestión de Vacaciones\ny Horarios YYYY.xlsx"]
        I5["TELEVENTAS_EJECUTIVOS\n(Mes Anterior)"]
    end

    subgraph PIPELINE ["Pipeline Dotación (Fases 1 a 4)"]
        I1 & I2 & I3 & I4 --> F1["Fase 1 — Limpieza\nfase1_limpieza.py\nLimpia AVANCE DIARIO, RESULTADOS\ny hojas de productos"]
        F1 --> F2["Fase 2 — Sincronización Roster\nfase2_sincronizacion.py\nAltas, Bajas y Antigüedad (R0 -> R1 -> R2 -> R3)"]
        F2 --> F3["Fase 3 — Distribución de Cuotas\nfase3_distribucion.py\nCálculo de vacaciones y reparto a 4 analistas\n(Karin +12% en SELECT; BN_B primero)"]
        F3 --> F4["Fase 4 — Televentas Ejecutivos\nfase4_televentas.py\nGenera archivo preliminar de planilla activa"]
    end

    subgraph SALIDAS ["Entregables Generados"]
        F3 --> O1["EQUIPO DE VENTAS {MES} {YYYY}_PRELIMINAR.xlsx\n(Hojas protegidas con bloqueo estricto)"]
        F4 --> O2["{MES}_TELEVENTAS_EJECUTIVOS_PRELIMINAR.xlsx"]
    end

    subgraph TERADATA ["Ingesta a Teradata (Vía Web Uploader)"]
        O2 -->|"Uploader Web: Plantilla P021\n(Validación humana previa)"| TD1[("DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS")]
        TD1 -->|"Hook automático post-carga\nprocess_televentas_grouped()"| TD2[("DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED")]
    end

    subgraph LICENCIAS ["Sub-proceso Paralelo: Licencias SA"]
        L_IN["LICENCIAS_SA_{YYYY}.xlsx\n(Mes Anterior)"] --> FL["Licencias SA\nfase_licencias_sa.py\nExcluye BackOffice permanente (preserva interinos)"]
        FL --> L_OUT["Pestaña nuevo periodo en\nLICENCIAS_SA_{YYYY}.xlsx"]
    end
```

### 3.1 Mapa de Rutas de Insumos y Entregables (OneDrive)

El orquestador resuelve automáticamente la carpeta base de OneDrive del usuario (`OneDrive - Interbank` o `OneDrive`):

| Insumo / Entregable | Tipo | Ruta Relativa en OneDrive | Archivo Dinámico por Período |
| :--- | :--- | :--- | :--- |
| **Plantilla Mes Anterior** | Insumo | `1. EXPERIENCIA DE COMPRA\EQUIPO DE VENTAS {YYYY}\` | `{M_ANT} EQUIPO DE VENTAS {MES_ANT_UPPER} {Y_ANT}.xlsx` |
| **Consolidado Ausentismo** | Insumo | `Dotación {YYYY}\Dotación {YYYYMM}\` | `Consolidado Planilla ausentismo {YYYYMM}.xlsx` |
| **Dotación Select** | Insumo | `Dotación {YYYY}\Dotación {YYYYMM}\Equipo Select\` | `Dotacion_Ausencias_Select_{MesCap}{YY}.xlsx` |
| **Gestión de Vacaciones** | Insumo | `1. EXPERIENCIA DE COMPRA\GESTIÓN {YYYY}\VACACIONES\` | `Gestión de Vacaciones y Horarios {YYYY}.xlsx` (hoja: `Programación de Fechas {YYYY}`) |
| **Televentas Mes Anterior** | Insumo | `1. EXPERIENCIA DE COMPRA\GESTIÓN {YYYY}\DOTACION\TERADATA\` | `{M_ANT} {MES_ANT_UPPER}_TELEVENTAS_EJECUTIVOS.xlsx` |
| **Libro Maestro Licencias** | Insumo / Salida | `1. EXPERIENCIA DE COMPRA\GESTIÓN {YYYY}\DOTACION\` | `LICENCIAS_SA_{YYYY}.xlsx` |
| **Equipo de Ventas Final** | Entregable | `1. EXPERIENCIA DE COMPRA\EQUIPO DE VENTAS {YYYY}\` | `{M_ACT} EQUIPO DE VENTAS {MES_ACT_UPPER} {YYYY}_PRELIMINAR.xlsx` |
| **Televentas Final** | Entregable | `1. EXPERIENCIA DE COMPRA\GESTIÓN {YYYY}\DOTACION\TERADATA\` | `{M_ACT} {MES_ACT_UPPER}_TELEVENTAS_EJECUTIVOS_PRELIMINAR.xlsx` |

**Reglas de negocio críticas:**
- **Seguridad en RESULTADOS:** La hoja `RESULTADOS` se limpia en filas manuales (18, 21, 24, 27) y se re-bloquea estrictamente a nivel de celda (`locked=True`, `ws.protection.sheet=True`) para impedir modificaciones manuales de usuario.
- **Reparto a 4 analistas:** Las hojas con 2 evaluaciones (`BN_B`, `PP`, `SEG`, `CxC 1`) se reparten equitativamente primero. Karin absorbe su meta adicional (+12%) en hojas de 1 evaluación (`SELECT`).
- **Licencias SA:** La función `is_backoffice()` excluye puestos BackOffice permanentes pero preserva asesores BO interinos.
- **Ingesta a Teradata:** El pipeline no sube directamente a Teradata para permitir validación humana del archivo preliminar. La subida se realiza mediante la plantilla **`P021-TELEVENTAS_EJECUTIVOS`** en la web, la cual ejecuta automáticamente el hook para generar `DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED`.

---

## 4. Cierre Mensual

**Orquestador:** [cierre_orchestrator.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/cierre/use_cases/cierre_orchestrator.py)  
**Cómo ejecutar:** UI → Sección *Cierre* → Seleccionar período cerrado → Elegir scripts a ejecutar

```mermaid
flowchart TD
    NF[("DLAB_GEC.M_EXP_CALIDAD_NOTA_FINAL")] --> S1
    V[("VIEW: DLAB_GEC.V_EXP_CALIDAD_NOTA_FINAL")] --> S1

    S1["01_auditoria_y_cierre.sql"] --> G1[("DLAB_GEC.M_EXP_CALIDAD_NOTAS_TOTAL_GERENCIAL")]
    EJ[("DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED")] -->|"UPDATE jerarquías:\nSupervisor, Jefe, Equipo"| G1

    NF --> S3["03_consolidado_notas_cierre.sql"]
    S3 --> G3[("DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE")]
    EJ -->|"UPDATE jerarquías"| G3

    KV[("DLAB_GEC.T_EXP_KRI_VENTAS_SINAUDIO")] --> S2["02_kri_resumen_total.sql"]
    KT[("DLAB_GEC.T_EXP_KRI_TELF_NO_AUTORIZADO")] --> S2
    S2 --> G2[("DLAB_GEC.M_KRI_RESUMEN_TOTAL")]

    style G1 fill:#d9edf7
    style G2 fill:#d9edf7
    style G3 fill:#d9edf7
```

**Scripts:**

| Script | Tabla destino | Descripción |
|---|---|---|
| [01_auditoria_y_cierre.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/cierre/sql/01_auditoria_y_cierre.sql) | `DLAB_GEC.M_EXP_CALIDAD_NOTAS_TOTAL_GERENCIAL` | Notas + jerarquía organizativa para Power BI gerencial |
| [02_kri_resumen_total.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/cierre/sql/02_kri_resumen_total.sql) | `DLAB_GEC.M_KRI_RESUMEN_TOTAL` | Ventas sin audio + teléfonos no autorizados |
| [03_consolidado_notas_cierre.sql](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/cierre/sql/03_consolidado_notas_cierre.sql) | `DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE` | Consolidado de notas con jerarquía para reportes |

---

## 5. Auditoría PA-TC con Gemini

**Archivo fuente:** [audit_cumplimiento_pa_tc.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/tools/audit_cumplimiento_pa_tc.py)  
**Cómo ejecutar:** `.\.venv\Scripts\python modules\calidad\tools\audit_cumplimiento_pa_tc.py`  
**Input auto-detectado:** `Solicitud Cumplimiento TC YYYY.xlsx` en raíz del proyecto  
**Output:** `Solicitud Cumplimiento TC YYYY_Auditada.xlsx` + `logs/audit_pago_automatico.log`

### 5.1 Diagrama de Flujo Técnico Detallado

```mermaid
flowchart TD
    subgraph INSUMO["1. Archivo de Entrada"]
        EXCEL["Solicitud Cumplimiento TC 2026.xlsx\n(Filas con DNI, Registro y Fecha Solicitud)"]
    end

    subgraph PASO1["2. Búsqueda Telefónica en Teradata"]
        TD_QUERY["TeradataService: Consulta DLAB_GEC\nFiltra por DNI (zfill 8 dígitos)"]
        PHONES["Lista de Teléfonos de Contacto\n(Celulares y Fijos asociados al cliente)"]
        EXCEL --> TD_QUERY --> PHONES
    end

    subgraph PASO2["3. Resolución en Genesys Cloud API v2"]
        CHROME_CDP["GenesysBrowserAutomation:\nChrome vía CDP (Puerto 9222)\nExtrae Bearer Token activo"]
        GENESYS_API["POST /api/v2/analytics/conversations/details/query\nFiltro: Intervalo (+/- 2 días) + Teléfonos + UserID Asesor"]
        CONV_MATCH["Identificación de Llamada:\n• conversationId (UUID)\n• Fecha y Hora exacta de inicio"]
        PHONES --> GENESYS_API
        CHROME_CDP --> GENESYS_API
        GENESYS_API --> CONV_MATCH
    end

    subgraph PASO3["4. Extracción de Audio/Transcripción en Verint"]
        VERINT_REST["VerintAPIClient:\nPOST GetInteractionTranscriptionResult\n(API REST directa con credenciales VERINT_USER/PASS)"]
        TRANSCRIPT["Transcripción estructurada por turnos:\n[mm:ss] Asesor / Cliente + Palabras exactas\nCaché local en data/transcripciones/"]
        CONV_MATCH --> VERINT_REST --> TRANSCRIPT
    end

    subgraph PASO4["5. Auditoría Cognitiva con Gemini LLM"]
        PROMPT["GeminiClient (Modelo: gemini-3.1-flash-lite):\nPrompt de Auditoría Bancaria Senior\nEvalúa Afiliación a Pago / Débito Automático"]
        DECISION{"Clasificación LLM\n(JSON Estricto)"}
        R_NO["NO_ACEPTA\n• Minuto y segundo exacto del rechazo\n• Cita textual del cliente\n• Cita textual del asesor"]
        R_SI["ACEPTA\n• Minuto y segundo de aceptación\n• Cita textual de conformidad"]
        R_NONE["NO_OFRECIDO\n• Confirmación de no ofrecimiento en llamada"]
        TRANSCRIPT --> PROMPT --> DECISION
        DECISION --> R_NO
        DECISION --> R_SI
        DECISION --> R_NONE
    end

    subgraph PASO5["6. Persistencia y Respaldo"]
        WRITE_EXCEL["Actualización Celda por Celda en Excel:\n• Escribe Estado y Marca Temporal (mm:ss)\n• Auto-guardado progresivo ante cortes"]
        BACKUP["Generación de Archivo Final:\nSolicitud Cumplimiento TC 2026_Auditada.xlsx"]
        R_NO --> WRITE_EXCEL
        R_SI --> WRITE_EXCEL
        R_NONE --> WRITE_EXCEL
        WRITE_EXCEL --> BACKUP
    end
```

### 5.2 Desglose Paso a Paso del Flujo

1. **Lectura del Excel de Cumplimiento:** Detecta automáticamente `Solicitud Cumplimiento TC YYYY.xlsx` en la raíz. Lee fila por fila los registros pendientes de auditoría (DNI, código de asesor y fecha estimada).
2. **Cruce Telefónico en Teradata:** Con el DNI normalizado a 8 dígitos (`zfill(8)`), consulta en las tablas maestras de `DLAB_GEC` todos los números telefónicos registrados para ese cliente.
3. **Localización de Llamada en Genesys Cloud:** Mediante `GenesysBrowserAutomation` se conecta por Chrome DevTools Protocol (CDP) para reutilizar la sesión corporativa y obtener el Bearer Token. Envía una consulta analítica a `https://api.mypurecloud.com/api/v2/analytics/conversations/details/query` filtrando por teléfono, usuario y una ventana de tiempo de $\pm 2$ días respecto a la fecha de la solicitud, obteniendo el `conversationId` exacto.
4. **Descarga de Transcripción Verint:** `VerintAPIClient` consume directamente el endpoint REST `GetInteractionTranscriptionResult` de Verint WFO sin necesidad de interfaz gráfica. Convierte los milisegundos de cada turno de habla a formato `[mm:ss]` separando las intervenciones de "Asesor" y "Cliente".
5. **Auditoría Focalizada con Gemini:** El diálogo estructurado se envía al modelo `gemini-3.1-flash-lite` con temperatura 0.0 y salida JSON estricta. El modelo evalúa:
   - `NO_ACEPTA`: El asesor ofreció pero el cliente declinó (registra `timestamp_cliente` en `mm:ss` y citas textuales).
   - `ACEPTA`: El cliente consintió la afiliación explícitamente.
   - `NO_OFRECIDO`: No hubo mención de pago/débito automático.
6. **Escritura y Salvaguarda Progresiva:** El resultado se escribe celda por celda en el archivo Excel tras cada llamada analizada, evitando pérdida de avance ante interrupciones de red.

---

## 6. Auditoría WhatsApp con Gemini

**Archivo:** [run_transcript_audit.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/verint/tools/run_transcript_audit.py)  
**Cómo ejecutar:** `.\.venv\Scripts\python modules\verint\tools\run_transcript_audit.py`  
**Input:** `data/input/auditorias_wsp/*.docx` + `Plantillas TLV WhatsApp.xlsx`  
**Output:** Excel gerencial con 2 pestañas (*Resumen_Evaluaciones* + *Detalle_Hallazgos*)

```mermaid
flowchart LR
    D[".docx WhatsApp auditado\n(Export chat)"] -->|"wsp_docx_extractor.py\nParsea turnos de chat"| E["Transcripción estructurada"]
    PL["Plantillas TLV WhatsApp.xlsx\n(Mensajes oficiales permitidos)"] -->|"wsp_rules.py\nCarga reglas y textos"| E
    E -->|"auditor.py\nGemini 3.1 Flash Lite"| A["Evaluación en 3 Ejes:\n• Gramática → Leve\n• Cumplimiento protocolo → Medio\n• Trato al cliente → Grave"]
    A -->|"excel_presenter.py"| XL["Reporte Excel Gerencial\n(Resumen_Evaluaciones + Detalle_Hallazgos)"]
```

**Ejes de evaluación:**
- **Gramática** → Leve
- **Cumplimiento del protocolo** → Medio
- **Trato con el cliente** → Grave
- **Regla especial:** si el cliente proporcionó su DNI antes de que el asesor lo solicitara, se aplica la excepción "DNI Reciente Previo" y no se computa penalización.

---

## 7. Transcripciones Verint

Existen **tres variantes** operativas según la necesidad:

### 7a. Barrido Masivo (Batch)

**Archivo:** [batch_verint_extractor.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/verint/tools/batch_verint_extractor.py)

```mermaid
flowchart LR
    T[("DLAB_GEC\nPendientes sin transcripción")] -->|"get_pending_calls_from_teradata\n(Filtro PERIODO=YYYYMM)"| B["run_batch_extraction\nReutiliza 1 sesión Verint API\nModo headless"]
    B --> TXT["Archivos locales:\ndata/transcripciones/TRANSCRIPT_conid.txt"]
```

### 7b. Descarga para PA-TC (desde Excel)

**Archivo:** [download_transcripts_from_verint.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/verint/tools/download_transcripts_from_verint.py)

```mermaid
flowchart LR
    XL["Solicitud Cumplimiento TC 2026.xlsx\n(o versión auditada)"] -->|"Lee conversationIds UUID"| V["VerintAPIClient\nREST directo sin navegador"]
    V --> OUT["data/transcripciones_pa/\nTRANSCRIPT_conid.txt"]
```

---

## 8. Pipeline Speech — Teradata → SQL Server

**Archivo:** [speech_orchestrator.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/speech/use_cases/speech_orchestrator.py)  
**Servicio TIPO_LEAD:** [insight_lead_service.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/speech/services/insight_lead_service.py)

```mermaid
flowchart TD
    TD[("DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD")] -->|"extract_interactions\n(Filtro por plantilla, ej: Exp. Compra - TC)"| INT["Lista de Interacciones Evaluadas"]

    INT -->|"get_tipos_lead_batch\nInsightLeadService (session_summary)"| IL["Mapeo TIPO_LEAD"]

    INT -->|"extract_transcripts_from_verint\nVerintAPIClient REST"| TR["Transcripciones\nTRANSCRIPT_conid.txt"]

    INT --> MERGE["Consolidación de atributos:\nCONID, PRODUCTO, FECHA_LLAMADA, DNI,\nREGISTRO, TIPO_LEAD, TRANSCRIPCION_TEXTO"]
    IL --> MERGE
    TR --> MERGE

    MERGE -->|"SpeechDbRepository\nUpsert en lotes de batch_size=200"| SS[("SQL Server DB_SPEECH\ntabla dbo.TRANSCRIPCION")]
```

---

## 9. Genesys — Audio y Outlook

**Módulo:** `modules/genesys/`  
**Cómo ejecutar:** UI → Sección *Genesys* (o CLI: `python -m modules.genesys.genesys_downloader`)

```mermaid
flowchart LR
    OL["Outlook Desktop\nCorreos con solicitudes"] -->|"outlook_reader.py\nLectura MAPI (pywin32)"| GD["Extracción Solicitud:\nConversationId, DNI, Teléfono"]
    GD --> API["Genesys Cloud REST API v2\nConsultas Analytics e Interacciones"]
    API --> AUD["Descarga Directa de Audio:\n.mp3 / .wav a data/downloads/audios/"]

    SES["Sesión Genesys\n(Bearer Token)"] -.-> API
```

**Precisiones de Arquitectura (API vs Playwright):**
- **Genesys Cloud (100% API):** La descarga y consulta de interacciones se realiza directamente mediante la **API REST v2** de Genesys (`requests`). No se utiliza Playwright para navegación web ni descargas interactivas de audio.
- **Verint WFO (Playwright sólo para Cookies):** El único uso de Playwright en toda la plataforma es el cosechador de cookies [verint_cookie_harvester.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/verint/services/verint_cookie_harvester.py), el cual automatiza el login para obtener las cookies de sesión. Una vez capturadas las cookies, toda la extracción y descarga de transcripciones se hace vía HTTP REST con `VerintAPIClient` sin abrir navegadores.

---

## 10. Pilotos

### 10a. Piloto No Venta

**Estado:** 🚧 En desarrollo  
**Módulo:** `modules/piloto_no_venta/`

```mermaid
flowchart LR
    SRC["Llamadas marcadas\nsin venta registrada"] -->|"01_ddl_stage_no_venta.sql\nCrea estructura staging"| ST[("DLAB_GEC.T_STAGE_NO_VENTA")]
    ST -->|"02_cruce_ventas_reales.sql\nCruce con bases reales de ventas"| CR["Identificación de brechas\nNo Venta vs Conversión Real"]
```

### 10b. Piloto TCAD

**Estado:** 🚧 En desarrollo  
**Módulo:** `modules/Piloto TCAD/`

- Módulo experimental para tarjetas adicionales en proceso de estandarización.

---

## 11. Convenios

**Módulo:** `modules/convenios/`

```mermaid
flowchart LR
    SQL["modules/convenios/sql/\nScripts DDL y ETL de convenios"] --> TD[("Teradata DLAB_GEC\nTablas Maestras Convenios")]
    UC["modules/convenios/use_cases/\nOrquestador de carga mensual"] --> TD
```

- Se ejecuta a demanda ante la incorporación o actualización de convenios comerciales.

---

## 12. Diccionario de Tablas DLAB_GEC

### 12.1 Tablas de Staging (se truncan en cada ejecución)

| Tabla Completa | Descripción | Fase / Módulo | Script Python |
|---|---|---|---|
| `DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE` | Evaluaciones crudas desde Insight (1 fila = 1 pregunta evaluada, incluye toda la metadata de la interacción) | Calidad Fase 1 | [phase1_ingest_insight.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/use_cases/phases/phase1_ingest_insight.py) · Plantilla `P008-INSIGHT_07_EVALUATIONS` |
| `DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS` | Reporte Speech Analytics Verint (1 fila = 1 interacción, detecciones por categoría) | Calidad Fase 2 | [phase2_ingest_verint.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/use_cases/phases/phase2_ingest_verint.py) · Plantilla `P001-CALIDAD_SA` |
| `DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE` | Acciones tomadas (`ACCION_TOMADA.xlsx`), deduplicadas por rango de severidad | Calidad Fase 3 | [phase3_ingest_accion_tomada.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/calidad/use_cases/phases/phase3_ingest_accion_tomada.py) · Plantilla `P004-ACC_TOMADA` |
| `DLAB_GEC.T_SP_CD40K` | Ingesta manual base CD40K de Consumo | Consumo Fase 2 | [phase2_cd40k.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/consumo/use_cases/phases/phase2_cd40k.py) · Plantilla `P003-CD40K` |
| `DLAB_GEC.T_VENTAS_BPE_MARKET` | Desembolsos extraídos desde SQL Server Market | Consumo Fase 3 | [phase3_desembolsos.py](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/modules/consumo/use_cases/phases/phase3_desembolsos.py) |

### 12.2 Tablas de Homologación (setup único en Teradata)

| Tabla Completa | Descripción | Cuándo actualizar |
|---|---|---|
| `DLAB_GEC.M_EXP_CALIDAD_HOMOLOGA_GRUPO` | Equivalencias de grupos de preguntas entre formularios Insight y el estándar | Cuando Insight altera el nombre de un grupo de evaluación |
| `DLAB_GEC.M_EXP_CALIDAD_HOMOLOGA_PREGUNTA` | Equivalencias y mapeo de nombres de preguntas individuales | Cuando se detectan preguntas sin mapear en la Fase 4 |
| `DLAB_GEC.M_EXP_CALIDAD_HOMOLOGA_RESPUESTA` | Equivalencias de respuestas ("Si"/"Sí" → "SI") | Cuando Insight modifica valores de respuesta |
| `DLAB_GEC.M_EXP_CALIDAD_MAESTRA_GRUPO_PREGUNTAS_PCLOUD` | Catálogo de plantillas, grupos y preguntas homologadas de Pure Cloud | Al incorporar nuevas plantillas o formularios en Insight |
| `DLAB_GEC.M_EXP_CALIDAD_MAESTRA_SA` | Pesos y umbrales por categoría de Speech Analytics por producto | Al ajustar el modelo analítico de calidad SA |

### 12.3 Tablas de Detalle — Salida del Pipeline SQL

| Tabla Completa | Descripción | Script que escribe | Fuentes |
|---|---|---|---|
| `DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD` | Evaluaciones manuales procesadas, homologadas y con `NUM_EVALUACION` | `01_evaluacion_manual_pc.sql` | `DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE` + Homologaciones |
| `DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS` | SA con marcación de ventas, pesos aplicados, curvas y topes | `02` + `03` + `04` + `04b` | `DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS` + `DLAB_GEC.M_EXP_VENTAS_TC/PP` |
| `DLAB_GEC.M_EXP_NOT_TO_DO` | Histórico acumulado de interacciones calificadas con NTD | `06_carga_ntd.sql` | `DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE` + `DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE` |
| `DLAB_GEC.M_EXP_NTD_OBSERVACIONES_NEW` | Tabla derivada de observaciones NTD procesadas en la ejecución | `06_carga_ntd.sql` | `DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE` |

### 12.4 Tablas de Nota Final

| Tabla / Vista Completa | Descripción | Script que escribe | Fuentes |
|---|---|---|---|
| `DLAB_GEC.M_EXP_CALIDAD_NOTA_FINAL` | Nota mensual definitiva por ejecutivo y evaluación (PC + SA ponderados con caps) | `05_consolidacion_nota_final.sql` | `DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD` + `DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS` |
| `DLAB_GEC.V_EXP_CALIDAD_NOTA_FINAL` | Vista calculada sobre la nota final | DDL en `00_setup_homologaciones.sql` | `DLAB_GEC.M_EXP_CALIDAD_NOTA_FINAL` |
| `DLAB_GEC.V_EXP_CALIDAD_NOTA_SA` | Vista de nota SA aislada | DDL en `00_setup_homologaciones.sql` | `DLAB_GEC.M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS` |
| `DLAB_GEC.V_EXP_ERRORES_CALIDAD_HISTORICO` | Vista histórica de preguntas falladas | DDL en `00_setup_homologaciones.sql` | `DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD` |
| `DLAB_GEC.V_CHECK_FECHAS_NTD` | Vista de monitoreo con la última fecha de carga de las tablas PRE | DDL en `06_carga_ntd.sql` | `M_EXP_CALIDAD_PURECLOUD_PRE`, `M_EXP_NTD_OBSERVACIONES_PRE` |

### 12.5 Tablas Gerenciales — Cierre Mensual

| Tabla Completa | Descripción | Script que escribe |
|---|---|---|
| `DLAB_GEC.M_EXP_CALIDAD_NOTAS_TOTAL_GERENCIAL` | Histórico consolidado con jerarquía de mando completa (Ejecutivo, Supervisor, Jefe, Equipo) | `01_auditoria_y_cierre.sql` |
| `DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE` | Consolidado de notas para reportes de cierre oficial | `03_consolidado_notas_cierre.sql` |
| `DLAB_GEC.M_KRI_RESUMEN_TOTAL` | Métricas KRI del mes: ventas sin audio + teléfonos no autorizados | `02_kri_resumen_total.sql` |

### 12.6 SQL Server — Base Speech

| Base / Tabla | Descripción | Proceso que escribe |
|---|---|---|
| `DB_SPEECH.dbo.TRANSCRIPCION` | Repositorio de transcripciones de interacciones con `CON_ID`, `PRODUCTO`, `FECHA_LLAMADA`, `DNI`, `REGISTRO`, `TIPO_LEAD`, `TRANSCRIPCION_TEXTO` | `modules/speech/use_cases/speech_orchestrator.py` |

---

## Árbol de Archivos Clave

```
APP_CALIDAD/
├── backend/main.py                              ← API FastAPI + WebSockets en tiempo real
├── frontend/app.js                              ← React 18 SPA (interfaz gráfica completa)
├── infrastructure/
│   ├── database/database.py                     ← Conexiones y cargas optimizadas a Teradata
│   ├── scrapers/insight_downloader.py           ← Scraper / descargador de Insight Cloud
│   └── llm/gemini_client.py                    ← Cliente Gemini con reintentos y soporte JSON
├── modules/
│   ├── calidad/
│   │   ├── use_cases/phases/                    ← Fases 1 a 5 del pipeline Calidad NTD
│   │   ├── sql/00–06 + 99                       ← Scripts SQL de homologación, cálculo y NTD
│   │   ├── tools/audit_cumplimiento_pa_tc.py    ← Auditoría Gemini PA-TC
│   │   └── televentas/                          ← Gestión de M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED
│   ├── consumo/use_cases/phases/               ← Fases 1 a 5 de Base Consumo
│   ├── dotacion/
│   │   ├── phases/fase1–4 + licencias_sa        ← Pipeline de dotación y licencias Verint SA
│   │   └── dotacion_config.py                   ← Configuración de insumos de dotación
│   ├── cierre/
│   │   ├── use_cases/cierre_orchestrator.py     ← Orquestador de cierre mensual
│   │   └── sql/01–03                            ← Scripts SQL de cierre gerencial y KRI
│   ├── speech/
│   │   ├── use_cases/speech_orchestrator.py     ← Pipeline Teradata → SQL Server DB_SPEECH
│   │   └── services/insight_lead_service.py     ← Enriquecimiento TIPO_LEAD vía Insight
│   ├── verint/
│   │   ├── services/verint_api_client.py        ← Cliente REST Verint WFO
│   │   ├── services/verint_cookie_harvester.py  ← Cosechador de sesiones Verint
│   │   ├── tools/
│   │   │   ├── batch_verint_extractor.py        ← Extracción masiva de transcripciones
│   │   │   ├── download_transcripts_from_verint.py ← Descarga orientada a PA-TC
│   │   │   └── run_transcript_audit.py          ← Auditoría WhatsApp con Gemini
│   │   └── transcripciones/
│   │       ├── use_cases/auditor.py             ← Motor LLM para auditoría 3 ejes
│   │       └── extractors/                      ← Extractores para Verint y WhatsApp (.docx)
│   ├── genesys/
│   │   ├── outlook_reader.py                    ← Parser de correos y adjuntos Outlook
│   │   ├── genesys_downloader.py               ← Descargador de audios Genesys
│   │   └── services/genesys_browser.py         ← Automatización Chrome CDP y Bearer Token
│   ├── convenios/                               ← Setup y procesamiento de convenios
│   ├── piloto_no_venta/sql/01–02               ← DDL y cruce de ventas reales
│   └── Piloto TCAD/                            ← Módulo experimental TCAD
└── data/
    ├── input/proceso_calidad/                  ← Insumos Calidad (ACCION_TOMADA.xlsx, etc.)
    ├── input/proceso_consumo/                  ← Insumos Consumo (CD40K.xlsx, etc.)
    ├── input/auditorias_wsp/                   ← Insumos WhatsApp (.docx + plantillas)
    ├── transcripciones/                        ← Transcripciones en texto (.txt)
    └── transcripciones_pa/                     ← Transcripciones específicas PA-TC
```

---

*Documento técnico actualizado el 2026-09-03.*
