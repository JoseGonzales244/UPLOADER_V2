# 📊 Pipeline: PBI Evaluaciones Calidad (NTD)

Este documento describe las fases y orquestación del consolidado mensual de **Evaluaciones de Calidad No Te Dejes (NTD)**.

---

## 📊 Diagrama de Flujo

```mermaid
flowchart TD
    subgraph F1 ["Fase 1: Insumos de Calidad"]
        A[Evaluaciones Insight] --> B[Normalización JSON]
        B --> C[(Carga Teradata DLAB_GEC)]
    end

    subgraph F2 ["Fase 2: Cruce de Muestras"]
        D[Bases de Muestreo] --> E[Validación de DNIs y Registros]
    end

    subgraph F3 ["Fase 3: Reglas de Ponderación"]
        F[Cálculo de Notas NTD] --> G[Atribución por Supervisor/Asesor]
    end

    subgraph F4 ["Fase 4: Consolidación SQL"]
        H[CALIDAD_CONSOLIDADO.sql] --> I[(Tabla Final Evaluaciones)]
    end

    subgraph F5 ["Fase 5: Extracción PowerBI"]
        I --> J[Vistas Analíticas PBI Calidad]
    end

    F1 --> F2 --> F3 --> F4 --> F5
```

---

## 📋 Entradas y Salidas

- **Entradas:** Evaluaciones manuales de Insight, cruce de dotación de asesores y catálogo de tipificaciones.
- **Transformación:** Ponderación de no conformidades críticas y no críticas, normalización de DNIs.
- **Salida:** Tablas maestras de calidad en `DLAB_GEC` consumidas directamente por el tablero PowerBI de Calidad Televentas.
