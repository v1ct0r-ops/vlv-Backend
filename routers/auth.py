from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import create_access_token
from core.deps import get_current_user
from core.limiter import limiter
from services.usuario_service import UsuarioService
from schemas.auth import Token
from schemas.usuario import UsuarioRead
from models.usuario import Usuario

router = APIRouter(tags=["Auth"])


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,  # requerido por slowapi para leer la IP del cliente
    # OAuth2PasswordRequestForm lee campos de formulario 'username' y 'password'
    # (no JSON). Es lo que exige el estándar OAuth2 password flow y lo que el
    # botón "Authorize" de /docs usa automáticamente. Requiere python-multipart.
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Autentica credenciales y devuelve un access token JWT.

    'username' del formulario = email del usuario.

    Rate limit: 5 intentos por minuto por IP (mitiga fuerza bruta).
    """
    servicio = UsuarioService(db)
    usuario = servicio.autenticar(form_data.username, form_data.password)

    if usuario is None:
        # Mismo mensaje para email inexistente y clave incorrecta: no revelamos
        # cuál de los dos falló (evita enumerar usuarios).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )

    # empresa_id viaja en el token desde ya: base del filtrado multi-tenant.
    access_token = create_access_token(
        data={
            "sub": usuario.email,
            "empresa_id": usuario.empresa_id,
            "rol": usuario.rol,
        }
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UsuarioRead)
def leer_usuario_actual(current: Usuario = Depends(get_current_user)):
    """Ruta protegida de ejemplo: devuelve el usuario dueño del token.
    Sirve al frontend para saber quién está logueado tras el login."""
    return current
