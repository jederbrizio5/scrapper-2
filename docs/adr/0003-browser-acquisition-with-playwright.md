# ADR 0003: Adquisición por Navegador usando Playwright (ADR-0003)

* **Fecha**: 2026-06-29
* **Estado**: Aceptado
* **Contexto**: La API oficial de Meta Ads está altamente restringida, solo muestra anuncios de temas sociales/políticos o categorías limitadas, y no expone las Landing URLs externas ni los datos sociales del anunciante, los cuales son críticos para el objetivo del proyecto.

---

## Decisión
Se decidió implementar un scraper basado en navegador real utilizando **Playwright (Chromium)** para extraer la información directamente del DOM de la página pública de Meta Ads Library. Meta Ads Library no requiere inicio de sesión para realizar búsquedas o ver detalles de anunciantes.

---

## Consecuencias

### Positivas:
* **Acceso completo**: Permite extraer las Landing URLs externas reales de los botones de interacción y la información del anunciante (redes sociales y seguidores).
* **Sin login**: Evita el uso de cuentas de Facebook de prueba que podrían ser bloqueadas o requerir verificación en dos pasos (2FA).
* **Anti-detección**: Se implementaron técnicas de bypass (User-Agent realista, deshabilitar blink automation flag, inyección de variables de plugins y jitter en esperas) para mitigar el bloqueo por parte de Meta.

### Negativas:
* **Sensibilidad al DOM**: Cambios en el diseño HTML o las clasesCSS de Meta Ads Library pueden romper los selectores del extractor, requiriendo mantenimiento y actualización periódica de la lógica de parsing.
* **Rendimiento**: Ejecutar un navegador real es más lento y consume más CPU/Memoria que realizar llamadas de API HTTP crudas.
