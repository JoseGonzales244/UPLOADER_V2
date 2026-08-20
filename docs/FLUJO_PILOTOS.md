# 🚀 Flujo de Ejecución - Pilotos Analíticos (TCAD y No Venta)

Este documento detalla la arquitectura, flujos de datos, fuentes y scripts SQL de los módulos especializados **Piloto TCAD** (Tarjetas Adicionales) y **Piloto No Venta** (Speech Analytics & Objeciones).

---

## 1. 💳 Piloto TCAD (Tarjetas Adicionales)

### 📊 Diagrama de Flujo

```mermaid
flowchart TD
    subgraph Ingesta ["1. Ingesta Speech Analytics"]
        A[Export Verint Speech TCAD] --> B[Plantilla P025-SA_TCAD / Fila 29]
        B --> C[(DLAB_GEC.M_EXP_DATA_TCAD_SA)]
    end

    subgraph Cruce ["2. Cruce y Normalización SQL"]
        C --> D[01_dml_tcad_monthly_ingest.sql]
        E[(E_DW_VIEWS.V_FCT_RT_TC_HISTORICO)] --> F[V_EXP_VENTAS_TC_TCAD]
        F --> D
        D --> G{Deduplicación QUALIFY}
    end

    subgraph Destino ["3. Tabla Final de Colocaciones"]
        G --> H[(DLAB_GEC.M_EXP_CROSS_TCAD)]
    end
```

### 🔍 Especificación Técnica

- **Plantilla de Mapeo:** `P025-SA_TCAD` / `P026-CROSS_TCAD` en `config/plantillas.json`.
- **Lector:** Salto dinámico a fila 29 (`header_row: 28`) para reportes Verint.
- **Tablas Teradata:**
  - `DLAB_GEC.M_EXP_DATA_TCAD_SA`: Datos crudos normalizados de llamadas de Speech Analytics con ofertas TCAD.
  - `DLAB_GEC.V_EXP_VENTAS_TC_TCAD`: Vista normalizada de ventas de tarjetas en `E_DW_VIEWS`.
  - `DLAB_GEC.M_EXP_CROSS_TCAD`: Tabla consolidada final con cruce de colocaciones efectivas.
- **Scripts:**
  - `modules/Piloto TCAD/sql/00_ddl_tcad_tables_views.sql` (DDL de tablas y vistas).
  - `modules/Piloto TCAD/sql/01_dml_tcad_monthly_ingest.sql` (Ingesta mensual y cruce analítico).

---

## 2. 🎯 Piloto No Venta (Analítica de Objeciones y Cierres)

### 📊 Diagrama de Flujo

```mermaid
flowchart TD
    subgraph Carga ["1. Carga Stage Ligera"]
        A[Reporte Verint Speech No Venta] --> B[Plantilla P031-PILOTO_NO_VENTA / Fila 29]
        B --> C[(DLAB_GEC.M_EXP_STAGE_NO_VENTA)]
    end

    subgraph Ventas ["2. Deduplicación de Ventas Reales"]
        D[(DLAB_GEC.M_EXP_VENTAS_TC)] --> V1[VT_VENTAS_TC_DEDUP]
        E[(DLAB_GEC.M_EXP_VENTAS_PP)] --> V2[VT_VENTAS_PP_DEDUP]
        F[(DLAB_GEC.M_EXP_VENTAS_EC)] --> V3[VT_VENTAS_EC_DEDUP]
        G[(DLAB_GEC.M_EXP_VENTAS_CD)] --> V4[VT_VENTAS_CDEUDA_DEDUP]
        H[(DLAB_GEC.M_EXP_VENTAS_SEG)] --> V5[VT_VENTAS_SEG_DEDUP]
    end

    subgraph Analitica ["3. Cruce Maestro y Diagnóstico"]
        C --> M[02_cruce_ventas_reales.sql]
        V1 & V2 & V3 & V4 & V5 --> M
        M --> I{Clasificación de Gestión}
    end

    subgraph Persistencia ["4. Persistencia y Liberación de Espacio"]
        I --> J[(DLAB_GEC.M_EXP_PILOTO_NO_VENTA)]
        J --> K[DELETE FROM M_EXP_STAGE_NO_VENTA ALL]
    end
```

### 🔍 Especificación Técnica

- **Plantilla de Mapeo:** `P031-PILOTO_NO_VENTA` en `config/plantillas.json`.
- **Lector:** Salto dinámico a fila 29 (`header_row: 28`) con 22 columnas de objeciones (tasa alta, lo pensará, sin interés, competencia, endeudamiento, ocupado, mala experiencia, membresía) y silencios.
- **Diagnósticos Generados Automáticamente:**
  1. `VENTA RESCATADA (MANEJO DE OBJECION EXITOSO)`: El cliente tuvo objeciones pero se concretó la venta real.
  2. `VENTA CONFORME`: Venta real registrada sin objeciones en audio.
  3. `FUGA / TIPIFICACION ERRONEA (RECHAZO POR TASA)`: Tipificada como "No califica" pero el cliente rechazó por tasa alta.
  4. `NO VENTA - LEAD EN SEGUIMIENTO (LO PENSARA)`: Cliente interesado que postergó la decisión.
  5. `NO VENTA - FALTA DE REBATIMIENTO`: Existió objeción del cliente sin intento de manejo/cierre por parte del asesor.
  6. `NO VENTA REGULAR`: Gestión regular sin objeciones críticas ni venta.
- **Tablas Teradata:**
  - `DLAB_GEC.M_EXP_STAGE_NO_VENTA`: Tabla stage ligera temporal de ingesta.
  - `DLAB_GEC.M_EXP_PILOTO_NO_VENTA`: Tabla física histórica permanente con clave primaria `(PERIODO, DNI, REG_EV, FECHA_LLAMADA)`.
- **Scripts:**
  - `modules/piloto_no_venta/sql/01_ddl_stage_no_venta.sql` (DDL de stage y tabla final).
  - `modules/piloto_no_venta/sql/02_cruce_ventas_reales.sql` (Cruce deduplicado por `MESDESEMBOLSO`, inserción en tabla final y `DELETE ALL` de stage).
