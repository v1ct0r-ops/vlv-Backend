"""Aislamiento multi-tenant: cada empresa solo ve y toca sus propios datos."""
from fastapi.testclient import TestClient

import main
from core.database import SessionLocal
from core.security import hash_password
from core.seed import seed_productos
from models.empresa import Empresa
from models.usuario import Usuario


def _crear_segunda_empresa():
    """Crea empresa 2 con sus 5 productos y un admin propio. Devuelve su id."""
    with SessionLocal() as db:
        emp2 = Empresa(nombre="Empresa Dos", rut="22222222-2", activo=True)
        db.add(emp2)
        db.commit()
        db.refresh(emp2)
        seed_productos(db, emp2.id)
        db.add(Usuario(
            email="admin2@test.cl",
            hashed_password=hash_password("clave-dos-123"),
            nombre="Admin Dos",
            rol="admin",
            empresa_id=emp2.id,
        ))
        db.commit()
        return emp2.id


def test_productos_aislados_por_empresa(client):
    emp2_id = _crear_segunda_empresa()

    # admin tenant 1: ve solo sus 5 productos, ninguno de la empresa 2
    r1 = client.get("/productos/")
    assert r1.status_code == 200
    p1 = r1.json()
    assert len(p1) == 5
    assert all(p["empresa_id"] == 1 for p in p1)

    # admin tenant 2: ve solo sus 5, con ids distintos
    oc = TestClient(main.app)
    tok = oc.post(
        "/token", data={"username": "admin2@test.cl", "password": "clave-dos-123"}
    ).json()["access_token"]
    oc.headers.update({"Authorization": f"Bearer {tok}"})

    r2 = oc.get("/productos/")
    p2 = r2.json()
    assert len(p2) == 5
    assert all(p["empresa_id"] == emp2_id for p in p2)

    # los conjuntos de ids no se solapan: son inventarios separados
    assert {p["id"] for p in p1}.isdisjoint({p["id"] for p in p2})


def test_no_puede_ver_producto_de_otra_empresa(client):
    _crear_segunda_empresa()

    # id de un producto de la empresa 2
    with SessionLocal() as db:
        from models.producto import Producto
        prod_emp2 = db.query(Producto).filter(Producto.empresa_id == 2).first()
        prod_emp2_id = prod_emp2.id

    # admin tenant 1 intenta leerlo -> 404 (no existe para su tenant)
    r = client.get(f"/productos/{prod_emp2_id}")
    assert r.status_code == 404
