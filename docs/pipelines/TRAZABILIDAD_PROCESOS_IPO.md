# 🧭 Matriz de Trazabilidad Técnica End-to-End (IPO: Inputs ➔ Process ➔ Outputs)

> **Documento Oficial de Trazabilidad, Auditoría y Linaje de Datos** de la plataforma **`APP_CALIDAD`**.  
> Mapea cada proceso desde su **Origen Identificable (Inputs)**, los **Scripts y Tablas de Transformación (Process)** y los **Entregables / Tablas Productivas (Outputs)**.

---

## ⚠️ Regla de Oro Operativa: Interdependencia de Períodos Mensuales

El pipeline de **Calidad** y el pipeline de **Base Consumo** están fuertemente acoplados por diseño:

```mermaid
flowchart LR
    A["1. Dotación (Mes M)<br/>Genera Planilla Activa"] --> B["2. Base Consumo (Mes M)<br/>Fase 3: T_VENTAS_BPE_MARKET<br/>Fase 4: M_EXP_VENTAS_*"]
    B --> C["3. Calidad NTD (Mes M)<br/>02_sa cruza llamadas con ventas del Mes M"]
    C --> D["4. Cierre Mensual (Mes M)<br/>Snapshots Gerenciales"]
```

> [!CAUTION]
> **NUNCA ejecutar Base Consumo de un mes nuevo (ej. Septiembre) si aún no se ha cerrado la Fase 4 de Calidad del mes previo (ej. Agosto).**  
> Tanto la tabla de desembolsos `DLAB_GEC.T_VENTAS_BPE_MARKET` (cargada en la **Fase 3 de Consumo**) como las tablas maestras `DLAB_GEC.M_EXP_VENTAS_*` (TC, PP, CD, EC, CON - calculadas en la **Fase 4 de Consumo: `VENTAS_DN.sql`**) solo almacenan el mes activo.  
> Si se sobreescriben con el mes nuevo, el script `02_sa_marcacion_ventas_lpdp.sql` de Calidad no encontrará las ventas del mes previo y **anulará las notas de Speech Analytics (SA) de los asesores**.

---

## 📊 Matriz Exhaustiva IPO por Dominio

---

### 1. Dominio: Dotación y Staffing Mensual
* **Frecuencia:** Mensual (Días 25 al 30).
* **Propósito:** Generar el padrón oficial de personal activo, gestionar altas, bajas, antigüedad, vacaciones y repartir las cuotas de evaluación entre los 4 analistas.

```mermaid
flowchart LR
    subgraph INPUTS ["1. Inputs (Orígenes)"]
        I1["OneDrive Janesy:\nEQUIPO DE VENTAS anterior"]
        I2["OneDrive Rossmery:\nPlanilla Ausentismo RRHH"]
        I3["OneDrive Rossmery:\nDotación Select"]
        I4["OneDrive Janesy:\nVacaciones y Horarios"]
        I5["OneDrive Janesy:\nLICENCIAS_SA.xlsx"]
    end

    subgraph PROCESS ["2. Process (Scripts & Fases)"]
        F1["fase1_limpieza.py"]
        F2["fase2_sincronizacion.py"]
        F3["fase3_distribucion.py"]
        F4["fase4_televentas.py"]
        LIC["licencias_orchestrator.py"]
    end

    subgraph OUTPUTS ["3. Outputs (Entregables & Tablas)"]
        O1["EQUIPO DE VENTAS {MES}_PRELIMINAR.xlsx"]
        O2["{MES}_TELEVENTAS_EJECUTIVOS_PRELIMINAR.xlsx"]
        O3["DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS (vía P021)"]
        O4["DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED"]
        O5["LICENCIAS_SA_{YYYY}.xlsx actualizado"]
    end

    I1 & I2 & I3 & I4 --> F1 --> F2 --> F3 --> O1
    F3 --> F4 --> O2 --> O3 --> O4
    I5 --> LIC --> O5
```

