import os

# la BD de tests es sqlite local; debe setearse ANTES de importar la app
os.environ["DATABASE_URL"] = "sqlite:///./test_gas.db"

import pytest
from fastapi.testclient import TestClient

from core.database import Base, engine, SessionLocal
from core.seed import seed_productos
from main import app


@pytest.fixture()
def client():
    """Cliente con base de datos limpia y los 5 formatos sembrados"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_productos(db)
    return TestClient(app)


def id_por_formato(client):
    """Mapa formato -> producto_id segun el seed"""
    productos = client.get("/productos/").json()
    return {p["formato"]: p["id"] for p in productos}


def cargar_stock(client, cantidades: dict):
    """Ingresa stock por factura para los formatos indicados {formato: cantidad}"""
    ids = id_por_formato(client)
    respuesta = client.post("/inventario/facturas", json={
        "numero_factura": "F-TEST",
        "proveedor": "Proveedor Test",
        "items": [
            {"producto_id": ids[formato], "cantidad": cantidad}
            for formato, cantidad in cantidades.items()
        ],
    })
    assert respuesta.status_code == 200, respuesta.text
    return ids
