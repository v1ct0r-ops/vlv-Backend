from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from models.producto import Producto
from models.movimiento import MovimientoInventario
from schemas.movimiento import MovimientoCreate, MovimientoRead
from schemas.paginacion import Pagina, paginar

router = APIRouter(prefix="/movimientos", tags=["Movimientos"])

@router.post("/", response_model=MovimientoRead)
def registrar_venta(datos: MovimientoCreate, db: Session = Depends(get_db)):
    producto = db.query(Producto).filter(Producto.id == datos.producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if producto.stock_actual < datos.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    total = datos.cantidad * datos.precio_unitario

    producto.stock_actual -= datos.cantidad

    nuevo_movimiento = MovimientoInventario(
        producto_id = datos.producto_id,
        cantidad= datos.cantidad,
        precio_unitario = datos.precio_unitario,
        total=total,
    )

    db.add(nuevo_movimiento)
    db.commit()
    db.refresh(nuevo_movimiento)
    return nuevo_movimiento


# listado paginado de 10 para no sobrecargar la base de datos
@router.get("/", response_model=Pagina[MovimientoRead])
def listar_movimientos(page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    query = db.query(MovimientoInventario).order_by(MovimientoInventario.fecha.desc())
    return paginar(query, page)
