from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from core.database import get_db
from models.ingreso_factura import IngresoFactura, IngresoFacturaDetalle
from schemas.ingreso_factura import IngresoFacturaCreate, IngresoFacturaRead, IngresoFacturaResumen
from schemas.paginacion import Pagina, paginar
from services.factura_service import FacturaService
from services.pdf_service import generar_pdf_factura
from sqlalchemy import func

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.post("/facturas", response_model=IngresoFacturaRead)
def registrar_ingreso_factura(datos: IngresoFacturaCreate, db: Session = Depends(get_db)):
    """Ingresa stock por factura y deja movimientos INGRESO_FACTURA para trazabilidad"""
    try:
        servicio = FacturaService(db)
        factura = servicio.registrar_ingreso(datos)
        factura_obj, detalles = servicio.obtener_factura(factura.id)
        return servicio.formatear_factura(factura_obj, detalles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/facturas", response_model=Pagina[IngresoFacturaResumen])
def listar_facturas(page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    """Listado paginado de 10, mas recientes primero"""
    query = db.query(IngresoFactura).order_by(IngresoFactura.fecha.desc())
    pagina = paginar(query, page)

    resumenes = []
    for factura in pagina["items"]:
        total_unidades = db.query(func.coalesce(func.sum(IngresoFacturaDetalle.cantidad), 0)).filter(
            IngresoFacturaDetalle.factura_id == factura.id
        ).scalar()
        resumenes.append({
            "id": factura.id,
            "numero_factura": factura.numero_factura,
            "proveedor": factura.proveedor,
            "fecha": factura.fecha,
            "total_unidades": total_unidades,
        })
    pagina["items"] = resumenes
    return pagina


@router.get("/facturas/{factura_id}", response_model=IngresoFacturaRead)
def obtener_factura(factura_id: int, db: Session = Depends(get_db)):
    try:
        servicio = FacturaService(db)
        factura, detalles = servicio.obtener_factura(factura_id)
        return servicio.formatear_factura(factura, detalles)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/facturas/{factura_id}/pdf")
def descargar_pdf_factura(factura_id: int, db: Session = Depends(get_db)):
    """Descarga el PDF de respaldo del ingreso por factura"""
    try:
        servicio = FacturaService(db)
        factura, detalles = servicio.obtener_factura(factura_id)
        datos = servicio.formatear_factura(factura, detalles)
        pdf = generar_pdf_factura(datos)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ingreso_factura_{factura_id}.pdf"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
