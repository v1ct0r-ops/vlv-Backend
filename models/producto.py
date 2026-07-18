from sqlalchemy import Column, Integer, String, Numeric
from core.database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column (Integer, primary_key= True, index = True)
    nombre = Column(String(50), nullable = False)
    formato = Column(String(30), nullable = False, unique = True)
    precio_unitario = Column(Numeric(10,2), nullable = False)
    stock_actual = Column(Integer, nullable = False, default =0)
    kg_por_unidad = Column(Integer, nullable = False) # kilos por unidad segun formato (gruas = 15)
    comision_unitaria = Column(Numeric(10,2), nullable = False, default = 0) # comision del chofer por unidad vendida
