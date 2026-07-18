from sqlalchemy.orm import Session
from sqlalchemy import extract
from decimal import Decimal
from typing import Optional

from models.producto import Producto
from models.movimiento import MovimientoInventario, TipoMovimiento
from models.rendicion import Rendicion, RendicionVenta, RendicionAjuste, TipoAjuste
from schemas.rendicion import RendicionCreate


class RendicionService:
    def __init__(self, db: Session):
        self.db = db

    def registrar_rendicion(self, chofer: str, datos: RendicionCreate):
        """
        Registra la rendicion completa del chofer (documento independiente).
        Valida que lo vendido no supere el stock del inventario: si una linea
        no alcanza, se rechaza TODO (rollback) y no se guarda nada.
        """
        try:
            rendicion = Rendicion(
                chofer=chofer,
                bencina=Decimal(datos.bencina),
                comision_pagada=datos.comision_pagada,
                observaciones=datos.observaciones,
            )
            self.db.add(rendicion)
            self.db.flush()

            total_ventas = Decimal(0)
            total_kg = 0
            total_comision = Decimal(0)

            for venta in datos.ventas:
                producto = self.db.query(Producto).filter(
                    Producto.id == venta.producto_id
                ).first()
                if not producto:
                    raise ValueError(f"Producto {venta.producto_id} no encontrado")

                # el stock nunca puede quedar negativo: se rechaza toda la rendicion
                if producto.stock_actual < venta.cantidad:
                    raise ValueError(
                        f"Stock insuficiente para {producto.formato}: "
                        f"vendidos {venta.cantidad}, disponibles {producto.stock_actual}. "
                        f"No se puede registrar la rendicion."
                    )

                producto.stock_actual -= venta.cantidad

                subtotal = Decimal(venta.precio_unitario) * venta.cantidad
                kg = producto.kg_por_unidad * venta.cantidad
                comision = Decimal(str(producto.comision_unitaria)) * venta.cantidad

                self.db.add(RendicionVenta(
                    rendicion_id=rendicion.id,
                    producto_id=producto.id,
                    cantidad=venta.cantidad,
                    precio_unitario=venta.precio_unitario,
                    subtotal=subtotal,
                    kg=kg,
                    comision=comision,
                ))

                self.db.add(MovimientoInventario(
                    producto_id=producto.id,
                    cantidad=venta.cantidad,
                    precio_unitario=venta.precio_unitario,
                    total=subtotal,
                    tipo=TipoMovimiento.VENTA.value,
                ))

                total_ventas += subtotal
                total_kg += kg
                total_comision += comision

            total_tarjetas = Decimal(0)
            for tarjeta in datos.tarjetas:
                self.db.add(RendicionAjuste(
                    rendicion_id=rendicion.id,
                    tipo=TipoAjuste.TARJETA.value,
                    monto=Decimal(tarjeta.monto),
                    descripcion=tarjeta.descripcion,
                ))
                total_tarjetas += Decimal(tarjeta.monto)

            total_descuentos = Decimal(0)
            for descuento in datos.descuentos:
                self.db.add(RendicionAjuste(
                    rendicion_id=rendicion.id,
                    tipo=TipoAjuste.DESCUENTO.value,
                    monto=Decimal(descuento.monto),
                    descripcion=descuento.descripcion,
                ))
                total_descuentos += Decimal(descuento.monto)

            # efectivo a rendir: si pago la comision hoy, tambien se descuenta
            efectivo = total_ventas - total_tarjetas - Decimal(datos.bencina) - total_descuentos
            if datos.comision_pagada:
                efectivo -= total_comision

            rendicion.total_ventas = total_ventas
            rendicion.total_kg = total_kg
            rendicion.total_tarjetas = total_tarjetas
            rendicion.total_descuentos = total_descuentos
            rendicion.total_comision = total_comision
            rendicion.efectivo_a_rendir = efectivo

            self.db.commit()
            self.db.refresh(rendicion)
            return rendicion
        except Exception:
            self.db.rollback()
            raise

    def rendiciones_cerradas_chofer(
        self, chofer: str, mes: Optional[int] = None, anio: Optional[int] = None
    ):
        """
        Todas las rendiciones "cerradas" del chofer, sin paginar.
        No existe un estado borrador: toda rendicion registrada ya es descargable
        en PDF desde su creacion, por lo que "cerrada" = toda Rendicion existente.
        """
        query = self.db.query(Rendicion).filter(Rendicion.chofer == chofer)
        if mes is not None:
            query = query.filter(extract("month", Rendicion.fecha) == mes)
        if anio is not None:
            query = query.filter(extract("year", Rendicion.fecha) == anio)
        rendiciones = query.order_by(Rendicion.fecha.desc()).all()
        return [self.formatear_rendicion(r) for r in rendiciones]

    def obtener_rendicion(self, rendicion_id: int):
        rendicion = self.db.query(Rendicion).filter(
            Rendicion.id == rendicion_id
        ).first()
        if not rendicion:
            raise ValueError(f"Rendicion {rendicion_id} no encontrada")
        return rendicion

    def formatear_rendicion(self, rendicion: Rendicion):
        """Arma el detalle completo (mismo formato que usa el PDF y la API)"""
        ventas = self.db.query(RendicionVenta).filter(
            RendicionVenta.rendicion_id == rendicion.id
        ).all()
        ajustes = self.db.query(RendicionAjuste).filter(
            RendicionAjuste.rendicion_id == rendicion.id
        ).all()

        ventas_formateadas = []
        for venta in ventas:
            producto = self.db.query(Producto).filter(
                Producto.id == venta.producto_id
            ).first()
            ventas_formateadas.append({
                "producto": f"{producto.nombre} {producto.formato}",
                "formato": producto.formato,
                "cantidad": venta.cantidad,
                "precio_unitario": int(venta.precio_unitario),
                "subtotal": int(venta.subtotal),
                "kg": venta.kg,
                "comision": int(venta.comision),
            })

        tarjetas = [
            {"monto": int(a.monto), "descripcion": a.descripcion}
            for a in ajustes if a.tipo == TipoAjuste.TARJETA.value
        ]
        descuentos = [
            {"monto": int(a.monto), "descripcion": a.descripcion}
            for a in ajustes if a.tipo == TipoAjuste.DESCUENTO.value
        ]

        return {
            "id": rendicion.id,
            "chofer": rendicion.chofer,
            "fecha": rendicion.fecha,
            "ventas": ventas_formateadas,
            "tarjetas": tarjetas,
            "descuentos": descuentos,
            "bencina": int(rendicion.bencina),
            "total_ventas": int(rendicion.total_ventas),
            "total_kg": rendicion.total_kg,
            "total_tarjetas": int(rendicion.total_tarjetas),
            "total_descuentos": int(rendicion.total_descuentos),
            "total_comision": int(rendicion.total_comision),
            "comision_pagada": rendicion.comision_pagada,
            "efectivo_a_rendir": int(rendicion.efectivo_a_rendir),
            "observaciones": rendicion.observaciones,
        }
