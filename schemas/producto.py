from enum import Enum
from pydantic import BaseModel, Field

class FormatoGas(str, Enum):
    GALON_5 = "5kg"
    GALON_11 = "11kg"
    GALON_15 = "15kg"
    GALON_45 = "45kg"
    GALON_GRUA = "gruas"

# kilos por unidad de cada formato (ojo: gruas pesa 15kg)
KG_POR_FORMATO = {
    FormatoGas.GALON_5: 5,
    FormatoGas.GALON_11: 11,
    FormatoGas.GALON_15: 15,
    FormatoGas.GALON_45: 45,
    FormatoGas.GALON_GRUA: 15,
}

# comision del chofer por unidad vendida segun formato
COMISION_POR_FORMATO = {
    FormatoGas.GALON_5: 1500,
    FormatoGas.GALON_11: 1500,
    FormatoGas.GALON_15: 1600,
    FormatoGas.GALON_45: 3500,
    FormatoGas.GALON_GRUA: 1500,
}

class ProductoBase(BaseModel):
    nombre: str = Field(min_length=3, max_length=50)
    formato: FormatoGas


class ProductoCreate(ProductoBase):
    precio_compra: float = Field(ge=0, default=0)   # costo para la pyme
    ganancia: float = Field(ge=0, default=0)        # margen que decide el admin
    # opcional: si no se envía, se calcula como precio_compra + ganancia
    precio_venta: float | None = Field(default=None, gt=0)
    stock_actual: int = Field(ge=0, default=0)

class ProductoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=50)
    precio_compra: float | None = Field(default=None, ge=0)
    ganancia: float | None = Field(default=None, ge=0)
    # si se envía, sobrescribe el cálculo automático (override manual del admin)
    precio_venta: float | None = Field(default=None, gt=0)
    stock_actual: int | None = Field(default=None, ge=0)
    comision_unitaria: float | None = Field(default=None, ge=0)

# Vista completa: admin y operador. Expone costo y margen.
class ProductoRead(ProductoBase):
    id: int
    precio_compra: float
    ganancia: float
    precio_venta: float
    stock_actual: int
    kg_por_unidad: int
    comision_unitaria: float
    empresa_id: int

    class Config:
        from_attributes = True

# Vista del chofer: solo lo que necesita para vender. Oculta precio_compra y
# ganancia (costos internos de la pyme). id se mantiene porque el chofer lo usa
# para registrar sus ventas/rendiciones.
class ProductoReadChofer(BaseModel):
    id: int
    formato: FormatoGas
    precio_venta: float

    class Config:
        from_attributes = True
