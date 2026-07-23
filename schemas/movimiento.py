from pydantic import BaseModel, Field, field_serializer
from enum import Enum
from datetime import datetime

from core.timezone import a_chile_naive

class TipoMovimiento(str, Enum):
    VENTA = "VENTA"
    DEVOLUCION = "DEVOLUCION"
    INGRESO_FACTURA = "INGRESO_FACTURA"

class MovimientoCreate(BaseModel):
    producto_id : int
    cantidad: int = Field(gt=0)
    precio_unitario: int = Field(gt=0)
    tipo: TipoMovimiento = TipoMovimiento.VENTA

class MovimientoRead (BaseModel):
    id: int
    producto_id: int
    cantidad: int
    precio_unitario: int
    total: int
    tipo: str
    fecha: datetime

    @field_serializer("fecha")
    def _fecha_chile(self, v: datetime) -> datetime | None:
        return a_chile_naive(v)

    class Config:
        from_attributes= True