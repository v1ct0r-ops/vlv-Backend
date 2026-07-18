from sqlalchemy.orm import Session
from models.producto import Producto
from schemas.producto import FormatoGas, KG_POR_FORMATO, COMISION_POR_FORMATO

# precios de venta por defecto, editables despues via PUT /productos/{id}
PRECIO_DEFAULT = {
    FormatoGas.GALON_5: 8000,
    FormatoGas.GALON_11: 17000,
    FormatoGas.GALON_15: 23000,
    FormatoGas.GALON_45: 68000,
    FormatoGas.GALON_GRUA: 23000,
}

def seed_productos(db: Session):
    """
    Crea los 5 formatos de gas si no existen (idempotente).
    El inventario completo se trabaja solo con estos 5 productos.
    """
    for formato in FormatoGas:
        existe = db.query(Producto).filter(Producto.formato == formato.value).first()
        if not existe:
            db.add(Producto(
                nombre="Gas GLP",
                formato=formato.value,
                precio_unitario=PRECIO_DEFAULT[formato],
                stock_actual=0,
                kg_por_unidad=KG_POR_FORMATO[formato],
                comision_unitaria=COMISION_POR_FORMATO[formato],
            ))
    db.commit()
