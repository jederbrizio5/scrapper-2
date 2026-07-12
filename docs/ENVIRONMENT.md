# Guía de Entorno (ENVIRONMENT.md)

Este documento explica cómo configurar el entorno del proyecto y el propósito de cada variable en el archivo `.env`.

---

## 1. Archivo de Configuración (.env)
El archivo `.env` se encuentra en la raíz del proyecto y contiene variables de configuración que el código lee dinámicamente mediante la clase `Settings` en `src/config/settings.py`.

El repositorio incluye un archivo de ejemplo `.env.example`. Para comenzar, copia este archivo:
```bash
cp .env.example .env
```

---

## 2. Variables de Configuración Detalladas

### `DATABASE_URL`
* **Descripción**: La cadena de conexión para base de datos SQLAlchemy.
* **Por defecto**: `sqlite:///./data/processed/scrapper.db`
* **Notas**: SQLite crea la base de datos como un archivo local dentro de la carpeta `data/processed/`. Si en el futuro migras a PostgreSQL, utiliza el formato: `postgresql://usuario:contraseña@host:puerto/nombre_db`.

### `META_ACCESS_TOKEN`
* **Descripción**: Token de acceso para la Graph API de Meta (opcional, solo para el cliente secundario).
* **Por defecto**: Vacío `""`.

### `META_ADS_API_URL`
* **Descripción**: Endpoint base de la Graph API de Meta para el archivo de anuncios.
* **Por defecto**: `https://graph.facebook.com/v19.0/ads_archive`

### `META_TIMEOUT_SECONDS`
* **Descripción**: Tiempo de espera máximo para llamadas HTTP del cliente secundario.
* **Por defecto**: `30`

### `META_USER_AGENT`
* **Descripción**: Encabezado User-Agent utilizado por el cliente HTTP secundario.
* **Por defecto**: `MetaAdsScrapper/1.0`
