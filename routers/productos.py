from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.deps import get_current_user, get_current_admin
from core.roles import Rol
from models.usuario import Usuario
from models.producto import Producto
from models.movimiento import MovimientoInventario
from schemas.producto import (
    ProductoCreate, ProductoRead, ProductoReadChofer, ProductoUpdate,
    KG_POR_FORMATO, COMISION_POR_FORMATO,
)
from fastapi import HTTPException


def _serializar_para(usuario: Usuario, producto: Producto):
    """El chofer solo ve formato + precio_venta; admin y operador ven todo
    (costo de compra y margen incluidos)."""
    if usuario.rol == Rol.CHOFER:
        return ProductoReadChofer.model_validate(producto)
    return ProductoRead.model_validate(producto)

router = APIRouter(
    prefix="/productos",
    tags=["Productos"],
    dependencies=[Depends(get_current_user)],
)

# solo puede existir 1 producto por formato (maximo los 5 formatos de gas) POR empresa
@router.post("/", response_model= ProductoRead)
def crear_producto(
    producto: ProductoCreate,
    current: Usuario = Depends(get_current_admin),  # alta de producto/precio: solo admin
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

    datos = producto.model_dump()
    # precio_venta: si el admin no lo fija a mano, se calcula compra + ganancia
    if datos.get("precio_venta") is None:
        datos["precio_venta"] = datos["precio_compra"] + datos["ganancia"]

    nuevo_producto = Producto(
        **datos,
        kg_por_unidad=KG_POR_FORMATO[producto.formato],
        comision_unitaria=COMISION_POR_FORMATO[producto.formato],
        empresa_id=current.empresa_id,
    )
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    return nuevo_producto

# maximo 5 productos, uno por formato
# response_model Union: el chofer recibe la vista reducida, admin/operador la completa
@router.get("/", response_model=List[ProductoRead | ProductoReadChofer])
def listar_productos(
    current: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    productos = db.query(Producto).filter(Producto.empresa_id == current.empresa_id).all()
    return [_serializar_para(current, p) for p in productos]


@router.get("/{producto_id}", response_model=ProductoRead | ProductoReadChofer)
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
    return _serializar_para(current, producto)



# el formato no se puede cambiar para no romper la coherencia del inventario
@router.put("/{producto_id}", response_model= ProductoRead)
def actualizar_producto(
    producto_id: int,
    datos: ProductoUpdate,
    current: Usuario = Depends(get_current_admin),  # editar precio: solo admin (403 a operador/chofer)
    db: Session= Depends(get_db),
):
    producto = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.empresa_id == current.empresa_id,
    ).first()
    if not producto:
        raise HTTPException(status_code=404, detail= "Producto no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(producto, campo, valor)

    # Recalcular precio_venta:
    #  - si el admin lo mandó explícito -> ya quedó seteado (override manual).
    #  - si tocó compra o ganancia sin fijar precio_venta -> se recalcula.
    if "precio_venta" not in cambios and ("precio_compra" in cambios or "ganancia" in cambios):
        # float() evita mezclar Decimal (columna ya cargada) con float (payload)
        producto.precio_venta = float(producto.precio_compra) + float(producto.ganancia)

    db.commit()
    db.refresh(producto)
    return producto

@router.delete("/{producto_id}")
def eliminar_producto(
    producto_id: int,
    current: Usuario = Depends(get_current_admin),  # borrar producto: solo admin
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
