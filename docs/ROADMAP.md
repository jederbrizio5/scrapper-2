# Plan de Ruta del Proyecto (ROADMAP.md)

Este documento describe la visión a mediano y largo plazo para transformar el scrapper de anuncios en una plataforma autónoma de adquisición y cualificación de leads.

---

## 1. Fase 4: Persistencia y Scraping de Landings (En progreso)
* **Objetivo**: Unir el scraper de anuncios con la base de datos local e iniciar el scraping de landing pages de empresas.
* **Componentes**:
  * Orquestador de persistencia.
  * Extractor de correos y teléfonos desde las landings.
  * Detección de redes sociales alternativas (LinkedIn, Twitter/X).

---

## 2. Fase 5: Algoritmo de Scoring Automatizado (Pendiente)
* **Objetivo**: Evaluar y calificar cada lead de forma automática para priorizar el esfuerzo de ventas.
* **Criterios de Calificación (Scoring)**:
  * **Volumen de anuncios**: Empresas con múltiples anuncios activos obtienen mayor score (indica mayor presupuesto).
  * **Calidad de landing**: Velocidad de carga, diseño moderno y presencia de píxeles de Meta.
  * **Seguidores sociales**: Priorizar empresas en crecimiento con mediana o baja comunidad orgánica que necesitan más pauta digital.
  * **Clasificación de industria**: Filtro por industrias prioritarias (ej. e-commerce, educación en línea, SaaS).

---

## 3. Fase 6: Integración con CRM y Canales de Salida (Pendiente)
* **Objetivo**: Exportar y sincronizar leads calificados de forma automática con herramientas comerciales.
* **Integraciones planeadas**:
  * **Google Sheets API**: Exportación automática de leads con score > 70.
  * **HubSpot / Salesforce API**: Creación de contactos y empresas de forma automática.
  * **Notificaciones por Slack/Telegram**: Alertas inmediatas al canal comercial al descubrir un lead de alta prioridad.

---

## 4. Fase 7: Automatización y Orquestación de Tareas (Pendiente)
* **Objetivo**: Ejecución autónoma programada sin intervención manual.
* **Tecnologías**:
  * **Cron jobs locales** o **Celery** con Redis para colas de scraping distribuidas.
  * Panel de control web sencillo (Streamlit o Next.js) para monitorear el estado de las búsquedas, cantidad de leads descubiertos y estadísticas de rendimiento.