| Origen Específico (**Inputs**) | Proceso y Transformación (**Process**) | Entregables y Tablas Finales (**Outputs**) |
| :--- | :--- | :--- |
| **OneDrive Janesy Lopez:**<br/>`1. EXPERIENCIA DE COMPRA\EQUIPO DE VENTAS {YYYY}\`<br/>• `{M_ANT} EQUIPO DE VENTAS {MES_ANT}.xlsx` | **Fase 1 — Limpieza:**<br/>• `modules/dotacion/phases/fase1_limpieza.py`<br/>Limpia hoja `AVANCE DIARIO`, filas manuales de `RESULTADOS` (18, 21, 24, 27) y resetea pestañas de productos. | **Libro de Trabajo de Calidad:**<br/>• `{M_ACT} EQUIPO DE VENTAS {MES_ACT} {YYYY}_PRELIMINAR.xlsx`<br/>*(Celdas protegidas bajo clave para resguardo de fórmulas).* |
| **OneDrive Rossmery / Jacqueline:**<br/>`Dotación {YYYY}\Dotación {YYYYMM}\`<br/>• `Consolidado Planilla ausentismo {YYYYMM}.xlsx`<br/>• `Equipo Select\Dotacion_Ausencias_Select_{Mes}.xlsx` | **Fase 2 — Sincronización Roster:**<br/>• `modules/dotacion/phases/fase2_sincronizacion.py`<br/>Cruza con planilla RRHH. Marca Bajas (rojo), Altas (amarillo) y calcula antigüedad (`R0` ➔ `R1` ➔ `R2` ➔ `R3`). | **Padrón para Carga a Teradata:**<br/>• `{M_ACT} {MES_ACT}_TELEVENTAS_EJECUTIVOS_PRELIMINAR.xlsx`<br/>*(Hoja `Hoja2` lista para subir vía cargador web).* |
| **OneDrive Janesy Lopez:**<br/>`1. EXPERIENCIA DE COMPRA\GESTIÓN {YYYY}\VACACIONES\`<br/>• `Gestión de Vacaciones y Horarios {YYYY}.xlsx`<br/>*(Hoja: Programación de Fechas)* | **Fase 3 — Distribución de Cuotas:**<br/>• `modules/dotacion/phases/fase3_distribucion.py`<br/>Descuenta vacaciones y asigna cuotas de evaluación entre 4 analistas (Karin absorbe +12% en Select; BN_B se reparte primero). | **Tablas Físicas en Teradata (`DLAB_GEC`):**<br/>• `M_EXP_TELEVENTAS_EJECUTIVOS`<br/>• `M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED`<br/>*(Generada por hook automático `process_televentas_grouped` al subir P021).* |
| **OneDrive Janesy Lopez:**<br/>`1. EXPERIENCIA DE COMPRA\GESTIÓN {YYYY}\DOTACION\`<br/>• `LICENCIAS_SA_{YYYY}.xlsx` | **Fase 4 y Licencias:**<br/>• `fase4_televentas.py`: Construye jerarquías supervisor/jefe con fallback dinámico.<br/>• `licencias_orchestrator.py`: Sincroniza personal activo y filtra puestos BackOffice permanentes. | **Archivo Maestro de Licencias:**<br/>• `LICENCIAS_SA_{YYYY}.xlsx` actualizado en OneDrive. |

---

### 2. Dominio: Base Consumo (Ventas Comerciales y Consentimiento)
* **Frecuencia:** Diaria / Mensual (Ejecución matutina).
* **Propósito:** Centralizar desembolsos, líneas de crédito, tráfico telefónico y evaluar consentimientos de llamadas.

```mermaid
flowchart TD
    subgraph INPUTS ["1. Inputs (Fuentes Externas)"]
        I1["Insight Cloud API:\n7 Consultas de Tráfico & Tipificaciones"]
        I2["SharePoint Janesy:\nCD40K_NEW.xlsx (Power Query)"]
        I3["SQL Server Market (S83VP2\\BDT):\nBN_DESEMBOLSOS_GENERAL"]
        I4["Data Warehouse Teradata:\nE_DW_VIEWS.V_FCT_RT_TC_HISTORICO\nE_DW_VIEWS_DLAB.CGR_PRESTAMOS\nE_DW_VIEWS_DLAB.CGR_EXTRACASH\nE_DW_VIEWS_DLAB.V_CD_DESEMB_HISTORICO\nE_DW_VIEWS.V_FCT_CNV_VENTAS"]
    end

    subgraph PROCESS ["2. Process (Fases & Scripts SQL)"]
        P1["Fase 1: phase1_insight_ingest.py\n(Descarga & Carga Staging P009-P015)"]
        P2["Fase 2: phase2_cd40k.py\n(Excel COM Refresh & Carga P016)"]
        P3["Fase 3: phase3_desembolsos.py\n(Extracción PyODBC & Ingesta Teradata)"]
        P4["Fase 4: sql_executor.py\n• VENTAS_DN.sql\n• CD40K.sql\n• SOURCE_TVL.sql\n• CA_CONSENTIMIENTO_DIARIO.sql\n• KRI_VENTAS_SIN_AUDIO.sql\n• TLF_NO_AUTORIZADO.sql"]
    end

    subgraph OUTPUTS ["3. Outputs (Tablas Teradata DLAB_GEC)"]
        O1[("T_SP_INSIGHT_VENTAS_TC\nT_SP_INSIGHT_VENTAS_PP\nT_SP_INSIGHT_VENTAS_CON\nM_EXP_TRAFICO_GENESIS\nM_EXP_BT_CONVERSATIONS_ATTRIBUTES")]
        O2[("T_SP_CD40K")]
        O3[("T_VENTAS_BPE_MARKET\n(Desembolsos BNB)")]
        O4[("M_EXP_VENTAS_TC\nM_EXP_VENTAS_PP\nM_EXP_VENTAS_CD\nM_EXP_VENTAS_EC\nM_EXP_VENTAS_CON\nM_EXP_VENTAS_UPG\nM_EXP_VENTAS_IL\nM_EXP_VENTAS_PA\nM_EXP_VENTAS_SEG\nM_EXP_CD40K\nT_EXP_KRI_VENTAS_SINAUDIO\nT_EXP_KRI_TELF_NO_AUTORIZADO")]
    end

    I1 --> P1 --> O1
    I2 --> P2 --> O2
    I3 --> P3 --> O3
    I4 & O1 & O2 & O3 --> P4 --> O4
