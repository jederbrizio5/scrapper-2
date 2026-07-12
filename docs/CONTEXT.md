# Contexto de Dominio y Terminología (CONTEXT.md)

Este archivo explica los conceptos clave de negocio y el glosario técnico del proyecto. Ayuda a cualquier desarrollador o agente de IA a entender el dominio comercial del sistema.

---

## 1. Dominio de Negocio (Meta Prospecting)
El propósito de este sistema es automatizar la prospección B2B utilizando Meta Ads (Facebook e Instagram) como fuente de descubrimiento. La hipótesis fundamental es que **las empresas que invierten activamente en publicidad en Meta Ads tienen presupuesto y necesidad de mejorar sus embudos de ventas, captación y retención.**

Al capturar y enriquecer estos prospectos, creamos una base de datos calificada de leads de alto valor que posteriormente pueden ser contactados por un equipo de ventas o evaluados automáticamente por un algoritmo de scoring.

---

## 2. Glosario de Conceptos

### Discovery (Descubrimiento)
El proceso de buscar términos (keywords) en **Meta Ads Library**, identificar anuncios activos que dirigen el tráfico a una página web externa (fuera de Facebook/Instagram) y extraer la URL de destino final.

### Enrichment (Enriquecimiento)
El proceso de obtener más información del anunciante que no es visible en el anuncio plano. Esto incluye abrir los detalles del anuncio para leer sus redes sociales oficiales (Facebook, Instagram) y la cantidad de seguidores de cada una.

### Lead
Un cliente potencial calificado. En este sistema, un Lead se asocia a una **Company** (Empresa) y tiene un **Score** que determina su nivel de interés y viabilidad.

### Keyword (Palabra Clave)
El término de búsqueda utilizado en Meta Ads Library para filtrar anuncios. Ejemplos: "curso", "agencia", "ecommerce".

### Library ID (ID de Biblioteca)
Un identificador numérico único asignado por Meta a cada anuncio específico en su base de datos. Sirve para deduplicación y tracking.

### Landing URL
La URL final del sitio web de destino de la empresa que se anuncia. Por ejemplo, si el anuncio promociona un curso, la Landing URL será la página de ventas de ese curso.

### Domain (Dominio)
El nombre de host o dominio web extraído de la Landing URL (ej. `empresa.com`). Sirve para identificar y agrupar leads de una misma empresa, evitando duplicados.

### Advertiser Name (Nombre del Anunciante)
El nombre comercial de la página o perfil que está publicando los anuncios en Meta.

---

## 3. Entidades de Base de Datos y su Correspondencia

1. **Search**: Representa una búsqueda realizada (keyword, fecha, país, idioma, estado).
2. **Domain**: El dominio web del anunciante. Se deduplica a nivel de base de datos para no procesar dos veces el mismo sitio.
3. **Company**: La empresa detrás del dominio (nombre del anunciante, industria, idioma, país).
4. **Lead**: El registro de oportunidad de negocio (score, estado de contacto, fecha de creación).
