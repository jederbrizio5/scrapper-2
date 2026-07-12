# ADR 0001: Infraestructura de Base de Datos SQLite (ADR-0001)

* **Fecha**: 2026-06-28
* **Estado**: Aceptado
* **Contexto**: Se requería una base de datos local ligera y de rápida configuración para almacenar y calificar los prospectos descubiertos en las primeras etapas de prospección.

---

## Decisión
Se decidió utilizar **SQLite** como motor de base de datos relacional inicial junto con **SQLAlchemy 2.x** como ORM y **Alembic** para la gestión de migraciones de esquema.

---

## Consecuencias

### Positivas:
* **Configuración cero**: No requiere levantar servidores ni dependencias externas de docker o servicios en la nube en la etapa inicial.
* **Velocidad**: Acceso y escritura ultrarrápidos para desarrollo y pruebas en memoria.
* **Control de versiones**: Las migraciones estructuradas con Alembic permiten modificar el esquema de base de datos de manera incremental y controlada.

### Negativas:
* **Escalabilidad**: SQLite bloquea la base de datos completa en escrituras concurrentes. Si el volumen crece más allá de ~500,000 registros, será necesario migrar a PostgreSQL (soportado fácilmente gracias a SQLAlchemy).