```

| Origen Específico (**Inputs**) | Proceso y Transformación (**Process**) | Entregables y Tablas Finales (**Outputs**) |
| :--- | :--- | :--- |
| **Insight Cloud (PureCloud API):**<br/>• Consultas automáticas:<br/>1. `TRAFICO_GENESYS`<br/>2. `CONV_ATTRIBUTES`<br/>3. `DERIVA_BT`<br/>4. `CLOUD_MARCA_TRANSF`<br/>5. `BT_TRANSFERENCIA`<br/>6. `IVR_VENTAS`<br/>7. `EVALUATIONS` | **Fase 1 (Ingesta Insight):**<br/>• `modules/consumo/use_cases/phases/phase1_insight_ingest.py`<br/>Descarga reportes crudos, formatea tipos de datos con Polars y sube a Teradata usando plantillas `P009` a `P015`. | **Tablas Staging Teradata (`DLAB_GEC`):**<br/>• `M_EXP_TRAFICO_GENESIS`<br/>• `M_EXP_BT_CONVERSATIONS_ATTRIBUTES`<br/>• `M_EXP_DERIVA_BT_TIEMPOS`<br/>• `M_EXP_CO_CLOUD_MARCA_TRASNFERENCIA_PRE`<br/>• `M_DERIVA_BT_EV_TRANSFERENCIA`<br/>• `M_EXP_IVR_VENTAS_2022` |
| **SharePoint Janesy Lopez:**<br/>• Libro Excel: `CD40K_NEW.xlsx`<br/>*(Conexiones Power Query a bases de riesgo)* | **Fase 2 (Refresh SharePoint CD40K):**<br/>• `modules/consumo/use_cases/phases/phase2_cd40k.py`<br/>Ejecuta refresco en background vía Excel COM API (`RefreshAll`), limpia con Polars y sube a Teradata con plantilla `P016-CD40K`. | **Tabla de Líneas CD40K (`DLAB_GEC`):**<br/>• `T_SP_CD40K` |
| **SQL Server Market (`S83VP2\BDT`):**<br/>• Base de Datos: `BDT`<br/>• Tabla física: `BN_DESEMBOLSOS_GENERAL` | **Fase 3 (Extracción Desembolsos):**<br/>• `modules/consumo/use_cases/phases/phase3_desembolsos.py`<br/>Conecta vía PyODBC, extrae desembolsos del período con Polars y carga en Teradata con `clear_table=True`. | **Tabla Desembolsos BNB (`DLAB_GEC`):**<br/>• `T_VENTAS_BPE_MARKET`<br/>*(Crucial: se sobreescribe aquí en Fase 3).* |
| **Vistas Data Warehouse Teradata:**<br/>• `E_DW_VIEWS.V_FCT_RT_TC_HISTORICO`<br/>• `E_DW_VIEWS_DLAB.CGR_PRESTAMOS`<br/>• `E_DW_VIEWS_DLAB.CGR_EXTRACASH`<br/>• `E_DW_VIEWS_DLAB.V_CD_DESEMB_HISTORICO`<br/>• `E_DW_VIEWS.V_FCT_CNV_VENTAS`<br/>• `E_DW_VIEWS_DLAB.CGR_UPGRADE_HST`<br/>• `E_DW_VIEWS_DLAB.CGR_INC_LINEA_HST`<br/>• `E_DW_VIEWS_DLAB.V_CGR_PAGO_AUTOMATICO`<br/>• `E_DW_VIEWS_DLAB.V_DLAB_CGR_SEGUROS_VENTAS` | **Fase 4 (Scripts SQL Consumo):**<br/>• `modules/consumo/sql/`<br/>1. `VENTAS_DN.sql`: Cruza DW con padrón de dotación y extrae ventas oficiales del mes.<br/>2. `CD40K.sql`: Cruza `M_EXP_VENTAS_CD` con `T_SP_CD40K` y montos > 40K.<br/>3. `SOURCE_TVL.sql`: Cruce de consentimientos.<br/>4. `CA_CONSENTIMIENTO_DIARIO.sql`<br/>5. `KRI_VENTAS_SIN_AUDIO.sql`<br/>6. `TLF_NO_AUTORIZADO.sql` | **Tablas Maestras de Ventas del Mes (`DLAB_GEC`):**<br/>• `M_EXP_VENTAS_TC`<br/>• `M_EXP_VENTAS_PP`<br/>• `M_EXP_VENTAS_CD`<br/>• `M_EXP_VENTAS_EC`<br/>• `M_EXP_VENTAS_CON`<br/>• `M_EXP_VENTAS_UPG`<br/>• `M_EXP_VENTAS_IL`<br/>• `M_EXP_VENTAS_PA`<br/>• `M_EXP_VENTAS_SEG`<br/>• `M_EXP_CD40K`<br/>**Tablas Intermedias KRI:**<br/>• `T_EXP_KRI_VENTAS_SINAUDIO`<br/>• `T_EXP_KRI_TELF_NO_AUTORIZADO` |

---

### 3. Dominio: Proceso Calidad NTD y Speech Analytics
* **Frecuencia:** Semanal / Cierre Mensual.
* **Propósito:** Consolidar evaluaciones manuales (Pure Cloud) y automáticas (Speech Analytics Verint), aplicar calibraciones y alimentar el reporte No Te Dejes (NTD).

```mermaid
flowchart TD
    subgraph INPUTS ["1. Inputs (Fuentes Calidad & Consumo)"]
        I1["Insight Cloud:\nQuery EVALUATIONS (Pure Cloud)"]
        I2["Verint WFO API REST:\nExport_Calidad_{YYYYMM}.xlsx"]
        I3["SharePoint Calidad UX:\nACCION_TOMADA.xlsx"]
        I4["Consumo Fase 3 & 4:\n• T_VENTAS_BPE_MARKET\n• M_EXP_VENTAS_* (TC, PP, CD, EC, CON)"]
        I5["Maestras en Teradata:\n• M_EXP_CALIDAD_HOMOLOGA_*\n• M_EXP_MAESTRA_PESOS_SA\n• M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED"]
    end

    subgraph PROCESS ["2. Process (Fases 1 a 5 Calidad)"]
        P1["Fase 1: phase1_ingest_insight.py (P008)"]
        P2["Fase 2: phase2_ingest_verint.py (P001)"]
        P3["Fase 3: phase3_ingest_accion_tomada.py (P004)"]
        P4["Fase 4: SQL Pipeline Calidad\n• 01_evaluacion_manual_pc.sql\n• 02_sa_marcacion_ventas_lpdp.sql\n• 03_sa_calculo_pesos_unpivot.sql\n• 04_sa_ajustes_curva.sql\n• 04_b_sa_parche_nota_cero.sql\n• 05_consolidacion_nota_final.sql"]
        P5["Fase 5: phase5_ntd.py\n• 06_carga_ntd.sql"]
    end

    subgraph OUTPUTS ["3. Outputs (Tablas Productivas DLAB_GEC)"]
        O1[("M_EXP_CALIDAD_PURECLOUD_PRE")]
        O2[("M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS")]
        O3[("M_EXP_NTD_OBSERVACIONES_PRE")]
        O4[("M_EXP_CALIDAD_DETALLE_PURE_CLOUD\n(Notas Manuales 40%)")]
        O5[("M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS\n(Notas Speech 60%)")]
        O6[("M_EXP_CALIDAD_NOTA_FINAL\nVIEW: V_EXP_CALIDAD_NOTA_FINAL")]
        O7[("M_EXP_NOT_TO_DO\nM_EXP_NTD_OBSERVACIONES_NEW")]
    end

    I1 --> P1 --> O1
    I2 --> P2 --> O2
    I3 --> P3 --> O3
    O1 & O2 & I4 & I5 --> P4
    P4 --> O4 & O5 & O6
    O1 & O3 --> P5 --> O7
