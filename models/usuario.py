from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from core.database import Base
from core.timezone import ahora_utc


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), nullable=False, index=True)
    # NUNCA se guarda la contraseña en claro. Solo el hash bcrypt (~60 chars).
    hashed_password = Column(String(255), nullable=False)

    nombre = Column(String(120), nullable=False)
    rol = Column(String(20), nullable=False, default="operador")  # "admin" | "operador" | "chofer" (ver core/roles.py)
    activo = Column(Boolean, nullable=False, default=True)         # baja lógica, no DELETE

    # Discriminador de tenant. Obligatorio desde hoy: cada usuario pertenece a una empresa.
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    empresa = relationship("Empresa", back_populates="usuarios")

    creado_en = Column(DateTime(timezone=True), nullable=False, default=ahora_utc)

    __table_args__ = (
        # Multi-tenant real: el email es único DENTRO de una empresa, no globalmente.
        # Así "jefe@correo.com" puede existir en dos empresas distintas mañana.
        # Requisito para el login por email con múltiples tenants: resolver la empresa
        # antes (subdominio / header X-Empresa) para saber cuál de los dos usuarios es.
        UniqueConstraint("empresa_id", "email", name="uq_usuario_empresa_email"),
    )
