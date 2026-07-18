from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from core.database import get_db
from models.rendicion import Rendicion
from schemas.rendicion import RendicionCreate, RendicionRead, RendicionResumen
from schemas.paginacion import Pagina, paginar
from services.rendicion_service import RendicionService
from services.pdf_service import generar_pdf_rendicion

router = APIRouter(prefix="/rendiciones", tags=["Rendiciones"])


@router.post("/chofer/{nombre_chofer}", response_model=RendicionRead)
def registrar_rendicion_chofer(nombre_chofer: str, datos: RendicionCreate, db: Session = Depends(get_db)):
    """Registra la rendicion del dia del chofer; si algo supera el stock se rechaza todo"""
    try:
        servicio = RendicionService(db)
        rendicion = servicio.registrar_rendicion(nombre_chofer, datos)
        return servicio.formatear_rendicion(rendicion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=Pagina[RendicionResumen])
def listar_rendiciones(page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    """Listado paginado de 10, mas recientes primero"""
    query = db.query(Rendicion).order_by(Rendicion.fecha.desc())
    return paginar(query, page)


@router.get("/chofer/{nombre_chofer}", response_model=Pagina[RendicionResumen])
def historial_rendiciones_chofer(
    nombre_chofer: str,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    """Historial de rendiciones del chofer (seguimiento de ventas), paginado de 10"""
    query = db.query(Rendicion).filter(
        Rendicion.chofer == nombre_chofer
    ).order_by(Rendicion.fecha.desc())
    return paginar(query, page)


@router.get("/chofer/{nombre_chofer}/cerradas", response_model=List[RendicionRead])
def rendiciones_cerradas_chofer(
    nombre_chofer: str,
    mes: Optional[int] = Query(default=None, ge=1, le=12),
    anio: Optional[int] = Query(default=None, ge=2000),
    db: Session = Depends(get_db),
):
    """Rendiciones del chofer con detalle completo, sin paginar; no existe estado borrador, filtra opcional por mes/anio"""
    servicio = RendicionService(db)
    return servicio.rendiciones_cerradas_chofer(nombre_chofer, mes, anio)


@router.get("/{rendicion_id}", response_model=RendicionRead)
def obtener_rendicion(rendicion_id: int, db: Session = Depends(get_db)):
    try:
        servicio = RendicionService(db)
        rendicion = servicio.obtener_rendicion(rendicion_id)
        return servicio.formatear_rendicion(rendicion)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{rendicion_id}/pdf")
def descargar_pdf_rendicion(rendicion_id: int, db: Session = Depends(get_db)):
    """Descarga el PDF con el detalle completo de la rendicion del chofer"""
    try:
        servicio = RendicionService(db)
        rendicion = servicio.obtener_rendicion(rendicion_id)
        datos = servicio.formatear_rendicion(rendicion)
        pdf = generar_pdf_rendicion(datos)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=rendicion_{rendicion_id}_{rendicion.chofer.replace(' ', '_')}.pdf"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
