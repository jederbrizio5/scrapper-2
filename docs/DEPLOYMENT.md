# Guía de Despliegue (DEPLOYMENT.md)

Este documento detalla los requerimientos y pasos para desplegar y ejecutar el sistema de prospección en diferentes entornos.

---

## 1. Requerimientos de Sistema
* **Sistema Operativo**: Linux (Ubuntu 22.04 LTS recomendado) o macOS.
* **Python**: Versión 3.10 o superior.
* **Navegador**: Playwright Chromium (se descarga automáticamente con la herramienta CLI).

---

## 2. Ejecución Local (Producción y Desarrollo)
Para ejecutar el scraping de forma persistente en tu máquina local:

1. **Instalar el proyecto**:
   ```bash
   ./scripts/install.sh
   source venv/bin/activate && playwright install chromium
   ```
2. **Crear archivo de configuración (.env)**:
   ```bash
   cp .env.example .env
   # Edita el archivo .env con tus credenciales y configuración
   ```
3. **Ejecutar en segundo plano (Nohup)**:
   Si quieres ejecutar una lista larga de búsquedas y cerrar tu terminal, usa `nohup` para que el proceso no se interrumpa:
   ```bash
   nohup python scripts/run_meta_ads_browser.py \
     --keyword "curso:100" --keyword "marketing:100" \
     --headless --no-enrich > output/night_run.log 2>&1 &
   ```
   Puedes monitorear la salida en tiempo real con:
   ```bash
   tail -f output/night_run.log
   ```

---

## 3. Despliegue en VPS / Servidores Cloud
Si decides desplegar el bot en un servidor (ej. DigitalOcean, AWS, Linode):

### Configuración sin Interfaz Gráfica (Headless-Only)
Los servidores Linux no suelen tener interfaz gráfica instalada, por lo que es obligatorio ejecutar el bot con el argumento `--headless`.

Además, debes instalar las dependencias del sistema necesarias para que Playwright Chromium funcione. Ejecuta este comando dentro de tu VPS:
```bash
source venv/bin/activate && playwright install-deps
```

### Base de Datos
Por defecto, el sistema utiliza SQLite, almacenando la base de datos localmente en `data/processed/scrapper.db`. 
* Asegúrate de respaldar este archivo periódicamente.
* Si el volumen de búsquedas y leads supera los 500,000 registros, migra a **PostgreSQL** cambiando la variable `DATABASE_URL` en tu archivo `.env`.
