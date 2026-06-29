# Reglas de Desarrollo Permanentes

1. **Nunca romper compatibilidad sin justificar.**
2. **Siempre documentar cambios importantes.**
3. **Cada módulo debe ser independiente y tener responsabilidades únicas (Single Responsibility Principle).**
4. **Toda función debe ser testeable.**
5. **No duplicar lógica (Don't Repeat Yourself - DRY).**
6. **Evitar archivos gigantes. Mantener el código modular.**
7. **No escribir código muerto (Keep It Simple, Stupid - KISS). Eliminar el código que no se use.**
8. **Manejar errores correctamente (try-except con tipos específicos y logging, no solo `pass`).**
9. **Tipado estricto (Type hints en Python requeridos para cada función y método).**
10. **Configuración mediante archivos de configuración (variables de entorno, JSON, YAML). Nada de valores mágicos en el código.**
11. **Todo cambio importante en la arquitectura debe quedar documentado en `docs/DECISIONS.md`.**
12. **El estado del proyecto se debe verificar con `./scripts/check.sh` antes de considerar cualquier tarea como finalizada.**
13. **Toda fase debe tener archivo propio en `docs/phases/` con objetivo, alcance, pruebas, logs esperados y resultado final.**
14. **El flujo futuro de adquisicion debe priorizar navegador con Playwright; la API de Meta queda como componente secundario/mockeable.**
15. **Todo codigo nuevo debe seguir `docs/CODE_DOCUMENTATION.md` y `docs/LOGGING_AND_OBSERVABILITY.md`.**
