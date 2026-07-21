"""Tests de gestión de usuarios: alta por admin, permisos y tenant scoping."""
from fastapi.testclient import TestClient

import main

OPERADOR = {
    "email": "operador@test.cl",
    "nombre": "Operador Uno",
    "rol": "operador",
    "password": "clave-operador-123",
}


def test_admin_crea_usuario(client):
    r = client.post("/usuarios/", json=OPERADOR)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == OPERADOR["email"]
    assert body["empresa_id"] == 1
    # El hash y la password jamás salen en la respuesta.
    assert "password" not in body
    assert "hashed_password" not in body


def test_usuario_creado_puede_loguear(client):
    client.post("/usuarios/", json=OPERADOR)
    r = client.post(
        "/token",
        data={"username": OPERADOR["email"], "password": OPERADOR["password"]},
    )
    assert r.status_code == 200


def test_email_duplicado_en_empresa_409(client):
    client.post("/usuarios/", json=OPERADOR)
    r = client.post("/usuarios/", json=OPERADOR)
    assert r.status_code == 409


def test_operador_no_puede_crear_usuarios(client):
    # admin crea un operador
    client.post("/usuarios/", json=OPERADOR)

    # cliente autenticado como ese operador (mismo app/DB, otro token)
    oc = TestClient(main.app)
    tok = oc.post(
        "/token",
        data={"username": OPERADOR["email"], "password": OPERADOR["password"]},
    ).json()["access_token"]
    oc.headers.update({"Authorization": f"Bearer {tok}"})

    r = oc.post("/usuarios/", json={
        "email": "otro@test.cl",
        "nombre": "Otro",
        "password": "otra-clave-123",
    })
    assert r.status_code == 403  # rol operador no autorizado


def test_listar_usuarios_de_la_empresa(client):
    client.post("/usuarios/", json=OPERADOR)
    r = client.get("/usuarios/")
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert emails == {"admin@test.cl", OPERADOR["email"]}
    # todos del mismo tenant
    assert all(u["empresa_id"] == 1 for u in r.json())
