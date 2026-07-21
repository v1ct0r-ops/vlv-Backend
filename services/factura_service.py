from sqlalchemy.orm import Session
from decimal import Decimal

from models.producto import Producto
from models.movimiento import MovimientoInventario, TipoMovimiento
from models.ingreso_factura import IngresoFactura, IngresoFacturaDetalle
from schemas.ingreso_factura import IngresoFacturaCreate


class FacturaService:
    def __init__(self, db: Session):
        self.db = db

    def registrar_ingreso(self, datos: IngresoFacturaCreate, empresa_id: int):
        """
        Registra el ingreso de stock por factura (grupo de formatos).
        Todo en una sola transaccion: si un item falla, no se ingresa nada.
        empresa_id lo impone el usuario autenticado (multi-tenant).
        """
        try:
            factura = IngresoFactura(
                numero_factura=datos.numero_factura,
                proveedor=datos.proveedor,
                observaciones=datos.observaciones,
                empresa_id=empresa_id,
            )
            self.db.add(factura)
            self.db.flush()

            for item in datos.items:
                # el producto debe ser del mismo tenant: nadie ingresa stock a otra empresa
                producto = self.db.query(Producto).filter(
                    Producto.id == item.producto_id,
                    Producto.empresa_id == empresa_id,
                ).first()
                if not producto:
                    raise ValueError(f"Producto {item.producto_id} no encontrado")

                subtotal = None
                if item.costo_unitario is not None:
                    subtotal = Decimal(item.costo_unitario) * item.cantidad

                producto.stock_actual += item.cantidad

                self.db.add(IngresoFacturaDetalle(
                    factura_id=factura.id,
                    producto_id=producto.id,
                    cantidad=item.cantidad,
                    costo_unitario=item.costo_unitario,
                    subtotal=subtotal,
                    stock_resultante=producto.stock_actual,
                ))

                # movimiento de inventario para trazabilidad
                self.db.add(MovimientoInventario(
                    producto_id=producto.id,
                    cantidad=item.cantidad,
                    precio_unitario=item.costo_unitario or 0,
                    total=subtotal or 0,
                    tipo=TipoMovimiento.INGRESO_FACTURA.value,
                    empresa_id=empresa_id,
                ))

            self.db.commit()
            self.db.refresh(factura)
            return factura
        except Exception:
            self.db.rollback()
            raise

    def obtener_factura(self, factura_id: int, empresa_id: int):
        # scoping por tenant: una empresa no puede leer facturas de otra
        factura = self.db.query(IngresoFactura).filter(
            IngresoFactura.id == factura_id,
            IngresoFactura.empresa_id == empresa_id,
        ).first()
        if not factura:
            raise ValueError(f"Factura {factura_id} no encontrada")

        detalles = self.db.query(IngresoFacturaDetalle).filter(
            IngresoFacturaDetalle.factura_id == factura.id
        ).all()
        return factura, detalles

    def formatear_factura(self, factura: IngresoFactura, detalles):
        """Arma el detalle completo (mismo formato que usa el PDF y la API)"""
        items = []
        total_unidades = 0
        total_kg = 0
        total_costo = 0
        hay_costos = False
        for detalle in detalles:
            producto = self.db.query(Producto).filter(
                Producto.id == detalle.producto_id,
                Producto.empresa_id == factura.empresa_id,
            ).first()
            items.append({
                "producto": f"{producto.nombre} {producto.formato}",
                "formato": producto.formato,
                "cantidad": detalle.cantidad,
                "costo_unitario": int(detalle.costo_unitario) if detalle.costo_unitario is not None else None,
                "subtotal": int(detalle.subtotal) if detalle.subtotal is not None else None,
                # snapshot al momento del ingreso; el stock actual puede haber cambiado despues
                "stock_resultante": detalle.stock_resultante if detalle.stock_resultante is not None else producto.stock_actual,
            })
            total_unidades += detalle.cantidad
            total_kg += producto.kg_por_unidad * detalle.cantidad
            if detalle.subtotal is not None:
                total_costo += int(detalle.subtotal)
                hay_costos = True

        return {
            "id": factura.id,
            "numero_factura": factura.numero_factura,
            "proveedor": factura.proveedor,
            "fecha": factura.fecha,
            "observaciones": factura.observaciones,
            "items": items,
            "total_unidades": total_unidades,
            "total_kg": total_kg,
            "total_costo": total_costo if hay_costos else None,
        }
