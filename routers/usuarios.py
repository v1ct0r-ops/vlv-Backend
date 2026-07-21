from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.deps import get_current_admin
from models.usuario import Usuario
from schemas.usuario import UsuarioCreate, UsuarioRead
from services.usuario_service import UsuarioService

# Todas las rutas exigen rol admin (get_current_admin encadena get_current_user).
router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("/", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCreate,
    admin: Usuario = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Alta de usuario dentro de la empresa del admin.

    empresa_id se toma de admin.empresa_id (el usuario autenticado), NUNCA del
    cliente: así un admin no puede crear usuarios en una empresa ajena aunque
    manipule el body.
    """
    servicio = UsuarioService(db)

    # Email único dentro de la empresa (respeta el UniqueConstraint del modelo).
    if servicio.obtener_por_email(datos.email, admin.empresa_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email en tu empresa",
        )

    return servicio.crear(datos, empresa_id=admin.empresa_id)


@router.get("/", response_model=List[UsuarioRead])
def listar_usuarios(
    admin: Usuario = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Lista solo los usuarios de la empresa del admin (filtrado multi-tenant)."""
    return UsuarioService(db).listar_por_empresa(admin.empresa_id)
