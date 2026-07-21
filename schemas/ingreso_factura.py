from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class ItemFacturaCreate(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0)
    costo_unitario: Optional[int] = Field(default=None, gt=0)

class IngresoFacturaCreate(BaseModel):
    numero_factura: str = Field(min_length=1, max_length=50)
    proveedor: str = Field(min_length=2, max_length=100)
    observaciones: Optional[str] = Field(default=None, max_length=500)
    items: List[ItemFacturaCreate] = Field(min_length=1)

class ItemFacturaRead(BaseModel):
    producto: str # nombre + formato
    formato: str
    cantidad: int
    costo_unitario: Optional[int]
    subtotal: Optional[int]
    stock_resultante: int

class IngresoFacturaRead(BaseModel):
    id: int
    numero_factura: str
    proveedor: str
    fecha: datetime
    observaciones: Optional[str]
    items: List[ItemFacturaRead]
    total_unidades: int
    total_kg: int
    total_costo: Optional[int]

    class Config:
        from_attributes = True

class IngresoFacturaResumen(BaseModel):
    """Version liviana para el listado paginado"""
    id: int
    numero_factura: str
    proveedor: str
    fecha: datetime
    total_unidades: int

    class Config:
        from_attributes = True
