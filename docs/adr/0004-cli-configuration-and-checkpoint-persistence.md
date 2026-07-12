# ADR 0004: Configuración CLI y Persistencia por Checkpoints (ADR-0004)

* **Fecha**: 2026-07-02
* **Estado**: Aceptado
* **Contexto**: El scraper por navegador toma tiempo de ejecución. Si el script se detiene a la mitad por un corte de red, fin de memoria (OOM) o interrupción manual (Ctrl+C), se perdía todo el progreso acumulado.

---

## Decisión
Se decidió implementar:
1. Un archivo JSON de salida como persistencia principal en el orquestador (`MetaAdsBrowserRunner`).
2. **Checkpoints automáticos**: Escritura completa del JSON de resultados en el disco después de procesar cada palabra clave.
3. **Signal handlers**: Captura de señales SIGINT (Ctrl+C) y SIGTERM para salvar la memoria temporal de resultados en el archivo JSON antes de salir.
4. **Modo Append y Resume**: Capacidad de leer archivos JSON previos para evitar re-scrapings de dominios y library_ids conocidos.

---

## Consecuencias

### Positivas:
* **Resiliencia**: Si el script es interrumpido, se salvan los datos procesados de las keywords completadas.
* **Flexibilidad**: Posibilidad de dividir ejecuciones o retomar búsquedas de días anteriores sin desperdiciar recursos ni duplicar dominios.
* **Deduplicación**: Ahorro de ancho de banda y menor volumen de interacción con Meta al descartar de forma temprana anuncios ya registrados.

### Negativas:
* **Escritura completa**: Escribir todo el archivo JSON en cada keyword puede ser ineficiente si el tamaño del archivo escala a megabytes de datos. En el futuro, se resolverá mediante la integración con la base de datos (Fase 4.1).
