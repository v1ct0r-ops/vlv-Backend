from tests.conftest import cargar_stock

CHOFER = "Juan Perez"


def rendicion_completa(client, ids, comision_pagada=True):
    return client.post(f"/rendiciones/chofer/{CHOFER}", json={
        "ventas": [
            {"producto_id": ids["5kg"], "cantidad": 20, "precio_unitario": 8000},
            {"producto_id": ids["11kg"], "cantidad": 5, "precio_unitario": 17000},
            {"producto_id": ids["15kg"], "cantidad": 4, "precio_unitario": 23000},
            {"producto_id": ids["45kg"], "cantidad": 2, "precio_unitario": 68000},
            {"producto_id": ids["gruas"], "cantidad": 3, "precio_unitario": 23000},
        ],
        "tarjetas": [
            {"monto": 50000, "descripcion": "Transbank 12:30"},
            {"monto": 30000, "descripcion": "Transbank 15:10"},
            {"monto": 12990},
        ],
        "descuentos": [
            {"monto": 2000, "descripcion": "cliente frecuente"},
            {"monto": 3500},
        ],
        "bencina": 10000,
        "comision_pagada": comision_pagada,
        "observaciones": "rendicion del dia",
    })


STOCK_INICIAL = {"5kg": 50, "11kg": 30, "15kg": 20, "45kg": 10, "gruas": 15}

# valores esperados de la rendicion completa (calculados a mano)
TOTAL_VENTAS = 20*8000 + 5*17000 + 4*23000 + 2*68000 + 3*23000   # 542.000
TOTAL_KG = 20*5 + 5*11 + 4*15 + 2*45 + 3*15                      # 350 (gruas = 15kg)
TOTAL_COMISION = 20*1500 + 5*1500 + 4*1600 + 2*3500 + 3*1500     # 55.400
TOTAL_TARJETAS = 50000 + 30000 + 12990                           # 92.990
TOTAL_DESCUENTOS = 2000 + 3500                                   # 5.500
BENCINA = 10000


def test_rendicion_calculos_exactos_comision_pagada(client):
    ids = cargar_stock(client, STOCK_INICIAL)

    respuesta = rendicion_completa(client, ids, comision_pagada=True)
    assert respuesta.status_code == 200, respuesta.text
    rendicion = respuesta.json()

    assert rendicion["chofer"] == CHOFER
    assert rendicion["total_ventas"] == TOTAL_VENTAS == 542000
    assert rendicion["total_kg"] == TOTAL_KG == 350
    assert rendicion["total_comision"] == TOTAL_COMISION == 55400
    assert rendicion["total_tarjetas"] == TOTAL_TARJETAS == 92990
    assert rendicion["total_descuentos"] == TOTAL_DESCUENTOS == 5500
    assert rendicion["bencina"] == BENCINA
    assert rendicion["comision_pagada"] is True

    # comision pagada hoy: tambien se descuenta del efectivo
    esperado = TOTAL_VENTAS - TOTAL_TARJETAS - BENCINA - TOTAL_DESCUENTOS - TOTAL_COMISION
    assert rendicion["efectivo_a_rendir"] == esperado == 378110

    # detalle por linea: gruas vendio 3 -> 45 kg y comision 4.500
    gruas = next(v for v in rendicion["ventas"] if v["formato"] == "gruas")
    assert gruas["kg"] == 45
    assert gruas["comision"] == 4500
    assert gruas["subtotal"] == 69000

    # el stock descuenta lo vendido
    productos = {p["formato"]: p for p in client.get("/productos/").json()}
    assert productos["5kg"]["stock_actual"] == 30
    assert productos["11kg"]["stock_actual"] == 25
    assert productos["15kg"]["stock_actual"] == 16
    assert productos["45kg"]["stock_actual"] == 8
    assert productos["gruas"]["stock_actual"] == 12


def test_rendicion_comision_retenida(client):
    ids = cargar_stock(client, STOCK_INICIAL)

    rendicion = rendicion_completa(client, ids, comision_pagada=False).json()

    # comision retenida: NO se descuenta del efectivo, pero queda registrada
    esperado = TOTAL_VENTAS - TOTAL_TARJETAS - BENCINA - TOTAL_DESCUENTOS
    assert rendicion["efectivo_a_rendir"] == esperado == 433510
    assert rendicion["total_comision"] == 55400
    assert rendicion["comision_pagada"] is False


