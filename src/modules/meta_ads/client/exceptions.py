class MetaException(Exception):
    """Excepción base para todos los errores del módulo de Meta."""

    pass


class RateLimitException(MetaException):
    """Lanzada cuando se supera el límite de peticiones (Rate Limit)."""

    pass


class AuthenticationException(MetaException):
    """Lanzada cuando hay problemas de autenticación o tokens inválidos/expirados."""

    pass


class ParsingException(MetaException):
    """Lanzada cuando ocurre un error procesando o parseando la respuesta de Meta."""

    pass


class RequestException(MetaException):
    """Lanzada cuando ocurre un error de red o de la petición HTTP."""

    pass