```

| Origen Específico (**Inputs**) | Proceso y Transformación (**Process**) | Entregables y Tablas Finales (**Outputs**) |
| :--- | :--- | :--- |
| **Insight Cloud:**<br/>• Query `EVALUATIONS`<br/>*(Formularios calificados por auditores)* | **Fase 1 — Ingesta Pure Cloud:**<br/>• `phase1_ingest_insight.py`<br/>Descarga llamadas calificadas del mes y carga con plantilla `P008-INSIGHT_07_EVALUATIONS`. | **Staging Pure Cloud (`DLAB_GEC`):**<br/>• `M_EXP_CALIDAD_PURECLOUD_PRE` |
| **Verint WFO Speech Analytics:**<br/>• API REST Directa (`export_televentas_period`)<br/>• Archivo: `Export_Calidad_{YYYYMM}.xlsx` | **Fase 2 — Ingesta Speech Analytics:**<br/>• `phase2_ingest_verint.py`<br/>Descarga transcripciones evaluadas por sofIA y carga con plantilla `P001-SPEECH_ANALYTICS`. | **Staging Speech Analytics (`DLAB_GEC`):**<br/>• `M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS` |
| **SharePoint Calidad UX / Vanessa:**<br/>• Archivo: `ACCION_TOMADA.xlsx`<br/>*(Observaciones de auditoría operativa)* | **Fase 3 — Ingesta Acción Tomada:**<br/>• `phase3_ingest_accion_tomada.py`<br/>Deduplica por severidad de error (`CRITICA` > `ALTA` > `MEDIA`) y carga con plantilla `P004-ACCION_TOMADA`. | **Staging Observaciones NTD (`DLAB_GEC`):**<br/>• `M_EXP_NTD_OBSERVACIONES_PRE` |
| **Cruces Clave en Fase 4:**<br/>• Tablas de Consumo: `T_VENTAS_BPE_MARKET` + `M_EXP_VENTAS_*`<br/>• Dotación: `M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED`<br/>• Maestra: `M_EXP_MAESTRA_PESOS_SA` | **Fase 4 — Transformación SQL Calidad:**<br/>• `01_evaluacion_manual_pc.sql`: Extrae `NUM_EVALUACION` y calcula notas PC.<br/>• `02_sa_marcacion_ventas_lpdp.sql`: **Cruza llamadas Verint con ventas del mes** asignando `NEVALUACION` 1 o 2.<br/>• `03_sa_calculo_pesos_unpivot.sql`: Unpivot y promedio `AVG()` de métricas SA.<br/>• `04_sa_ajustes_curva.sql`: Multiplica por Maestra de Pesos, aplica curvas y tope 0.6.<br/>• `04_b_sa_parche_nota_cero.sql`: Inyecta nota de sala a asesores sin llamadas SA.<br/>• `05_consolidacion_nota_final.sql`: Consolida PC (0.4) + SA (0.6) = 1.0 (o 100% PC para Select). | **Tablas Productivas de Calidad (`DLAB_GEC`):**<br/>• `M_EXP_CALIDAD_DETALLE_PURE_CLOUD`<br/>• `M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS`<br/>• `M_EXP_CALIDAD_NOTA_FINAL`<br/>• Vista: `V_EXP_CALIDAD_NOTA_FINAL`<br/>*(Alimenta directamente al Power BI de Calidad).* |
| **Staging NTD + Detalle Pure Cloud** | **Fase 5 — Reporte No Te Dejes (NTD):**<br/>• `phase5_ntd.py` ➔ `06_carga_ntd.sql`<br/>Cruza errores detectados contra reglas de fraude y no conformidades. | **Tablas Históricas NTD (`DLAB_GEC`):**<br/>• `M_EXP_NOT_TO_DO`<br/>• `M_EXP_NTD_OBSERVACIONES_NEW` |

---

### 4. Dominio: Cierre Mensual y KRIs Operativos
* **Frecuencia:** Mensual (Días 1 al 5 del mes vencido).
* **Propósito:** Congelar las notas oficiales definitivas por jerarquía para pago de comisiones y consolidar métricas KRI para Cumplimiento Normativo.

```mermaid
flowchart TD
    subgraph INPUTS ["1. Inputs (Tablas Finales del Mes)"]
        I1[("DLAB_GEC.M_EXP_CALIDAD_NOTA_FINAL\n(Generada en Calidad Fase 4)")]
        I2[("DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED\n(Dotación Histórica del Mes)")]
        I3[("DLAB_GEC.T_EXP_KRI_VENTAS_SINAUDIO\n(Generada en Consumo Fase 4)")]
        I4[("DLAB_GEC.T_EXP_KRI_TELF_NO_AUTORIZADO\n(Generada en Consumo Fase 4)")]
    end

    subgraph PROCESS ["2. Process (Scripts de Cierre)"]
        S1["01_auditoria_y_cierre.sql\nIdempotente: DELETE + INSERT + UPDATE"]
        S2["02_kri_resumen_total.sql\nAgrupación por Quincena & Idempotente"]
        S3["03_consolidado_notas_cierre.sql\nConsolidado Plano con Subgerencia"]
    end

    subgraph OUTPUTS ["3. Outputs (Snapshots Inmutables)"]
        O1[("DLAB_GEC.M_EXP_CALIDAD_NOTAS_TOTAL_GERENCIAL\n(PBI Gerencial / Comisiones)")]
        O2[("DLAB_GEC.M_KRI_RESUMEN_TOTAL\n(Riesgo Operativo / Cumplimiento)")]
        O3[("DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE\n(Reportería Analítica)")]
    end

    I1 & I2 --> S1 --> O1
    I3 & I4 --> S2 --> O2
    I1 & I2 --> S3 --> O3
