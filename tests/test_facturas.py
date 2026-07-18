from tests.conftest import id_por_formato


def test_ingreso_factura_incrementa_stock(client):
    ids = id_por_formato(client)
    respuesta = client.post("/inventario/facturas", json={
        "numero_factura": "F-001",
        "proveedor": "Abastible",
        "observaciones": "carga semanal",
        "items": [
            {"producto_id": ids["5kg"], "cantidad": 50, "costo_unitario": 5000},
            {"producto_id": ids["gruas"], "cantidad": 15, "costo_unitario": 15000},
        ],
    })
    assert respuesta.status_code == 200, respuesta.text
    factura = respuesta.json()

    assert factura["numero_factura"] == "F-001"
    assert factura["total_unidades"] == 65
    # kilos: 50*5 + 15*15 (gruas = 15kg c/u)
    assert factura["total_kg"] == 50 * 5 + 15 * 15
    assert factura["total_costo"] == 50 * 5000 + 15 * 15000

    productos = {p["formato"]: p for p in client.get("/productos/").json()}
    assert productos["5kg"]["stock_actual"] == 50
    assert productos["gruas"]["stock_actual"] == 15


def test_ingreso_factura_deja_movimientos(client):
    ids = id_por_formato(client)
    client.post("/inventario/facturas", json={
        "numero_factura": "F-002",
        "proveedor": "Abastible",
        "items": [{"producto_id": ids["11kg"], "cantidad": 20}],
    })
    movimientos = client.get("/movimientos/").json()
    assert movimientos["total"] == 1
    assert movimientos["items"][0]["tipo"] == "INGRESO_FACTURA"
    assert movimientos["items"][0]["cantidad"] == 20


def test_ingreso_con_producto_inexistente_no_ingresa_nada(client):
    ids = id_por_formato(client)
    respuesta = client.post("/inventario/facturas", json={
        "numero_factura": "F-003",
        "proveedor": "Abastible",
        "items": [
            {"producto_id": ids["5kg"], "cantidad": 10},
            {"producto_id": 9999, "cantidad": 5},
        ],
    })
    assert respuesta.status_code == 400
    # rollback total: el primer item tampoco se ingreso
    productos = {p["formato"]: p for p in client.get("/productos/").json()}
    assert productos["5kg"]["stock_actual"] == 0
    assert client.get("/inventario/facturas").json()["total"] == 0


def test_stock_resultante_es_snapshot_del_ingreso(client):
    ids = id_por_formato(client)
    factura_a = client.post("/inventario/facturas", json={
        "numero_factura": "F-A",
        "proveedor": "Abastible",
        "items": [{"producto_id": ids["5kg"], "cantidad": 10}],
    }).json()
    assert factura_a["items"][0]["stock_resultante"] == 10

    # un ingreso posterior sube el stock, pero la factura anterior mantiene su snapshot
    client.post("/inventario/facturas", json={
        "numero_factura": "F-B",
        "proveedor": "Abastible",
        "items": [{"producto_id": ids["5kg"], "cantidad": 5}],
    })
    factura_a = client.get(f"/inventario/facturas/{factura_a['id']}").json()
    assert factura_a["items"][0]["stock_resultante"] == 10


def test_listado_facturas_paginado_de_10(client):
    ids = id_por_formato(client)
    for i in range(12):
        client.post("/inventario/facturas", json={
            "numero_factura": f"F-{i:03}",
            "proveedor": "Abastible",
            "items": [{"producto_id": ids["5kg"], "cantidad": 1}],
        })

    pagina1 = client.get("/inventario/facturas?page=1").json()
    assert pagina1["total"] == 12
    assert pagina1["page_size"] == 10
    assert pagina1["total_pages"] == 2
    assert len(pagina1["items"]) == 10

    pagina2 = client.get("/inventario/facturas?page=2").json()
    assert len(pagina2["items"]) == 2


def test_pdf_factura(client):
    ids = id_por_formato(client)
    factura = client.post("/inventario/facturas", json={
        "numero_factura": "F-PDF",
        "proveedor": "Abastible",
        "items": [{"producto_id": ids["45kg"], "cantidad": 8, "costo_unitario": 40000}],
    }).json()

    respuesta = client.get(f"/inventario/facturas/{factura['id']}/pdf")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content.startswith(b"%PDF")


def test_pdf_factura_inexistente(client):
    assert client.get("/inventario/facturas/999/pdf").status_code == 404
