# 🗄️ Diccionario Oficial de Tablas Teradata (`DLAB_GEC`)

Catálogo exhaustivo y verificado de todas las tablas físicas, temporales y vistas analíticas ejecutadas en **Teradata (`DLAB_GEC`)** por los pipelines de la plataforma.

---

## ⚡ 1. Dominio: Base Consumo (Ventas Comerciales y Consentimiento)

| Objeto Teradata | Tipo | Descripción | Frecuencia |
| :--- | :---: | :--- | :--- |
| `DLAB_GEC.M_EXP_VENTAS_TC` | Multiset Table | Ventas de Tarjetas de Crédito colocadas por Televentas | Diaria / Cierre |
| `DLAB_GEC.M_EXP_VENTAS_PP` | Multiset Table | Ventas de Préstamos Personales | Diaria / Cierre |
| `DLAB_GEC.M_EXP_VENTAS_CD` | Multiset Table | Ventas de Crédito Digital | Diaria / Cierre |
| `DLAB_GEC.M_EXP_VENTAS_EC` | Multiset Table | Colocaciones de Extracash | Diaria / Cierre |
| `DLAB_GEC.M_EXP_VENTAS_CON` | Multiset Table | Colocaciones de Convenios | Diaria / Cierre |
| `DLAB_GEC.M_EXP_VENTAS_IL` | Multiset Table | Incrementos de Línea aceptados | Diaria / Cierre |
| `DLAB_GEC.M_EXP_VENTAS_UPG` | Multiset Table | Upgrades de Tarjeta de Crédito | Diaria / Cierre |
| `DLAB_GEC.M_EXP_VENTAS_PA` | Multiset Table | Ventas Préstamo al Toque | Diaria / Cierre |
| `DLAB_GEC.M_EXP_VENTAS_SEG` | Multiset Table | Colocaciones de Seguros 360 y asociados | Diaria / Cierre |
| `DLAB_GEC.T_SP_CD40K` | Multiset Table | Ingesta de líneas CD40K desde SharePoint/Excel | Diaria / On-Demand |
| `DLAB_GEC.BN_DESEMBOLSOS_GENERAL` | Multiset Table | Extracción y réplica de desembolsos desde SQL Server | Diaria / Cierre |
| `DLAB_GEC.M_EXP_CONSUMO_SELECT_TC_CD_SEG` | Multiset Table | Consolidado analítico multi-producto de Consumo | Diaria / Cierre |

---

## 📊 2. Dominio: Evaluaciones Calidad (NTD & Speech Analytics)

| Objeto Teradata | Tipo | Descripción | Frecuencia |
| :--- | :---: | :--- | :--- |
| `DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD` | Multiset Table | Evaluaciones manuales de llamadas extraídas de Insight/PureCloud | Semanal / Mensual |
| `DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE` | Multiset Table | Tabla intermedia de normalización de notas y no conformidades | Semanal / Mensual |
| `DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS` | Multiset Table | Transcripciones e interacciones de Verint Speech Analytics | Mensual |
| `DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE` | Multiset Table | Staging de observaciones críticas Not To Do (NTD) | Mensual |
| `DLAB_GEC.M_EXP_CALIDAD_HISTORICO_ERRORES` | Multiset Table | Registro histórico de desvíos y tipificaciones erróneas | Mensual |
| `DLAB_GEC.M_EXP_NTD_REPORTING_HISTORICO` | Multiset Table | Consolidado histórico oficial para reportes de Calidad | Mensual |
| `DLAB_GEC.V_EXP_CALIDAD_NOTA_FINAL` | View | Vista con notas finales consolidadas por asesor y supervisor | On-Demand (PBI) |

---

## 🛡️ 3. Dominio: KRIs Operativos y Tráfico Telefónico

