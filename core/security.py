"""Primitivas de seguridad: hashing de contraseñas (bcrypt) y JWT (PyJWT).

Este módulo NO conoce la base de datos ni FastAPI a propósito: son funciones
puras. Eso las hace fáciles de testear y reutilizar (login, registro, refresh).
"""
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from config import settings

# CryptContext elige el algoritmo y maneja verificación + rehash.
# deprecated="auto": si mañana cambias de esquema, passlib marca los hashes
# viejos y puedes re-hashearlos en el próximo login sin migración manual.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password_plano: str) -> str:
    """Devuelve el hash bcrypt. Cada hash lleva su propio salt embebido:
    dos usuarios con la misma clave tienen hashes distintos."""
    return pwd_context.hash(password_plano)


def verify_password(password_plano: str, hashed_password: str) -> bool:
    """Compara en tiempo constante (resistente a timing attacks). Nunca
    desencriptamos el hash — bcrypt es one-way; solo re-hasheamos y comparamos."""
    return pwd_context.verify(password_plano, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Firma un JWT con los claims de `data` más 'exp'.

    'data' típico: {"sub": email, "empresa_id": 1, "rol": "admin"}.
    'sub' (subject) es el claim estándar OAuth2 para identificar al usuario.
    """
    to_encode = data.copy()
    expira = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expira})
    # La firma usa SECRET_KEY: quien no la tenga no puede forjar tokens válidos.
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verifica firma y expiración; devuelve el payload. Lanza InvalidTokenError
    si el token es inválido, expiró o fue manipulado. El caller (get_current_user,
    Paso 3) traduce ese error a HTTP 401."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
