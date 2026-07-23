from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from core.database import Base
from core.timezone import ahora_utc


class Empresa(Base):
    """Tenant del sistema. Hoy hay una sola fila (tu pyme), pero toda la
    lógica de auth ya cuelga de aquí para soportar múltiples clientes mañana."""
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    rut = Column(String(20), nullable=False, unique=True)   # identificador legal, único por tenant
    activo = Column(Boolean, nullable=False, default=True)   # baja lógica: nunca borras un tenant, lo desactivas
    creado_en = Column(DateTime(timezone=True), nullable=False, default=ahora_utc)

    # back_populates conecta ambos lados: Empresa.usuarios <-> Usuario.empresa
    usuarios = relationship("Usuario", back_populates="empresa")
