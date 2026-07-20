import os

# Config de tests: debe setearse ANTES de importar la app, porque config.py
# instancia Settings() en el import y SECRET_KEY es obligatoria.
os.environ["DATABASE_URL"] = "sqlite:///./test_gas.db"   # BD de tests: sqlite local
os.environ["SECRET_KEY"] = "test-secret-no-usar-en-produccion"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["SEED_ADMIN_EMAIL"] = "admin@test.cl"
os.environ["SEED_ADMIN_PASSWORD"] = "test-password-123"

import pytest
from fastapi.testclient import TestClient

from core.database import Base, engine, SessionLocal
from core.seed import seed_productos, seed_empresa_admin
from main import app

def _reset_rate_limiter():
    """El limiter de /token cuenta por IP; TestClient siempre pega desde la
    misma IP simulada, así que sin resetear, tests que llaman /token varias
    veces gatillarían 429 entre sí."""
    app.state.limiter.reset()

ADMIN_EMAIL = os.environ["SEED_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["SEED_ADMIN_PASSWORD"]


def _autenticar(client: TestClient) -> str:
    """Hace login con el admin sembrado y devuelve el access token."""
    respuesta = client.post(
        "/token",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]


@pytest.fixture()
def client():
    """Cliente AUTENTICADO con BD limpia, 5 formatos + empresa/admin sembrados.

    Todas las rutas de negocio exigen token; este fixture pone el header
    Authorization por defecto, así los tests existentes no cambian."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        empresa = seed_empresa_admin(db)   # tenant primero
        seed_productos(db, empresa.id)     # productos del tenant

    _reset_rate_limiter()
    c = TestClient(app)
    token = _autenticar(c)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture()
def client_sin_auth():
    """Cliente SIN token, para verificar que las rutas protegidas rechazan (401)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        empresa = seed_empresa_admin(db)
        seed_productos(db, empresa.id)
    _reset_rate_limiter()
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
