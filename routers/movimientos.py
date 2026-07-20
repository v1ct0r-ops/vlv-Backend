from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.deps import get_current_user
from models.usuario import Usuario
from models.producto import Producto
from models.movimiento import MovimientoInventario
from schemas.movimiento import MovimientoCreate, MovimientoRead
from schemas.paginacion import Pagina, paginar

router = APIRouter(
    prefix="/movimientos",
    tags=["Movimientos"],
    dependencies=[Depends(get_current_user)],
)

@router.post("/", response_model=MovimientoRead)
def registrar_venta(
    datos: MovimientoCreate,
    current: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    producto = db.query(Producto).filter(
        Producto.id == datos.producto_id,
        Producto.empresa_id == current.empresa_id,
    ).first()
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
        empresa_id=current.empresa_id,
    )

    db.add(nuevo_movimiento)
    db.commit()
    db.refresh(nuevo_movimiento)
    return nuevo_movimiento


# listado paginado de 10 para no sobrecargar la base de datos
@router.get("/", response_model=Pagina[MovimientoRead])
def listar_movimientos(
    page: int = Query(default=1, ge=1),
    current: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(MovimientoInventario)
        .filter(MovimientoInventario.empresa_id == current.empresa_id)
        .order_by(MovimientoInventario.fecha.desc())
    )
    return paginar(query, page)
