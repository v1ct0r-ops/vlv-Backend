"""Tests de autenticación: login, protección de rutas y /me."""
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def test_login_ok(client_sin_auth):
    r = client_sin_auth.post(
        "/token",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_password_incorrecta(client_sin_auth):
    r = client_sin_auth.post(
        "/token",
        data={"username": ADMIN_EMAIL, "password": "clave-mala"},
    )
    assert r.status_code == 401


def test_login_usuario_inexistente(client_sin_auth):
    # Mismo 401 que password mala: no revela si el email existe.
    r = client_sin_auth.post(
        "/token",
        data={"username": "nadie@test.cl", "password": "x"},
    )
    assert r.status_code == 401


def test_ruta_protegida_sin_token(client_sin_auth):
    assert client_sin_auth.get("/productos/").status_code == 401
    assert client_sin_auth.get("/inventario/facturas").status_code == 401
    assert client_sin_auth.get("/movimientos/").status_code == 401
    assert client_sin_auth.get("/rendiciones/").status_code == 401


def test_ruta_protegida_token_invalido(client_sin_auth):
    h = {"Authorization": "Bearer token.falso.xxx"}
    assert client_sin_auth.get("/productos/", headers=h).status_code == 401


def test_ruta_protegida_con_token(client):
    # client ya trae el header Authorization por defecto.
    assert client.get("/productos/").status_code == 200


def test_me_devuelve_usuario_actual(client):
    r = client.get("/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["rol"] == "admin"
    assert body["empresa_id"] == 1


def test_rate_limit_en_login(client_sin_auth):
    """Al 6to intento en el mismo minuto, /token debe cortar con 429."""
    for _ in range(5):
        r = client_sin_auth.post(
            "/token",
            data={"username": ADMIN_EMAIL, "password": "clave-mala"},
        )
        assert r.status_code == 401

    r = client_sin_auth.post(
        "/token",
        data={"username": ADMIN_EMAIL, "password": "clave-mala"},
    )
    assert r.status_code == 429
