# 📚 Hub de Documentación Técnica - APP_CALIDAD

Bienvenido a la base de conocimiento y documentación técnica de la **Plataforma Calidad Televentas**.

---

## 🧭 Mapa de Navegación por Dominio

```mermaid
graph TD
    Root[docs/] --> OPE[1. Operaciones & Usuario<br>docs/operations/]
    Root --> PIP[2. Pipelines & Lógica SQL<br>docs/pipelines/]
    Root --> DAT[3. Gobierno & Datos<br>docs/data/]

    OPE --> M1[manual_usuario.md]
    OPE --> M2[troubleshooting.md]

    PIP --> P1[base_consumo.md]
    PIP --> P2[calidad_ntd.md]
    PIP --> P3[cierre_mensual.md]
    PIP --> P4[dotacion_mensual.md]
    PIP --> P5[audios_y_transcripciones.md]
    PIP --> P6[pilotos_y_nps.md]

    DAT --> D1[diccionario_tablas.md]
    DAT --> D2[matriz_linaje.md]
    DAT --> D3[trazabilidad_end_to_end.md]
```

---

## 📂 1. Dominio: Operaciones y Usuario (`docs/operations/`)

> **Audiencia:** Operadores, Analistas de Calidad, Supervisores.

- 📖 **[Manual de Usuario](operations/manual_usuario.md):** Guía paso a paso para la carga a Teradata, descarga de audios y orquestación.
- 🤝 **[Plan de Traspaso & Onboarding](operations/plan_de_traspaso.md):** Guía de instalación en laptop nueva, matriz de accesos y setup de OneDrive.
- 🩺 **[Troubleshooting y Diagnóstico](operations/troubleshooting.md):** Resolución de fallos de entorno (Outlook, Chrome CDP, Teradata).

---

## ⚡ 2. Dominio: Pipelines y Lógica de Negocio (`docs/pipelines/`)

> **Audiencia:** Ingenieros de Datos, Desarrolladores.

- 📊 **[PBI Base Consumo](pipelines/base_consumo.md):** Las 5 fases del pipeline de consumo, insumos y scripts SQL.
- 📈 **[PBI Evaluaciones Calidad](pipelines/calidad_ntd.md):** Proceso de consolidado NTD y reglas de ponderación.
- 🔒 **[Modo Cierre Mensual](pipelines/cierre_mensual.md):** Idempotencia, scripts `01_auditoria` y `02_kri_resumen`.
- 👥 **[Dotación Mensual & Licencias SA](pipelines/dotacion_mensual.md):** Fases 1 a 5, ausentismos de las 4 analistas y licencias Verint.
- 🎧 **[Audios y Transcripciones](pipelines/audios_y_transcripciones.md):** Genesys Cloud, Outlook MAPI y Verint ExtJS.
- 🚀 **[Pilotos y Encuestas NPS](pipelines/pilotos_y_nps.md):** Piloto TCAD, Objeciones No Venta y NPS IVR.

---

## 🗄️ 3. Dominio: Catálogo y Linaje de Datos (`docs/data/`)

> **Audiencia:** BI, Gobierno de Datos, Desarrolladores, Auditores.

- 🗺️ **[Trazabilidad Técnica End-to-End](data/trazabilidad_end_to_end.md):** Mapa exhaustivo de archivos de código, scripts SQL, triggers y destinos de los 8 módulos.
- 📋 **[Diccionario de Tablas](data/diccionario_tablas.md):** Catálogo de tablas en `DLAB_GEC` y esquemas de tipos.
- 🔄 **[Matriz de Linaje de Datos](data/matriz_linaje.md):** Trazabilidad conceptual desde orígenes hasta PowerBI.

