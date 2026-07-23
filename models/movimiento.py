from sqlalchemy import Column, Integer, Numeric, ForeignKey,String, DateTime
from core.database import Base
from core.timezone import ahora_utc
from enum import Enum as PyEnum

class TipoMovimiento(PyEnum):
    VENTA = "VENTA"
    DEVOLUCION = "DEVOLUCION"
    INGRESO_FACTURA = "INGRESO_FACTURA"

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventarios"

    id = Column(Integer, primary_key=True , index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10,2), nullable=False)
    total = Column(Numeric(10,2), nullable=False)
    tipo = Column(String(20), default="VENTA")
    fecha = Column(DateTime(timezone=True), default=ahora_utc)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)  # tenant

