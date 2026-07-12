# Guía de Prompts (PROMPT_GUIDE.md)

Esta guía contiene plantillas de prompts optimizadas que tú (el usuario) puedes copiar y pegar para instruir a cualquier agente de IA a continuar el proyecto sin perder calidad.

---

## 1. Prompt para Iniciar una Nueva Fase de Desarrollo
Copia este prompt cuando quieras que el agente comience una fase completa (ej. la Fase 4):

```text
Actúa como un Principal Software Architect. 
Revisa el estado actual del proyecto leyendo 'docs/PROJECT_STATE.md' y el backlog en 'docs/TASKS.md'.
Quiero implementar la Fase X [nombre de la fase].
Por favor:
1. Revisa los archivos involucrados en esta fase.
2. Escribe una propuesta de plan en 'docs/phases/' siguiendo la plantilla obligatoria 'docs/phases/TEMPLATE.md'.
3. Detalla qué cambios harás, cómo los probarás y los riesgos.
No implementes nada todavía. Preséntame el plan para mi aprobación.
```

---

## 2. Prompt para Corregir un Bug
Copia este prompt si detectas un error en la ejecución o un test fallido:

```text
Actúa como un Testing & Debugging Agent.
Se ha detectado el siguiente error en el sistema:
[pega aquí el error o mensaje de log]
Por favor:
1. Analiza el código relacionado para encontrar la causa raíz.
2. Propón una solución segura que mantenga la compatibilidad con el resto del sistema.
3. Asegúrate de añadir o corregir el test unitario correspondiente en 'tests/'.
4. Ejecuta './scripts/check.sh' y confirma que pasa limpio antes de finalizar.
```

---

## 3. Prompt para Integrar una Tarea de Refactorización
Copia este prompt si quieres limpiar partes del código para que sean más legibles:

```text
Actúa como un Refactoring Agent.
Quiero mejorar la legibilidad y estructura del módulo: [ruta/al/archivo.py].
Por favor:
1. Revisa que todas las funciones tengan type hints completos y docstrings comprensibles.
2. Elimina cualquier redundancia o código muerto.
3. No alteres la funcionalidad externa.
4. Asegúrate de correr los tests correspondientes para verificar que no rompiste nada.
```