```

| Origen Específico (**Inputs**) | Proceso y Transformación (**Process**) | Entregables y Tablas Finales (**Outputs**) |
| :--- | :--- | :--- |
| **Teradata Calidad:**<br/>• `DLAB_GEC.M_EXP_CALIDAD_NOTA_FINAL`<br/>**Teradata Dotación:**<br/>• `DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED` | **Script 01 (Auditoría y Cierre):**<br/>• `modules/cierre/sql/01_auditoria_y_cierre.sql`<br/>Limpia registros previos del período cerrado, copia notas de evaluación y hace `UPDATE` de Asesor, Supervisor, Jefe y Equipo desde `GROUPED`. | **Snapshot Gerencial Oficial:**<br/>• `DLAB_GEC.M_EXP_CALIDAD_NOTAS_TOTAL_GERENCIAL`<br/>*(Fuente oficial inmutable para cálculo de comisiones y PBI "CALIDAD de servicios").* |
| **Teradata Consumo / KRIs:**<br/>• `DLAB_GEC.T_EXP_KRI_VENTAS_SINAUDIO`<br/>• `DLAB_GEC.T_EXP_KRI_TELF_NO_AUTORIZADO` | **Script 02 (KRI Resumen Total):**<br/>• `modules/cierre/sql/02_kri_resumen_total.sql`<br/>Totaliza llamadas sin audio y teléfonos no autorizados por quincena para el período cerrado. | **Resumen Definitivo de Riesgos:**<br/>• `DLAB_GEC.M_KRI_RESUMEN_TOTAL`<br/>*(Entregable normativo a Riesgo Operativo).* |
| **Teradata Calidad + Dotación** | **Script 03 (Consolidado Notas Cierre):**<br/>• `modules/cierre/sql/03_consolidado_notas_cierre.sql`<br/>Genera tabla plana con desglose por Subgerencia, Negocio, Jefe y Asesor. | **Consolidado Analítico:**<br/>• `DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE` |

---

### 5. Dominio: Auditorías Cognitivas IA (Gemini LLM)
* **Frecuencia:** Mensual / A demanda.
* **Propósito:** Auditoría automática de grabaciones y chats de WhatsApp con modelos Gemini LLM para detectar vicios de consentimiento y corroborar reclamos.

```mermaid
flowchart TD
    subgraph INPUTS ["1. Inputs (Casos Sospechosos)"]
        I1["Raíz del Proyecto:\nSolicitud Cumplimiento TC {YYYY}.xlsx"]
        I2["data/input/auditorias_wsp/:\nArchivos .docx + Plantillas TLV WhatsApp.xlsx"]
    end

    subgraph PROCESS ["2. Process (Extracción & LLM)"]
        P1["audit_cumplimiento_pa_tc.py\n1. Busca teléfonos en DLAB_GEC\n2. Consulta Genesys API v2 vía Bearer\n3. Descarga transcripción de Verint REST\n4. Evalúa con gemini-3.1-flash-lite"]
        P2["audit_whatsapp.py\n1. Parsea texto de archivos Word (.docx)\n2. Evalúa prompts de pauta comercial con LLM"]
    end

    subgraph OUTPUTS ["3. Outputs (Dictámenes Auditados)"]
        O1["Solicitud Cumplimiento TC {YYYY}_Auditada.xlsx\n(Dictamen: ACEPTA / NO_ACEPTA, minuto, segundo y cita textual)"]
        O2["Reporte Excel de Auditoría WhatsApp\n(Infracciones a la pauta y políticas LPDP)"]
    end

    I1 --> P1 --> O1
    I2 --> P2 --> O2
