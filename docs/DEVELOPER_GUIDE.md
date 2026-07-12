# Guía del Desarrollador (DEVELOPER_GUIDE.md)

Esta guía te ayudará a comprender la arquitectura del código, la organización de carpetas y cómo realizar cambios de forma correcta.

---

## 1. Organización del Código

El código de producción vive en la carpeta `src/`. Está organizado siguiendo el principio de diseño modular y de responsabilidad única:

```text
src/
├── config/             # Configuración global y variables de entorno.
│   └── settings.py     # Clase Settings que lee variables del archivo .env.
│
├── database/           # Configuración de base de datos.
│   ├── connection.py   # Creación del engine SQLAlchemy.
│   ├── session.py      # Generador de sesiones local (get_session).
│   └── base.py         # Clase base declarativa (Base).
│
├── models/             # Modelos ORM SQLAlchemy (tablas de base de datos).
│   ├── searches.py     # Tabla 'searches' para búsquedas.
│   ├── domains.py      # Tabla 'domains' para dominios.
│   ├── companies.py    # Tabla 'companies' para empresas.
│   └── leads.py        # Tabla 'leads' para prospectos calificados.
│
├── repositories/       # Abstracción de base de datos (CRUD).
│   ├── base.py         # Repositorio genérico (create, get, list, update, delete).
│   ├── search_repository.py
│   ├── domain_repository.py
│   ├── company_repository.py
│   └── lead_repository.py
│
└── modules/            # Módulos específicos de lógica de negocio.
    └── meta_ads/       # Módulo para Meta Ads Library.
        ├── client/     # SDK HTTP para Graph API (secundario).
        ├── dto/        # Data Transfer Objects (BrowserAdDiscovery, BrowserAdResult).
        ├── browser/    # Configuración de Playwright y anti-detección.
        └── acquisition/# Lógica de extracción de anuncios y orquestador runner.
```

---

## 2. Flujo de Trabajo Típico de Desarrollo

Si eres un principiante, sigue este proceso paso a paso para añadir o modificar código:

### Paso 1: Configurar tu Entorno
Asegúrate de tener el entorno virtual activo:
```bash
source venv/bin/activate
```

### Paso 2: Ejecutar los Tests Existentes
Antes de cambiar nada, valida que todo funciona correctamente:
```bash
./scripts/test.sh
```

### Paso 3: Realizar tus Modificaciones
Asegúrate de:
* Agregar **type hints** a las firmas de tus funciones (ej. `def sumar(a: int, b: int) -> int:`).
* Añadir **docstrings** con triple comillas para explicar qué hace cada clase o función compleja.
* No hardcodear tokens ni credenciales. Si necesitas configurar algo, añádelo en `.env` y consúmelo mediante `settings.py`.

### Paso 4: Validar y Formatear
Usa las herramientas automáticas del proyecto para asegurar que tu código cumple con los estándares empresariales:
```bash
./scripts/check.sh
```
Este script aplicará formato automático (`ruff format`), revisará estilo y errores comunes (`ruff check`) y ejecutará la suite de pruebas.

---

## 3. Guía de Base de Datos y Migraciones (Alembic)

Cuando modifiques o crees un modelo en `src/models/`, debes crear y aplicar una migración para que la base de datos de SQLite se actualice:

1. **Crear migración automática**:
   ```bash
   source venv/bin/activate && alembic revision --autogenerate -m "descripción de cambios"
   ```
2. **Aplicar migración**:
   ```bash
   alembic upgrade head
   ```
3. **Verificar**: Corre los tests de repositorio para asegurar que SQLAlchemy mapea los datos correctamente:
   ```bash
   pytest tests/integration/test_repositories.py -v
   ```
