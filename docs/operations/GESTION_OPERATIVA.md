# Plataforma Calidad Televentas — Gestión Operativa
> Documento para traspaso, reemplazo y continuidad del área.

---

## 1. Catálogo de Procesos

| Proceso | Frecuencia | Automatización | Estado |
|---|---|---|---|
| **Calidad NTD** — Evaluaciones Insight + Speech Verint + NTD | Semanal | ✅ 1 click desde UI | ✅ Operativo |
| **Consumo Base** — Insumos Insight + CD40K + Desembolsos | Diario *(ejecutar lo más temprano posible — Teradata puede ser lento)* | ✅ 1 click desde UI | ✅ Operativo |
| **Dotación** — Staffing mensual Televentas + Licencias SA | Mensual | ✅ 1 click desde UI *(requiere inputs de otras áreas previo)* | ✅ Operativo |
| **Cierre Mensual** — Consolidado gerencial + KRI | Mensual | ✅ 1 click desde UI | ✅ Operativo |
| **Auditorías IA** — PA-TC (Gemini) + WhatsApp (Gemini) | Mensual | ⚠️ Manual *(colocar archivo de entrada, luego ejecutar por consola)* | ✅ Operativo |
| **Transcripciones Verint** — Batch + Pipeline Speech → SQL Server | Mensual | ✅ 1 click desde UI | ✅ Operativo |
| **Genesys** — Descarga audio + Parser Outlook | A demanda | ✅ 1 click desde UI | ✅ Operativo |
| **Convenios** — Setup / ETL de nuevos convenios | A demanda | ✅ 1 click desde UI | ✅ Operativo |
| **Piloto No Venta** | Semanal *(por ahora)* | ⚠️ Parcial *(en desarrollo)* | 🚧 En desarrollo |
| **Piloto TCAD** | Semanal *(por ahora)* | ⚠️ Parcial *(en desarrollo)* | 🚧 En desarrollo |

---

## 2. Estado Global de Desarrollo

| Módulo | Producción | En desarrollo | Pendiente reemplazo |
|---|---|---|---|
| Calidad NTD | ✅ | — | — |
| Consumo Base | ✅ | — | — |
| Dotación + Licencias SA | ✅ | — | — |
| Cierre Mensual | ✅ | — | — |
| Auditorías IA (PA-TC + WhatsApp) | ✅ | — | — |
| Transcripciones Verint + Speech | ✅ | — | — |
| Genesys (audio + Outlook) | ✅ | — | — |
| Convenios | ✅ | — | — |
| Piloto No Venta | — | 🚧 | ⏳ Definición completa pendiente |
| Piloto TCAD | — | 🚧 | ⏳ Definición completa pendiente |

---

## 3. Pendientes Críticos para el Sucesor

| # | Pendiente | Impacto | Workaround actual |
|---|---|---|---|
| 1 | **No hay scheduler** — todos los procesos son manuales desde la UI | Alto | El operador ejecuta manualmente desde la app |
| 2 | **No hay alertas de fallo** — si el pipeline falla, nadie es notificado automáticamente | Alto | Revisar `logs/proceso_calidad_YYYYMMDD.log` |
| 3 | **Homologaciones se actualizan en Teradata directo** — preguntas o grupos nuevos de Insight requieren editar y ejecutar `00_setup_homologaciones.sql` manualmente | Medio | La Fase 4 detecta y loguea preguntas sin mapear; pero no las agrega sola |
| 4 | **`V_CHECK_FECHAS_NTD` no está en la UI** — no puedes ver desde la app cuándo se actualizó cada tabla PRE | Medio | `SELECT * FROM DLAB_GEC.V_CHECK_FECHAS_NTD` en Teradata |
| 5 | **Tests automatizados insuficientes** | Medio | Correr el pipeline en período de prueba |
| 6 | **Piloto No Venta sin pipeline completo** — tiene SQL pero no está integrado a la UI | Bajo | Ejecutar SQL directamente en Teradata |
| 7 | **Convenios — algunos pasos de nuevos convenios aún son manuales** | Bajo | Coordinar con responsable de Convenios |
| 8 | **Insumos dispersos en OneDrives individuales** — `1. EXPERIENCIA DE COMPRA` reside en el OneDrive de **Janesy Lopez** y `Dotación` en la carpeta de **Rossmery** | Alto | Migrar a un SharePoint institucional del área para independizar insumos de personas específicas y evitar fallos de rutas |

---

## 4. Inputs Manuales Requeridos

> Los procesos **Calidad**, **Consumo** y **Dotación** son **100% automáticos con 1 click** — la app descarga y procesa todo internamente (incluyendo ACCION_TOMADA.xlsx y CD40K).  
> Solo los procesos de **Auditoría** requieren que el operador coloque un archivo antes de ejecutar.

| Proceso | Archivo a colocar | Dónde |
|---|---|---|
| **Dotación** | Consolidado Planilla ausentismo + Select Dotación *(enviados por otras áreas)* | Rutas configuradas en `.env` / `DotacionConfig` |
| **Auditoría PA-TC** | `Solicitud Cumplimiento TC YYYY.xlsx` | Raíz del proyecto |
| **Auditoría WhatsApp** | Archivos `.docx` + `Plantillas TLV WhatsApp.xlsx` | `data/input/auditorias_wsp/` |
