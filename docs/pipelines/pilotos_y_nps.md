# 🚀 Pipeline: Pilotos Analíticos y Encuestas NPS IVR

Este documento describe los procesos correspondientes al **Piloto TCAD**, **Piloto No Venta** y el procesamiento de **Encuestas NPS IVR**.

---

## 📈 1. Encuestas NPS IVR

Procesa las calificaciones post-llamada (`0-10`) emitidas por los clientes en el IVR:
- **Cruce:** Asocia la encuesta al asesor de televentas, fecha y producto colocado.
- **Métricas:** Clasificación en Promotores (9-10), Pasivos (7-8) y Detractores (0-6).
- **Destino:** Vistas analíticas en Teradata para tableros de experiencia del cliente.

---

## 🎯 2. Pilotos TCAD y No Venta

- **Piloto TCAD (Tarjetas Adicionales & Seguros 360):**
  - Mide la efectividad en colocación de adicionales y seguros cruzados.
- **Piloto No Venta (Speech Objeciones):**
  - Analiza llamadas no convertidas para categorizar objeciones (precio, falta de interés, ya cuenta con producto).
