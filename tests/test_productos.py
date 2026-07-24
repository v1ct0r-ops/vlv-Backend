from core.database import SessionLocal
from core.seed import seed_productos


def test_seed_crea_los_5_formatos(client):
    productos = client.get("/productos/").json()
    assert len(productos) == 5

    por_formato = {p["formato"]: p for p in productos}
    assert set(por_formato) == {"5kg", "11kg", "15kg", "45kg", "gruas"}

    # kilos por unidad (ojo: gruas pesa 15kg)
    assert por_formato["5kg"]["kg_por_unidad"] == 5
    assert por_formato["11kg"]["kg_por_unidad"] == 11
    assert por_formato["15kg"]["kg_por_unidad"] == 15
    assert por_formato["45kg"]["kg_por_unidad"] == 45
    assert por_formato["gruas"]["kg_por_unidad"] == 15

    # comisiones actuales del chofer
    assert por_formato["5kg"]["comision_unitaria"] == 1500
    assert por_formato["11kg"]["comision_unitaria"] == 1500
    assert por_formato["15kg"]["comision_unitaria"] == 1600
    assert por_formato["45kg"]["comision_unitaria"] == 3500
    assert por_formato["gruas"]["comision_unitaria"] == 1500


def test_seed_es_idempotente(client):
    with SessionLocal() as db:
        seed_productos(db)
        seed_productos(db)
    assert len(client.get("/productos/").json()) == 5


def test_no_permite_formato_duplicado(client):
    respuesta = client.post("/productos/", json={
        "nombre": "Gas Duplicado",
        "formato": "5kg",
        "precio_venta": 9000,
    })
    assert respuesta.status_code == 409
    assert len(client.get("/productos/").json()) == 5


def test_no_permite_formato_fuera_de_los_5(client):
    respuesta = client.post("/productos/", json={
        "nombre": "Gas Raro",
        "formato": "33kg",
        "precio_venta": 9000,
    })
    assert respuesta.status_code == 422


def test_actualizar_precio_y_comision(client):
    producto = client.get("/productos/").json()[0]
    respuesta = client.put(f"/productos/{producto['id']}", json={
        "precio_venta": 9990,
        "comision_unitaria": 2000,
    })
    assert respuesta.status_code == 200
    actualizado = respuesta.json()
    assert actualizado["precio_venta"] == 9990
    assert actualizado["comision_unitaria"] == 2000
    # el formato no cambia
    assert actualizado["formato"] == producto["formato"]


def test_no_eliminar_producto_con_movimientos(client, ):
    from tests.conftest import cargar_stock
    ids = cargar_stock(client, {"5kg": 10})
    respuesta = client.delete(f"/productos/{ids['5kg']}")
    assert respuesta.status_code == 400
