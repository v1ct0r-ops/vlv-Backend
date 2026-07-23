from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from typing import List, Optional

from core.timezone import a_chile_naive

class VentaRendicionCreate(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0)
    precio_unitario: int = Field(gt=0) # precio al que el chofer vendio cada galon

class AjusteCreate(BaseModel):
    """Transaccion de tarjeta o descuento: monto + descripcion opcional"""
    monto: int = Field(gt=0)
    descripcion: Optional[str] = Field(default=None, max_length=200)

class RendicionCreate(BaseModel):
    ventas: List[VentaRendicionCreate] = Field(min_length=1)
    tarjetas: List[AjusteCreate] = Field(default_factory=list) # pueden ser N transacciones
    descuentos: List[AjusteCreate] = Field(default_factory=list) # pueden ser N descuentos
    bencina: int = Field(ge=0, default=0) # un solo campo
    comision_pagada: bool = False # True = se paga hoy y se descuenta del efectivo, False = la retengo
    observaciones: Optional[str] = Field(default=None, max_length=500)

class VentaRendicionRead(BaseModel):
    producto: str
    formato: str
    cantidad: int
    precio_unitario: int
    subtotal: int
    kg: int
    comision: int

class AjusteRead(BaseModel):
    monto: int
    descripcion: Optional[str]

class RendicionRead(BaseModel):
    id: int
    chofer: str
    fecha: datetime
    ventas: List[VentaRendicionRead]
    tarjetas: List[AjusteRead]
    descuentos: List[AjusteRead]
    bencina: int
    total_ventas: int
    total_kg: int
    total_tarjetas: int
    total_descuentos: int
    total_comision: int
    comision_pagada: bool
    efectivo_a_rendir: int
    observaciones: Optional[str]

    @field_serializer("fecha")
    def _fecha_chile(self, v: datetime) -> datetime | None:
        return a_chile_naive(v)

    class Config:
        from_attributes = True

class RendicionResumen(BaseModel):
    """Version liviana para los listados paginados (seguimiento por chofer)"""
    id: int
    chofer: str
    fecha: datetime
    total_ventas: int
    total_kg: int
    total_comision: int
    comision_pagada: bool
    efectivo_a_rendir: int

    @field_serializer("fecha")
    def _fecha_chile(self, v: datetime) -> datetime | None:
        return a_chile_naive(v)

    class Config:
        from_attributes = True
