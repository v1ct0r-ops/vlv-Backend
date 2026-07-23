"""
Generacion de PDFs en el backend (fuente oficial de respaldo).
El frontend solo llama a los endpoints .../pdf y descarga el archivo.
"""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from core.timezone import a_chile_naive

COLOR_PRIMARIO = colors.HexColor("#1a3c5e")
COLOR_FILA_ALTERNA = colors.HexColor("#eef2f7")


def _formatear_peso(monto: int) -> str:
    """Formatea montos CLP: 150000 -> $150.000"""
    return "$" + f"{monto:,}".replace(",", ".")


def _estilos():
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(
        name="TituloDoc", fontSize=16, leading=20,
        textColor=COLOR_PRIMARIO, fontName="Helvetica-Bold",
    ))
    estilos.add(ParagraphStyle(
        name="Subtitulo", fontSize=10, leading=14, textColor=colors.grey,
    ))
    estilos.add(ParagraphStyle(
        name="Seccion", fontSize=11, leading=16,
        textColor=COLOR_PRIMARIO, fontName="Helvetica-Bold", spaceBefore=6,
    ))
    return estilos


def _tabla_base(data, col_widths):
    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.lightgrey),
    ]
    for fila in range(1, len(data)):
        if fila % 2 == 0:
            estilo.append(("BACKGROUND", (0, fila), (-1, fila), COLOR_FILA_ALTERNA))
    tabla.setStyle(TableStyle(estilo))
    return tabla


def _tabla_totales(filas, destacado=None):
    """Bloque de totales alineado a la derecha. `destacado` resalta esa etiqueta."""
    data = [[etiqueta, valor] for etiqueta, valor in filas]
    tabla = Table(data, colWidths=[90 * mm, 40 * mm], hAlign="RIGHT")
    estilo = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if destacado is not None:
        for i, (etiqueta, _) in enumerate(filas):
            if etiqueta == destacado:
                estilo += [
                    ("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"),
                    ("FONTSIZE", (0, i), (-1, i), 11),
                    ("TEXTCOLOR", (0, i), (-1, i), COLOR_PRIMARIO),
                    ("LINEABOVE", (0, i), (-1, i), 0.75, COLOR_PRIMARIO),
                ]
    tabla.setStyle(TableStyle(estilo))
    return tabla


def _bloque_firma(elementos, estilos):
    elementos.append(Spacer(1, 22 * mm))
    firma = Table(
        [["", ""], ["Firma chofer", "Firma responsable"]],
        colWidths=[70 * mm, 70 * mm],
    )
    firma.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.5, colors.black),
        ("LINEABOVE", (1, 1), (1, 1), 0.5, colors.black),
        ("ALIGN", (0, 1), (-1, 1), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, 1), 9),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
    ]))
    elementos.append(firma)


