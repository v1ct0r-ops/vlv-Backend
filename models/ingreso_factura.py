from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from core.database import Base
from core.timezone import ahora_utc

class IngresoFactura(Base):
    __tablename__ = "ingresos_factura"

    id = Column(Integer, primary_key=True, index=True)
    numero_factura = Column(String(50), nullable=False)
    proveedor = Column(String(100), nullable=False)
    fecha = Column(DateTime(timezone=True), default=ahora_utc)
    observaciones = Column(String(500), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)  # tenant


class IngresoFacturaDetalle(Base):
    __tablename__ = "ingresos_factura_detalles"

    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("ingresos_factura.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(10,2), nullable=True) # costo de compra segun la factura, opcional
    subtotal = Column(Numeric(12,2), nullable=True)
    stock_resultante = Column(Integer, nullable=True) # snapshot del stock al momento del ingreso (respaldo historico)
