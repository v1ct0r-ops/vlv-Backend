"""Lógica de negocio de usuarios: crear y autenticar.

Sigue el patrón del resto del repo (FacturaService, RendicionService): una clase
que recibe la Session en el constructor y expone métodos de dominio.
"""
from sqlalchemy.orm import Session

from models.usuario import Usuario
from schemas.usuario import UsuarioCreate
from core.security import hash_password, verify_password

# Hash válido calculado una sola vez al importar. Lo usamos cuando el email no
# existe para que autenticar() tarde lo mismo con o sin usuario (anti-timing).
_DUMMY_HASH = hash_password("timing-attack-mitigation")


class UsuarioService:
    def __init__(self, db: Session):
        self.db = db

    def obtener_por_email(self, email: str, empresa_id: int | None = None) -> Usuario | None:
        """Busca por email. Hoy hay una sola empresa, así que filtrar por
        empresa_id es opcional; el día que haya varias, este parámetro deja de
        ser opcional (dos empresas pueden tener el mismo email)."""
        query = self.db.query(Usuario).filter(Usuario.email == email)
        if empresa_id is not None:
            query = query.filter(Usuario.empresa_id == empresa_id)
        return query.first()

    def autenticar(self, email: str, password: str) -> Usuario | None:
        """Devuelve el usuario si las credenciales son válidas, si no None.

        Verificamos el hash SIEMPRE, incluso si el usuario no existe, para no
        filtrar por tiempo de respuesta qué emails están registrados
        (mitigación de user-enumeration por timing)."""
        usuario = self.obtener_por_email(email)
        if usuario is None:
            # Gastamos el mismo tiempo que una verificación real, con un hash válido.
            verify_password(password, _DUMMY_HASH)
            return None
        if not verify_password(password, usuario.hashed_password):
            return None
        return usuario

    def listar_por_empresa(self, empresa_id: int) -> list[Usuario]:
        """Filtrado multi-tenant real: solo usuarios de ESA empresa. Un admin
        nunca ve usuarios de otro tenant."""
        return (
            self.db.query(Usuario)
            .filter(Usuario.empresa_id == empresa_id)
            .order_by(Usuario.id)
            .all()
        )

    def crear(self, datos: UsuarioCreate, empresa_id: int) -> Usuario:
        """Crea un usuario hasheando la contraseña. empresa_id lo impone el
        backend (no el cliente) para no permitir alta en empresa ajena."""
        usuario = Usuario(
            email=datos.email,
            hashed_password=hash_password(datos.password),
            nombre=datos.nombre,
            rol=datos.rol,
            empresa_id=empresa_id,
        )
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario
