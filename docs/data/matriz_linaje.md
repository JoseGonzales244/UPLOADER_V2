# 🗺️ Matriz de Linaje de Datos End-to-End

Este documento detalla el linaje y trazabilidad de los datos desde sus fuentes primarias hasta los tableros analíticos en PowerBI.

---

## 🔄 Linaje de Datos por Pipeline

```mermaid
flowchart LR
    subgraph Orígenes ["1. Fuentes Primarias"]
        S1[SharePoint / Excel]
        S2[Insight Web]
        S3[SQL Server Corporativo]
        S4[Genesys Cloud / Verint]
    end

    subgraph Plataforma ["2. Ingesta & Orquestador APP_CALIDAD"]
        P1[Parser / Reader Python]
        P2[Scraper / Web Automation]
        P3[Transformación Teradata SQL]
    end

    subgraph Almacenamiento ["3. Teradata DLAB_GEC"]
        T1[(Tablas Intermedias Staging)]
        T2[(Tablas Finales / Snapshots)]
    end

    subgraph Consumo ["4. Consumo Analítico"]
        B1[PowerBI Tableros KRI]
        B2[PowerBI Calidad NTD]
    end

    S1 --> P1 --> T1
    S2 --> P2 --> T1
    S3 --> P1 --> T1
    S4 --> P2 --> T1

    T1 --> P3 --> T2
    T2 --> B1
    T2 --> B2
```

---

## 📋 Inventario de Fuentes

| Fuente | Tipo de Acceso | Transformación / Limpieza | Destino en Teradata |
| :--- | :--- | :--- | :--- |
| **`CD40K_NEW.xlsx`** | Archivo Local / SharePoint | Mapeo `P003-CD40K`, normalización de columnas | `DLAB_GEC.T_SP_CD40K` |
| **Bases de Desembolsos**| SQL Server (`pyodbc`) | Extracción por fecha de desembolso | `DLAB_GEC.BN_DESEMBOLSOS_GENERAL` |
| **Muestreos Insight** | Web Scraping / API | Parsing JSON, filtros de no conformidades | `DLAB_GEC.EVALUACIONES_CALIDAD` |
| **Audios Genesys** | Chrome CDP / Outlook | Enriquecimiento telefónico y descarga MP3 | Almacén local `data/downloads/` |

---

## 🔍 Trazabilidad Técnica Detallada por Proceso

Para consultar el mapa detallado de archivos fuente (`.py`), queries (`.sql`), endpoints de API y variables de entorno requeridas por cada flujo, consulta la:
👉 **[trazabilidad_end_to_end.md:L1](trazabilidad_end_to_end.md)**.

