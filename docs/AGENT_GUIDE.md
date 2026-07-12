# Guía para Agentes de IA (AGENT_GUIDE.md)

Este documento es una referencia de instrucciones directas para cualquier agente de IA o modelo LLM que trabaje en este repositorio. Ayuda a evitar la pérdida de contexto e instruye sobre cómo respetar las reglas permanentes del proyecto.

---

## 1. Reglas de Comportamiento del Agente
Si eres una IA que ha sido invocada para realizar una tarea en este proyecto:

1. **Leer la Memoria Persistente**: Revisa `docs/PROJECT_STATE.md` para conocer el estado actual y `docs/TASKS.md` para ver el backlog.
2. **Respetar la Modularidad**: No mezcles responsabilidades. La base de datos, el scraper Playwright y la lógica de negocio deben estar desacoplados.
3. **No Hardcodear**: Lee la configuración desde `src/config/settings.py` y agrégala en `.env` si es nueva.
4. **Verificación Obligatoria**: Antes de terminar tu turno, ejecuta `./scripts/check.sh` y asegúrate de que todos los tests pasen (Exit code 0).
5. **Escribir Handoff**: Deja un bloque de handoff al final del chat detallando qué hiciste y qué sigue (conforme a `docs/AGENTS.md`).

---

## 2. Formato de Cambios de Código
Cuando edites un archivo, prefiere modificaciones contiguas específicas y añade comentarios descriptivos explicativos (útiles para desarrolladores principiantes). Mantén la compatibilidad hacia atrás.

---

## 3. Manejo de Errores de Playwright
* Si estás depurando interacciones con Playwright en Meta Ads Library, recuerda que Meta utiliza **React** con divs superpuestos. Usa clics nativos JS mediante `page.evaluate('el => el.click()')` si los clics tradicionales de Playwright fallan.
* Todas las interacciones deben incluir un jitter aleatorio de ±30% para simular tráfico humano.
