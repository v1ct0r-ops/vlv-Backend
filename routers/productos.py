from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.deps import get_current_user
from models.usuario import Usuario
from models.producto import Producto
from models.movimiento import MovimientoInventario
from schemas.producto import (
    ProductoCreate, ProductoRead, ProductoUpdate,
    KG_POR_FORMATO, COMISION_POR_FORMATO,
)
from fastapi import HTTPException

router = APIRouter(
    prefix="/productos",
    tags=["Productos"],
    dependencies=[Depends(get_current_user)],
)

# solo puede existir 1 producto por formato (maximo los 5 formatos de gas) POR empresa
@router.post("/", response_model= ProductoRead)
def crear_producto(
    producto: ProductoCreate,
    current: Usuario = Depends(get_current_user),
    db: Session= Depends(get_db),
):
    existe = db.query(Producto).filter(
        Producto.formato == producto.formato.value,
        Producto.empresa_id == current.empresa_id,
    ).first()
    if existe:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un producto con formato {producto.formato.value}. El inventario trabaja solo con los 5 formatos."
        )

    nuevo_producto = Producto(
        **producto.model_dump(),
        kg_por_unidad=KG_POR_FORMATO[producto.formato],
        comision_unitaria=COMISION_POR_FORMATO[producto.formato],
        empresa_id=current.empresa_id,
    )
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    return nuevo_producto

# maximo 5 productos, uno por formato
@router.get("/", response_model=List[ProductoRead])
def listar_productos(
    current: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Producto).filter(Producto.empresa_id == current.empresa_id).all()


@router.get("/{producto_id}", response_model=ProductoRead)
def obtener_producto(
    producto_id: int,
    current: Usuario = Depends(get_current_user),
    db:Session = Depends(get_db),
):
    producto = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.empresa_id == current.empresa_id,
    ).first()
    if not producto:
        raise HTTPException(status_code = 404, detail = "Producto no encontrado")
    return producto



# el formato no se puede cambiar para no romper la coherencia del inventario
@router.put("/{producto_id}", response_model= ProductoRead)
def actualizar_producto(
    producto_id: int,
    datos: ProductoUpdate,
    current: Usuario = Depends(get_current_user),
    db: Session= Depends(get_db),
):
    producto = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.empresa_id == current.empresa_id,
    ).first()
    if not producto:
        raise HTTPException(status_code=404, detail= "Producto no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(producto,campo,valor)

    db.commit()
    db.refresh(producto)
    return producto

@router.delete("/{producto_id}")
def eliminar_producto(
    producto_id: int,
    current: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    producto = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.empresa_id == current.empresa_id,
    ).first()
    if not producto:
        raise HTTPException(status_code= 404, detail= "Producto no encontrado")

    tiene_movimientos = db.query(MovimientoInventario).filter(
        MovimientoInventario.producto_id == producto_id,
        MovimientoInventario.empresa_id == current.empresa_id,
    ).first()
    if tiene_movimientos:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: el producto tiene movimientos de inventario asociados"
        )

    db.delete(producto)
    db.commit()
    return {"detail" : "Producto eliminado"}