| Objeto Teradata | Tipo | Descripción | Frecuencia |
| :--- | :---: | :--- | :--- |
| `DLAB_GEC.T_EXP_KRI_VENTAS_SINAUDIO` | Multiset Table | Ventas comerciales que carecen de grabación en Genesys | Diaria / Cierre |
| `DLAB_GEC.T_EXP_KRI_VENTAS_SINAUDIO_CALIDAD` | Multiset Table | Cruce de ventas sin audio auditadas por el equipo de calidad | Mensual |
| `DLAB_GEC.M_EXP_CO_KRI_VENTA_TOTAL` | Multiset Table | Universo totalizado de ventas para cálculo del denominador KRI | Diaria / Cierre |
| `DLAB_GEC.M_EXP_TRAFICO_GENESIS` | Multiset Table | Tráfico e interacciones telefónicas descargadas de Genesys Cloud | Diaria / Cierre |
| `DLAB_GEC.T_EXP_KRI_TELF_NO_AUTORIZADO` | Multiset Table | Llamadas y ventas sobre números no autorizados (LPDP) | Diaria / Cierre |
| `DLAB_GEC.T_EXP_KRI_TELF_NO_AUTORIZADO_CALIDAD` | Multiset Table | Cruce de teléfonos no autorizados con muestras de calidad | Mensual |

---

## 🔒 4. Dominio: Cierre Mensual, Dotación y Jerarquías

| Objeto Teradata | Tipo | Descripción | Frecuencia |
| :--- | :---: | :--- | :--- |
| `DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS` | Multiset Table | Padrón maestro de asesores, registros y fechas de ingreso | Mensual / Cierre |
| `DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED` | Multiset Table | Jerarquía agrupada (Asesor -> Supervisor -> Jefe de Canal) | Mensual / Cierre |
| `DLAB_GEC.M_EXP_CALIDAD_NOTAS_TOTAL_GERENCIAL` | Multiset Table | Snapshot final inmutable para pago de comisiones y gerencia | Cierre Mensual |
| `DLAB_GEC.M_KRI_RESUMEN_TOTAL` | Multiset Table | Resumen definitivo totalizado de KRIs de Televentas | Cierre Mensual |

---

## 🚀 5. Dominio: Pilotos (TCAD, No Venta) y Encuestas NPS

| Objeto Teradata | Tipo | Descripción | Frecuencia |
| :--- | :---: | :--- | :--- |
| `DLAB_GEC.M_EXP_STAGE_NO_VENTA` | Multiset Table | Staging temporal de llamadas sin venta categorizadas en Speech | Mensual |
| `DLAB_GEC.M_EXP_PILOTO_NO_VENTA` | Multiset Table | Base consolidada de objeciones y cruce de ventas rescatadas | Mensual |
| `DLAB_GEC.M_EXP_DATA_TCAD_SA_PRE` | Multiset Table | Staging de marcaciones Speech Analytics para Tarjetas Adicionales | Quincenal / Mes |
| `DLAB_GEC.M_EXP_DATA_TCAD_SA` | Multiset Table | Data depurada de audios del piloto TCAD | Quincenal / Mes |
| `DLAB_GEC.M_EXP_CROSS_TCAD` | Multiset Table | Ingesta de ventas cross de adicionales | Quincenal / Mes |
| `DLAB_GEC.V_EXP_VENTAS_TC_TCAD` | View | Vista de cruce de ventas TC con oferta de adicionales | On-Demand |
| `DLAB_GEC.V_FNL_TCAD_SIMPLE` | View | Funnel analítico de conversión del piloto TCAD | On-Demand (PBI) |
| `DLAB_GEC.F_NPS_VENTAS_TV` | Multiset Table | Matriz de calificaciones NPS IVR cruzadas con ejecutivos y venta | Mensual |

---

## 🏛️ 6. Vistas Externas del Data Warehouse (`E_DW_VIEWS` / Maestros)

| Objeto DW | Descripción |
| :--- | :--- |
| `E_DW_VIEWS.V_FCT_RT_TC_HISTORICO` | Vista histórica corporativa de colocaciones de Tarjetas de Crédito |
| `V_CONT_TELEFONO_APICLIENTE` | Catálogo de teléfonos autorizados por cliente (API Cliente) |
| `TLV_CARGA_ACTUAL` / `TLV_CARGA_ACTUAL_DIGITAL` | Bases de asignación diaria de leads y teléfonos para emisión |
