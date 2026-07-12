# Guía de Seguridad y Escaneo de Vulnerabilidades (SECURITY.md)

Este documento describe las políticas de seguridad del proyecto, la gestión de secretos y cómo evitar inyecciones de código y bloqueos operativos.

---

## 1. Gestión de Secretos
* **Nunca** expongas claves, tokens de acceso o contraseñas en el repositorio de Git.
* El archivo `.env` está en `.gitignore` por defecto para evitar subidas accidentales.
* Si agregas nuevas variables de entorno, agrégalas con valores ficticios en `.env.example` para que otros desarrolladores sepan qué configurar.

---

## 2. Prevención de Inyección de Código

### Inyección SQL
* No construyas consultas SQL mediante concatenación directa de strings.
* Utiliza siempre la interfaz de SQLAlchemy ORM, la cual parametriza automáticamente todas las entradas a la base de datos:
  ```python
  # CORRECTO (SQLAlchemy parametriza automáticamente la entrada)
  session.query(Domain).filter(Domain.dominio == user_input).first()

  # INCORRECTO (Vulnerable a Inyección SQL)
  session.execute(f"SELECT * FROM domains WHERE dominio = '{user_input}'")
  ```

---

## 3. Seguridad Operativa (Evitar Bloqueos de Meta)
El scraper de Meta Ads Library implementa medidas activas para simular tráfico humano y evitar baneos de IP o bloqueos del servicio:

* **Modificación de navigator.webdriver**: Sobreescribimos el valor nativo para que aparezca como `undefined`, evitando firmas de automatización estándar.
* **Jitter aleatorio**: Agregamos un delay aleatorio de ±30% en todas las esperas e interacciones.
* **Rotación de Proxies**: Utiliza el flag `--proxy-list` con una lista de proxies de alta calidad si realizas adquisiciones a gran escala.
* **Recreación de Sesiones**: En ejecuciones largas, el runner recrea el contexto y la página periódicamente para no acumular cookies que puedan resultar sospechosas.
