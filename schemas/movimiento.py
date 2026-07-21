from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

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

    class Config:
        from_attributes= True