# 🎧 Pipeline: Audios Genesys y Transcripciones Speech Analytics

Este documento describe la arquitectura para la **descarga de audios** y la ingesta de **transcripciones**.

---

## 📊 Diagrama de Flujo

```mermaid
flowchart TD
    subgraph Genesys ["1. Descarga de Audios Genesys"]
        A[Outlook / Input Manual] --> B[Extracción REG_EV + DNI]
        B --> C[Enriquecimiento Teléfonos Teradata]
        C --> D[Chrome CDP Port 9222 Genesys Cloud]
        D --> E[Descarga de MP3/WAV a data/downloads/audios]
    end

    subgraph Speech ["2. Transcripciones Verint / Speech"]
        F[Extractor Verint ExtJS] --> G[Parsing de Conversaciones]
        G --> H[Procesador Speech: modules/speech/]
        H --> I[(Carga Teradata Transcripciones)]
    end

    E -.-> F
```

---

## 🛠️ Servicios Involucrados

- **`OutlookService` (`modules/genesys/services/outlook_service.py`):** Lector MAPI vía `pywin32`.
- **`GenesysDownloader` (`modules/genesys/services/downloader.py`):** Automatización vía Chrome DevTools Protocol.
- **`VerintTranscriptExtractor` (`modules/verint/transcripciones/extractors/verint_transcript_extractor.py`):** Extracción de texto e interacciones.