```

---

## 📋 Cuadro Resumen de Entidades: Dónde se Crea y Quién la Consume

| Tabla Teradata (`DLAB_GEC`) | Módulo / Fase que la CREA / PUEBLA | Módulo / Proceso que la CONSUME | Tipo de Persistencia |
| :--- | :--- | :--- | :--- |
| `M_EXP_TELEVENTAS_EJECUTIVOS` | Dotación (Fase 4 ➔ Web P021) | Consumo (Fase 4), Calidad (Fase 4) | **Mensual Activa** *(Se sobreescribe con cada carga P021)* |
| `M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED` | Hook post-carga de P021 | Calidad (Fase 4: 04, 04_b, 05), Cierre (01, 03) | **Histórica Particionada** (`WHERE PERIODO = '{PERIODO}'`) |
| `T_SP_CD40K` | Consumo (Fase 2: `phase2_cd40k.py`) | Consumo (Fase 4: `CD40K.sql`) | **Temporal Activa** *(Líneas > 40K del mes)* |
| `T_VENTAS_BPE_MARKET` | Consumo (Fase 3: `phase3_desembolsos.py`) | Consumo (Fase 4), Calidad (Fase 4: `02_sa`) | **Temporal Activa** *(Desembolsos BNB del mes)* |
| `M_EXP_VENTAS_*` (TC, PP, CD, EC, CON...) | Consumo (Fase 4: `VENTAS_DN.sql`) | Calidad (Fase 4: `02_sa_marcacion_ventas_lpdp.sql`) | **Temporal Activa** *(Ventas comerciales del mes)* |
| `M_EXP_CALIDAD_PURECLOUD_PRE` | Calidad (Fase 1: `phase1_ingest_insight.py`) | Calidad (Fase 4: `01_evaluacion_manual_pc.sql`) | **Temporal Activa** *(Llamadas calificadas del mes)* |
| `M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS` | Calidad (Fase 2: `phase2_ingest_verint.py`) | Calidad (Fase 4: `02_sa_marcacion_ventas_lpdp.sql`) | **Temporal Activa** *(Transcripciones Verint del mes)* |
| `M_EXP_CALIDAD_DETALLE_PURE_CLOUD` | Calidad (Fase 4: `01_evaluacion_manual_pc.sql`) | Calidad (Fase 4: `05_consolidacion`), NTD (Fase 5) | **Histórica Particionada** (`WHERE PERIODO = '{PERIODO}'`) |
| `M_EXP_CALIDAD_DETALLE_SPEECH_ANALYTICS` | Calidad (Fase 4: `04_sa_ajustes_curva.sql`) | Calidad (Fase 4: `05_consolidacion`) | **Histórica Particionada** (`WHERE PERIODO = '{PERIODO}'`) |
| `M_EXP_CALIDAD_NOTA_FINAL` | Calidad (Fase 4: `05_consolidacion_nota_final.sql`) | Cierre Mensual (`01_auditoria`, `03_consolidado`), PBI | **Histórica Particionada** (`WHERE PERIODO = '{PERIODO}'`) |
| `M_EXP_CALIDAD_NOTAS_TOTAL_GERENCIAL` | Cierre Mensual (`01_auditoria_y_cierre.sql`) | **Power BI "CALIDAD de servicios" (Oficial)** | **Histórica Particionada Inmutable** |
| `M_KRI_RESUMEN_TOTAL` | Cierre Mensual (`02_kri_resumen_total.sql`) | Oficialía de Cumplimiento / Riesgos | **Histórica Particionada Inmutable** |
