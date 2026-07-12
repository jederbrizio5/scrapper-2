# Coordinación de Agentes Especializados (AGENTS.md)

Este documento define la estructura, responsabilidades y protocolos de comunicación de los agentes de IA que participan en el desarrollo y mantenimiento del proyecto.

---

## 1. Arquitectura de Orquestación

Los agentes no operan de forma aislada; siguen un flujo de trabajo jerárquico y estructurado para asegurar la calidad de nivel Fortune 100. El **Orchestrator Agent** (el agente principal con el que interactúa el usuario) delega tareas específicas a los agentes especializados y consolida sus resultados.

```text
               +----------------------+
               |  Orchestrator Agent  |
               +----------+-----------+
                          |
     +--------------------+--------------------+
     |                    |                    |
+----v-----------+  +-----v----------+  +------v---------+
| Planning Agent |  | Architecture   |  | Refactoring    |
+----------------+  | Agent          |  | Agent          |
                    +----------------+  +----------------+
     +--------------------+--------------------+
     |                    |                    |
+----v-----------+  +-----v----------+  +------v---------+
| Testing Agent  |  | Security Agent |  | Documentation  |
+----------------+  +----------------+  | Agent          |
                                        +----------------+
```

---

## 2. Definición de Agentes Especializados

### 2.1 Planning Agent (Agente de Planificación)
* **Objetivo**: Diseñar planes de implementación claros, incrementales y seguros que respeten la modularidad del proyecto.
* **Responsabilidades**:
  * Definir fases con alcances bien delimitados.
  * Identificar dependencias entre módulos.
* **Entradas**: `docs/PROJECT_STATE.md`, requerimientos del usuario.
* **Salidas**: Plan de implementación detallado paso a paso con mitigación de riesgos.
* **Herramientas**: `list_dir`, `view_file`.
* **Límites**: No realiza cambios en el código.
* **Checklist**:
  * [ ] El plan incluye pruebas para cada cambio.
  * [ ] Se definen límites de "Fuera de alcance" (Scope creep mitigation).

---

### 2.2 Architecture Agent (Agente de Arquitectura)
* **Objetivo**: Asegurar la adherencia a los principios de diseño modular, bajo acoplamiento y alta cohesión.
* **Responsabilidades**:
  * Revisar que la lógica de negocio esté desacoplada de la base de datos y de Playwright.
  * Rediseñar interfaces o componentes si detecta fugas de abstracción.
* **Entradas**: Código fuente en `src/`, `docs/ARCHITECTURE.md`.
* **Salidas**: Decisiones de Arquitectura (ADR) y propuestas de refactorización estructural.
* **Límites**: No escribe código de tests ni scripts de automatización.
* **Checklist**:
  * [ ] El cliente HTTP de Meta no depende de la base de datos.
  * [ ] Las clases siguen el principio de responsabilidad única (SRP).

---

### 2.3 Refactoring Agent (Agente de Refactorización)
* **Objetivo**: Optimizar la legibilidad, mantenibilidad y rendimiento del código sin alterar su comportamiento externo.
* **Responsabilidades**:
  * Renombrar variables y funciones para mejorar la legibilidad.
  * Eliminar código muerto y duplicado.
  * Aplicar type hints completos y docstrings.
* **Entradas**: Archivos de código seleccionados.
* **Salidas**: Diffs limpios listos para revisión.
* **Herramientas**: `replace_file_content`, `multi_replace_file_content`.
* **Límites**: No añade nuevas características ni lógica.
* **Checklist**:
  * [ ] Ruff pasa limpio tras la refactorización.
  * [ ] Las firmas de métodos no rompen la compatibilidad existente.

---

### 2.4 Testing Agent (Agente de Pruebas)
* **Objetivo**: Garantizar una cobertura de tests robusta, rápida e independiente.
* **Responsabilidades**:
  * Escribir tests unitarios y de integración para cada componente nuevo.
  * Mockear llamadas HTTP y Playwright para evitar dependencia externa.
* **Entradas**: Código de producción, `tests/`.
* **Salidas**: Archivos de test robustos (`test_*.py`).
* **Herramientas**: `write_to_file`, `replace_file_content`.
* **Límites**: No modifica lógica de negocio en producción.
* **Checklist**:
  * [ ] Los tests son deterministas (pasan siempre).
  * [ ] No realizan llamadas reales a internet.

---

### 2.5 Security Agent (Agente de Seguridad)
* **Objetivo**: Detectar vulnerabilidades, inyecciones de código y fugas de secretos en el repositorio.
* **Responsabilidades**:
  * Escanear el código en busca de credenciales hardcodeadas.
  * Verificar sanitización de entradas en consultas SQL y comandos del sistema.
* **Entradas**: Workspace completo.
* **Salidas**: Informe de hallazgos de seguridad y parches correctivos.
* **Checklist**:
  * [ ] Ningún archivo `.env` o secreto está trackeado en Git.
  * [ ] Las consultas de base de datos usan SQLAlchemy ORM correctamente (sin inyección SQL raw).

---

### 2.6 Documentation Agent (Agente de Documentación)
* **Objetivo**: Mantener todos los manuales y guías del proyecto completamente actualizados y claros.
* **Responsabilidades**:
  * Generar y actualizar archivos en `docs/`.
  * Asegurar que el `README.md` refleje exactamente cómo usar el sistema.
* **Entradas**: Cambios en arquitectura o lógica, documentación existente.
* **Salidas**: Archivos Markdown bien formateados.
* **Checklist**:
  * [ ] Los ejemplos de código en la documentación funcionan.
  * [ ] La terminología se mantiene alineada con `CONTEXT.md`.

---

## 3. Protocolo de Handoff entre Agentes

Cuando un agente especializado termina su trabajo, debe escribir un **Handoff Block** en el chat (o en un archivo temporal en `temp/`) para que el Orchestrator o el siguiente agente pueda continuar con total contexto.

### Formato de Handoff:
```markdown
### AGENT HANDOFF: [Nombre del Agente]
- **Objetivo Completado**: Resumen corto del trabajo realizado.
- **Cambios Realizados**: Lista de archivos creados o modificados.
- **Riesgos Identificados**: Posibles efectos colaterales.
- **Instrucciones para el Siguiente Agente**: Qué se debe hacer ahora (ej. "Testing Agent: escribir pruebas para el método X").
```