def generar_pdf_rendicion(rendicion: dict) -> bytes:
    """Genera el PDF con el detalle completo de la rendicion del chofer."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title=f"Rendicion N° {rendicion['id']} - {rendicion['chofer']}",
    )
    estilos = _estilos()
    elementos = []

    # Encabezado
    elementos.append(Paragraph("Rendición de cuenta — Chofer", estilos["TituloDoc"]))
    elementos.append(Paragraph(
        f"Folio N° {rendicion['id']} &nbsp;|&nbsp; Chofer: <b>{rendicion['chofer']}</b> "
        f"&nbsp;|&nbsp; Fecha: {a_chile_naive(rendicion['fecha']).strftime('%d-%m-%Y %H:%M')}",
        estilos["Subtitulo"],
    ))
    elementos.append(Spacer(1, 2 * mm))
    elementos.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARIO))
    elementos.append(Spacer(1, 4 * mm))

    # Ventas por formato
    elementos.append(Paragraph("Ventas por formato", estilos["Seccion"]))
    data = [["Formato", "Cantidad", "Precio unit.", "Kilos", "Comisión", "Subtotal"]]
    for venta in rendicion["ventas"]:
        data.append([
            venta["producto"],
            str(venta["cantidad"]),
            _formatear_peso(venta["precio_unitario"]),
            f"{venta['kg']} kg",
            _formatear_peso(venta["comision"]),
            _formatear_peso(venta["subtotal"]),
        ])
    data.append([
        "TOTAL", "", "",
        f"{rendicion['total_kg']} kg",
        _formatear_peso(rendicion["total_comision"]),
        _formatear_peso(rendicion["total_ventas"]),
    ])
    tabla = _tabla_base(data, [45 * mm, 20 * mm, 26 * mm, 24 * mm, 28 * mm, 30 * mm])
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, COLOR_PRIMARIO),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 4 * mm))

    # Tarjetas
    if rendicion["tarjetas"]:
        elementos.append(Paragraph("Pagos con tarjeta", estilos["Seccion"]))
        data = [["#", "Descripción", "Monto"]]
        for i, tarjeta in enumerate(rendicion["tarjetas"], start=1):
            data.append([str(i), tarjeta["descripcion"] or "-", _formatear_peso(tarjeta["monto"])])
        data.append(["", "Total tarjetas", _formatear_peso(rendicion["total_tarjetas"])])
        tabla = _tabla_base(data, [12 * mm, 121 * mm, 40 * mm])
        tabla.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
        elementos.append(tabla)
        elementos.append(Spacer(1, 4 * mm))

    # Descuentos
    if rendicion["descuentos"]:
        elementos.append(Paragraph("Descuentos", estilos["Seccion"]))
        data = [["#", "Descripción", "Monto"]]
        for i, descuento in enumerate(rendicion["descuentos"], start=1):
            data.append([str(i), descuento["descripcion"] or "-", _formatear_peso(descuento["monto"])])
        data.append(["", "Total descuentos", _formatear_peso(rendicion["total_descuentos"])])
        tabla = _tabla_base(data, [12 * mm, 121 * mm, 40 * mm])
        tabla.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
        elementos.append(tabla)
        elementos.append(Spacer(1, 4 * mm))

    # Resumen final
    elementos.append(Paragraph("Resumen", estilos["Seccion"]))
    comision_texto = "PAGADA (descontada del efectivo)" if rendicion["comision_pagada"] else "RETENIDA"
    filas = [
        ("Total ventas", _formatear_peso(rendicion["total_ventas"])),
        ("(-) Tarjetas", _formatear_peso(rendicion["total_tarjetas"])),
        ("(-) Bencina", _formatear_peso(rendicion["bencina"])),
        ("(-) Descuentos", _formatear_peso(rendicion["total_descuentos"])),
        (f"Comisión chofer [{comision_texto}]", _formatear_peso(rendicion["total_comision"])),
        ("EFECTIVO A RENDIR", _formatear_peso(rendicion["efectivo_a_rendir"])),
    ]
    elementos.append(_tabla_totales(filas, destacado="EFECTIVO A RENDIR"))

    if rendicion["observaciones"]:
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(
            f"<b>Observaciones:</b> {rendicion['observaciones']}", estilos["Subtitulo"]
        ))

    _bloque_firma(elementos, estilos)
    doc.build(elementos)
    return buffer.getvalue()


def generar_pdf_factura(factura: dict) -> bytes:
    """Genera el PDF del ingreso de stock por factura."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title=f"Ingreso factura {factura['numero_factura']}",
    )
    estilos = _estilos()
    elementos = []

    elementos.append(Paragraph("Ingreso de stock — Factura", estilos["TituloDoc"]))
    elementos.append(Paragraph(
        f"Factura N° {factura['numero_factura']} &nbsp;|&nbsp; "
        f"Proveedor: <b>{factura['proveedor']}</b> &nbsp;|&nbsp; "
        f"Fecha: {a_chile_naive(factura['fecha']).strftime('%d-%m-%Y %H:%M')}",
        estilos["Subtitulo"],
    ))
    elementos.append(Spacer(1, 2 * mm))
    elementos.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARIO))
    elementos.append(Spacer(1, 4 * mm))

    elementos.append(Paragraph("Formatos ingresados", estilos["Seccion"]))
    data = [["Formato", "Cantidad", "Costo unit.", "Subtotal", "Stock resultante"]]
    for item in factura["items"]:
        data.append([
            item["producto"],
            str(item["cantidad"]),
            _formatear_peso(item["costo_unitario"]) if item["costo_unitario"] is not None else "-",
            _formatear_peso(item["subtotal"]) if item["subtotal"] is not None else "-",
            str(item["stock_resultante"]),
        ])
    data.append([
        "TOTAL",
        str(factura["total_unidades"]),
        "",
        _formatear_peso(factura["total_costo"]) if factura["total_costo"] is not None else "-",
        "",
    ])
    tabla = _tabla_base(data, [48 * mm, 24 * mm, 30 * mm, 34 * mm, 37 * mm])
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, COLOR_PRIMARIO),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 4 * mm))

    elementos.append(_tabla_totales([
        ("Total unidades ingresadas", str(factura["total_unidades"])),
        ("Total kilos ingresados", f"{factura['total_kg']} kg"),
    ]))

    if factura["observaciones"]:
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(
            f"<b>Observaciones:</b> {factura['observaciones']}", estilos["Subtitulo"]
        ))

    _bloque_firma(elementos, estilos)
    doc.build(elementos)
    return buffer.getvalue()
