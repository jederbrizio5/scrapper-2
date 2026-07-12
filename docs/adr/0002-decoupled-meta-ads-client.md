# ADR 0002: Cliente Meta Ads Desacoplado (ADR-0002)

* **Fecha**: 2026-06-28
* **Estado**: Aceptado
* **Contexto**: El sistema necesita interactuar con la Meta Ads Library para consultar anuncios, pero meter lógica de base de datos o persistencia dentro del cliente HTTP rompe el principio de responsabilidad única (SRP).

---

## Decisión
Se decidió diseñar un cliente HTTP (`MetaClient`) completamente desacoplado de la persistencia de datos. El cliente se encarga únicamente de realizar peticiones de red y mapear la respuesta JSON cruda a objetos tipados (DTOs) utilizando una capa estricta de parseo (`MetaParser`).

---

## Consecuencias

### Positivas:
* **Mantenibilidad**: Los cambios en el esquema de base de datos no afectan al cliente Meta Ads.
* **Testeabilidad**: Permite simular respuestas falsas de red (mocking con `responses`) de manera sencilla en las pruebas unitarias.
* **Reutilización**: El cliente puede ser empaquetado o reutilizado en otros componentes de forma independiente.

### Negativas:
* **Orquestación requerida**: Es necesario un componente intermedio (un orquestador o servicio de persistencia) que se encargue de recibir los DTOs del cliente y guardarlos mediante los repositorios en la base de datos.
