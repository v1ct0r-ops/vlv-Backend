"""Dependencias de autenticación reutilizables en cualquier router.

get_current_user es la pieza que "protege" una ruta: FastAPI la resuelve antes
de entrar al endpoint; si falla, el endpoint nunca se ejecuta.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import decode_access_token
from schemas.auth import TokenData
from models.usuario import Usuario

# tokenUrl apunta al endpoint que emite el token (POST /token). Solo sirve para
# que /docs sepa dónde pedir credenciales en el botón "Authorize"; no cambia la
# lógica. OAuth2PasswordBearer extrae el header "Authorization: Bearer <token>".
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Decodifica el JWT, carga el usuario y valida que siga activo.

    Devuelve el objeto ORM Usuario completo: el endpoint protegido recibe así
    su email, rol y empresa_id sin volver a consultar nada."""
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        empresa_id = payload.get("empresa_id")
        if email is None or empresa_id is None:
            raise credenciales_invalidas
        token_data = TokenData(email=email, empresa_id=empresa_id, rol=payload.get("rol"))
    except InvalidTokenError:
        # firma inválida, token expirado o manipulado
        raise credenciales_invalidas

    # Filtramos por email Y empresa_id: el token dice a qué tenant pertenece,
    # así el mismo email en otra empresa nunca resuelve al usuario equivocado.
    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.email == token_data.email,
            Usuario.empresa_id == token_data.empresa_id,
        )
        .first()
    )
    if usuario is None:
        # Token válido pero el usuario ya no existe (borrado/movido).
        raise credenciales_invalidas
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )
    return usuario


def get_current_admin(current: Usuario = Depends(get_current_user)) -> Usuario:
    """Encadena sobre get_current_user y además exige rol admin. Úsala para
    rutas de gestión (crear usuarios, editar precios, etc.)."""
    if current.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol de administrador",
        )
    return current