def test_rendicion_rechaza_venta_sobre_stock(client):
    ids = cargar_stock(client, {"5kg": 10})

    respuesta = client.post(f"/rendiciones/chofer/{CHOFER}", json={
        "ventas": [{"producto_id": ids["5kg"], "cantidad": 20, "precio_unitario": 8000}],
        "comision_pagada": False,
    })
    assert respuesta.status_code == 400
    assert "Stock insuficiente" in respuesta.json()["detail"]

    # rollback total: ni el stock ni las rendiciones cambiaron
    productos = {p["formato"]: p for p in client.get("/productos/").json()}
    assert productos["5kg"]["stock_actual"] == 10
    assert client.get("/rendiciones/").json()["total"] == 0


def test_rendicion_rechaza_linea_mixta_con_rollback(client):
    # una linea alcanza y la otra no: se rechaza TODO
    ids = cargar_stock(client, {"5kg": 50, "45kg": 1})

    respuesta = client.post(f"/rendiciones/chofer/{CHOFER}", json={
        "ventas": [
            {"producto_id": ids["5kg"], "cantidad": 10, "precio_unitario": 8000},
            {"producto_id": ids["45kg"], "cantidad": 3, "precio_unitario": 68000},
        ],
        "comision_pagada": False,
    })
    assert respuesta.status_code == 400

    productos = {p["formato"]: p for p in client.get("/productos/").json()}
    assert productos["5kg"]["stock_actual"] == 50
    assert productos["45kg"]["stock_actual"] == 1


def test_rendicion_producto_inexistente(client):
    cargar_stock(client, {"5kg": 10})
    respuesta = client.post(f"/rendiciones/chofer/{CHOFER}", json={
        "ventas": [{"producto_id": 999, "cantidad": 1, "precio_unitario": 8000}],
        "comision_pagada": False,
    })
    assert respuesta.status_code == 400
    assert "no encontrado" in respuesta.json()["detail"]


def test_varias_rendiciones_seguidas_mismo_chofer(client):
    # sin cuenta previa: el chofer puede rendir varias veces (una por dia)
    ids = cargar_stock(client, {"5kg": 10})
    for _ in range(2):
        respuesta = client.post(f"/rendiciones/chofer/{CHOFER}", json={
            "ventas": [{"producto_id": ids["5kg"], "cantidad": 2, "precio_unitario": 8000}],
            "comision_pagada": False,
        })
        assert respuesta.status_code == 200, respuesta.text

    assert client.get(f"/rendiciones/chofer/{CHOFER}").json()["total"] == 2
    productos = {p["formato"]: p for p in client.get("/productos/").json()}
    assert productos["5kg"]["stock_actual"] == 6


def test_historial_por_chofer_paginado_de_10(client):
    ids = cargar_stock(client, {"5kg": 100})
    for _ in range(12):
        respuesta = client.post(f"/rendiciones/chofer/{CHOFER}", json={
            "ventas": [{"producto_id": ids["5kg"], "cantidad": 1, "precio_unitario": 8000}],
            "comision_pagada": False,
        })
        assert respuesta.status_code == 200

    pagina1 = client.get(f"/rendiciones/chofer/{CHOFER}?page=1").json()
    assert pagina1["total"] == 12
    assert pagina1["page_size"] == 10
    assert pagina1["total_pages"] == 2
    assert len(pagina1["items"]) == 10

    pagina2 = client.get(f"/rendiciones/chofer/{CHOFER}?page=2").json()
    assert len(pagina2["items"]) == 2

    # el listado general tambien pagina
    todas = client.get("/rendiciones/?page=1").json()
    assert todas["total"] == 12
    assert len(todas["items"]) == 10


def test_pdf_rendicion(client):
    ids = cargar_stock(client, STOCK_INICIAL)
    rendicion = rendicion_completa(client, ids).json()

    respuesta = client.get(f"/rendiciones/{rendicion['id']}/pdf")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content.startswith(b"%PDF")
    assert "rendicion_" in respuesta.headers["content-disposition"]


def test_pdf_rendicion_inexistente(client):
    assert client.get("/rendiciones/999/pdf").status_code == 404
