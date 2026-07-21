from pydantic import BaseModel


class Token(BaseModel):
    """Respuesta del endpoint /token. El nombre de los campos lo fija el
    estándar OAuth2: el cliente espera exactamente 'access_token' y 'token_type'."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Contenido útil que viaja DENTRO del JWT (el 'payload' que firmamos).

    No es lo que enviamos al cliente; es lo que decodificamos del token en cada
    request protegido para saber quién es y de qué empresa. Incluir empresa_id
    aquí desde el día 1 es la clave del diseño multi-tenant: el formato del token
    no cambia cuando entre el segundo cliente."""
    email: str | None = None
    empresa_id: int | None = None
    rol: str | None = None
