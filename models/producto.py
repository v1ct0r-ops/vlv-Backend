from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from core.database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column (Integer, primary_key= True, index = True)
    nombre = Column(String(50), nullable = False)
    formato = Column(String(30), nullable = False)  # único POR empresa, no global (ver __table_args__)

    # --- Estructura de precio (solo la ve/edita el admin) ---
    precio_compra = Column(Numeric(10,2), nullable = False, default = 0)  # costo del producto para la pyme
    ganancia = Column(Numeric(10,2), nullable = False, default = 0)       # margen que el admin decide ganar por unidad
    # precio final que ve el chofer. Normalmente = precio_compra + ganancia,
    # pero el admin puede sobrescribirlo manualmente al editar.
    precio_venta = Column(Numeric(10,2), nullable = False)

    stock_actual = Column(Integer, nullable = False, default =0)
    kg_por_unidad = Column(Integer, nullable = False) # kilos por unidad segun formato (gruas = 15)
    comision_unitaria = Column(Numeric(10,2), nullable = False, default = 0) # comision del chofer por unidad vendida
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)  # tenant

    # cada formato existe una vez POR empresa: "5kg" puede estar en dos tenants distintos
    __table_args__ = (
        UniqueConstraint("empresa_id", "formato", name="uq_producto_empresa_formato"),
    )
