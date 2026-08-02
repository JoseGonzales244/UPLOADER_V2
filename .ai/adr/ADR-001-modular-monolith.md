# ADR-001: Adopción de Monolito Modular (Clean Architecture) en UPLOADER_V2

## Estado
Aprobado

## Contexto
La aplicación `UPLOADER_V2` orquesta múltiples procesos de negocio independientes de Interbank:
1. Base Consumo
2. Proceso Calidad
3. Descarga y Auditoría Multietapa de Transcripciones
4. Reporte Convenios
5. Próximo Proceso de Cierre

Anteriormente, todos los archivos de servicios, scrapers, ejecutores SQL e ingesta residían en una carpeta única `core/` sin separación explícita de responsabilidades. Esto generaba un antipatrón de "God Directory" que complicaba la mantenibilidad, escalabilidad y pruebas independientes.

## Decisión Propuesta
Se adopta una arquitectura de **Monolito Modular (Clean Architecture)** organizada en Bounded Contexts independientes dentro de la carpeta `modules/`, desacoplados de los servicios y adaptadores compartidos en `infrastructure/`:

- `infrastructure/database/`: Driver Teradata, conectores FastLoad y loteadores SQL.
- `infrastructure/llm/`: Cliente resiliente para la API de Gemini con políticas de reintento ante errores de cuota (HTTP 429).
- `modules/transcripciones/`: Extracción de textos (Verint/Genesys) y pipeline de auditoría de 4 agentes LLM (Gramática, Trato/NTD, Protocolo, Consolidador).
- `modules/calidad/`: Orquestación y ejecuciones SQL de Calidad.
- `modules/consumo/`: Proceso e ingesta de Base Consumo.
- `modules/convenios/`: Reportes de Convenios.
- `modules/cierre/`: Módulo reservado para el proceso de cierre futuro.

Se mantienen módulos de compatibilidad en `core/` para evitar la ruptura de llamadas existentes.

## Consecuencias

### Ganancias (+):
- **Single Responsibility (SRP):** Cada módulo cambia únicamente ante modificaciones de su propio dominio.
- **Open/Closed (OCP):** Nuevos procesos (como Cierre) se incorporan en subcarpetas aisladas sin modificar los módulos existentes.
- **Resiliencia e Idempotencia:** Fallos en la cuota de la API LLM o descargas de Verint quedan acotados al módulo de Transcripciones sin interrumpir la operación de Calidad o Consumo.
- **Mantenibilidad en IDE:** Estructura limpia y fácil de auditar en VS Code.

### Compromisos (-):
- Ligero incremento en la cantidad de subcarpetas (`infrastructure/`, `modules/`).
