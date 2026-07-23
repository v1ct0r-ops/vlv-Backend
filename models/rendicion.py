from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean
from core.database import Base
from core.timezone import ahora_utc
from enum import Enum as PyEnum

class TipoAjuste(PyEnum):
    TARJETA = "TARJETA"
    DESCUENTO = "DESCUENTO"

class Rendicion(Base):
    __tablename__ = "rendiciones"

    id = Column(Integer, primary_key=True, index=True)
    chofer = Column(String(100), nullable=False, index=True)
    fecha = Column(DateTime(timezone=True), default=ahora_utc)
    bencina = Column(Numeric(12,2), nullable=False, default=0) # un solo campo, se descuenta del efectivo a rendir
    total_ventas = Column(Numeric(12,2), nullable=False, default=0)
    total_kg = Column(Integer, nullable=False, default=0)
    total_tarjetas = Column(Numeric(12,2), nullable=False, default=0)
    total_descuentos = Column(Numeric(12,2), nullable=False, default=0)
    total_comision = Column(Numeric(12,2), nullable=False, default=0)
    comision_pagada = Column(Boolean, nullable=False, default=False) # True = se descuenta del efectivo, False = retenida
    efectivo_a_rendir = Column(Numeric(12,2), nullable=False, default=0)
    observaciones = Column(String(500), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)  # tenant


class RendicionVenta(Base):
    __tablename__ = "rendiciones_ventas"

    id = Column(Integer, primary_key=True, index=True)
    rendicion_id = Column(Integer, ForeignKey("rendiciones.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10,2), nullable=False)
    subtotal = Column(Numeric(12,2), nullable=False)
    kg = Column(Integer, nullable=False) # kg_por_unidad * cantidad
    comision = Column(Numeric(12,2), nullable=False) # comision_unitaria * cantidad


class RendicionAjuste(Base):
    __tablename__ = "rendiciones_ajustes"

    id = Column(Integer, primary_key=True, index=True)
    rendicion_id = Column(Integer, ForeignKey("rendiciones.id"), nullable=False)
    tipo = Column(String(20), nullable=False) # TARJETA o DESCUENTO
    monto = Column(Numeric(12,2), nullable=False)
    descripcion = Column(String(200), nullable=True)
