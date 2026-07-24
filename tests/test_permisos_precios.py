"""Tests de permisos por rol sobre productos/precios y roles extendidos (chofer).

Cubre la feature 'modulo-chofer-precios':
- Solo admin modifica productos/precios (POST/PUT/DELETE -> 403 para el resto).
- operador y chofer SÍ pueden consultar precios (GET) y usar rutas de chofer.
- El alta valida el rol (rechaza roles inexistentes).
- El rol viaja en el JWT y /me lo expone (frontend diferencia admin/chofer).
"""
from fastapi.testclient import TestClient

import main


def _crear_y_loguear(client, email: str, rol: str) -> TestClient:
    """El admin (fixture `client`) crea un usuario con `rol` y devuelve un
    TestClient nuevo autenticado como ESE usuario (mismo app/DB, otro token).

    Reutiliza el flujo real: alta por /usuarios/ (solo admin) + login /token.
    """
    password = "clave-rol-123456"
    r = client.post("/usuarios/", json={
        "email": email,
        "nombre": "Usuario Rol",
        "rol": rol,
        "password": password,
    })
    assert r.status_code == 201, r.text

    otro = TestClient(main.app)
    tok = otro.post(
        "/token",
        data={"username": email, "password": password},
    ).json()["access_token"]
    otro.headers.update({"Authorization": f"Bearer {tok}"})
    return otro


# --- Tarea 1: solo admin modifica productos/precios ---

def test_operador_no_puede_editar_precio(client):
    producto_id = client.get("/productos/").json()[0]["id"]
    op = _crear_y_loguear(client, "operador@test.cl", "operador")

    r = op.put(f"/productos/{producto_id}", json={"precio_venta": 12345})
    assert r.status_code == 403, r.text
    # el precio NO cambió
    assert client.get(f"/productos/{producto_id}").json()["precio_venta"] != 12345


def test_chofer_no_puede_editar_precio(client):
    producto_id = client.get("/productos/").json()[0]["id"]
    chofer = _crear_y_loguear(client, "chofer@test.cl", "chofer")

    r = chofer.put(f"/productos/{producto_id}", json={"precio_venta": 99999})
    assert r.status_code == 403, r.text


def test_operador_no_puede_crear_producto(client):
    op = _crear_y_loguear(client, "operador@test.cl", "operador")
    # body válido: el 403 debe venir del permiso, no de validación
    r = op.post("/productos/", json={
        "nombre": "Gas X",
        "formato": "11kg",
        "precio_venta": 15000,
    })
    assert r.status_code == 403, r.text


def test_chofer_no_puede_eliminar_producto(client):
    producto_id = client.get("/productos/").json()[0]["id"]
    chofer = _crear_y_loguear(client, "chofer@test.cl", "chofer")

    r = chofer.delete(f"/productos/{producto_id}")
    assert r.status_code == 403, r.text


def test_admin_si_puede_editar_precio(client):
    """Regresión: el admin conserva el acceso tras endurecer los permisos."""
    producto_id = client.get("/productos/").json()[0]["id"]
    r = client.put(f"/productos/{producto_id}", json={"precio_venta": 13500})
    assert r.status_code == 200, r.text
    assert r.json()["precio_venta"] == 13500


# --- Tarea 3: chofer/operador consultan precios y usan rutas de chofer ---

def test_operador_puede_consultar_precios(client):
    op = _crear_y_loguear(client, "operador@test.cl", "operador")
    r = op.get("/productos/")
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_chofer_puede_consultar_precios(client):
    chofer = _crear_y_loguear(client, "chofer@test.cl", "chofer")
    r = chofer.get("/productos/")
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_chofer_accede_a_rutas_de_rendiciones(client):
    """El chofer no recibe 403 en su propia ruta (listado de rendiciones)."""
    chofer = _crear_y_loguear(client, "chofer@test.cl", "chofer")
    r = chofer.get("/rendiciones/")
    assert r.status_code == 200, r.text


# --- Tarea 2: rol en el alta y en el token/me ---

def test_alta_rechaza_rol_invalido(client):
    r = client.post("/usuarios/", json={
        "email": "raro@test.cl",
        "nombre": "Rol Raro",
        "rol": "superadmin",
        "password": "clave-rol-123456",
    })
    assert r.status_code == 422, r.text


def test_me_expone_rol_chofer(client):
    """El JWT lleva el rol y /me lo devuelve: el frontend distingue chofer."""
    chofer = _crear_y_loguear(client, "chofer@test.cl", "chofer")
    r = chofer.get("/me")
    assert r.status_code == 200, r.text
    assert r.json()["rol"] == "chofer"


# --- Cálculo de precio: compra + ganancia = venta, con override manual ---

def test_precio_venta_se_calcula_compra_mas_ganancia(client):
    """Si el admin manda compra y ganancia sin precio_venta, se calcula."""
    producto_id = client.get("/productos/").json()[0]["id"]
    r = client.put(f"/productos/{producto_id}", json={
        "precio_compra": 8000,
        "ganancia": 2000,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["precio_compra"] == 8000
    assert body["ganancia"] == 2000
    assert body["precio_venta"] == 10000  # 8000 + 2000


def test_precio_venta_se_recalcula_al_cambiar_solo_ganancia(client):
    """Cambiar solo la ganancia recalcula sobre el precio_compra ya guardado."""
    producto_id = client.get("/productos/").json()[0]["id"]
    client.put(f"/productos/{producto_id}", json={"precio_compra": 5000, "ganancia": 1000})
    r = client.put(f"/productos/{producto_id}", json={"ganancia": 3000})
    assert r.status_code == 200, r.text
    assert r.json()["precio_venta"] == 8000  # 5000 + 3000


def test_precio_venta_manual_sobrescribe_calculo(client):
    """Si el admin fija precio_venta explícito, gana sobre compra+ganancia."""
    producto_id = client.get("/productos/").json()[0]["id"]
    r = client.put(f"/productos/{producto_id}", json={
        "precio_compra": 8000,
        "ganancia": 2000,
        "precio_venta": 15000,  # override manual
    })
    assert r.status_code == 200, r.text
    assert r.json()["precio_venta"] == 15000


# --- El chofer ve solo formato + precio_venta, nunca costo ni margen ---

def test_chofer_no_ve_precio_compra_ni_ganancia(client):
    # admin fija estructura de precio
    producto_id = client.get("/productos/").json()[0]["id"]
    client.put(f"/productos/{producto_id}", json={"precio_compra": 8000, "ganancia": 2000})

    chofer = _crear_y_loguear(client, "chofer@test.cl", "chofer")
    producto = chofer.get("/productos/").json()[0]

    assert "precio_venta" in producto
    assert "formato" in producto
    # costos internos ocultos
    assert "precio_compra" not in producto
    assert "ganancia" not in producto
    assert "comision_unitaria" not in producto


def test_admin_si_ve_precio_compra_y_ganancia(client):
    """Regresión: admin conserva la vista completa."""
    producto = client.get("/productos/").json()[0]
    assert "precio_compra" in producto
    assert "ganancia" in producto
    assert "precio_venta" in producto
