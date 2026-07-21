from sqlalchemy.orm import Session
from models.producto import Producto
from models.empresa import Empresa
from models.usuario import Usuario
from schemas.producto import FormatoGas, KG_POR_FORMATO, COMISION_POR_FORMATO
from core.security import hash_password
from config import settings

# precios de venta por defecto, editables despues via PUT /productos/{id}
PRECIO_DEFAULT = {
    FormatoGas.GALON_5: 8000,
    FormatoGas.GALON_11: 17000,
    FormatoGas.GALON_15: 23000,
    FormatoGas.GALON_45: 68000,
    FormatoGas.GALON_GRUA: 23000,
}

def seed_productos(db: Session, empresa_id: int | None = None):
    """
    Crea los 5 formatos de gas si no existen (idempotente).
    El inventario completo se trabaja solo con estos 5 productos.

    empresa_id define a qué tenant pertenecen. Si no se pasa, usa la primera
    empresa (compatibilidad con llamadas directas de los tests).
    """
    if empresa_id is None:
        empresa = db.query(Empresa).first()
        empresa_id = empresa.id if empresa else None

    for formato in FormatoGas:
        existe = db.query(Producto).filter(
            Producto.formato == formato.value,
            Producto.empresa_id == empresa_id,
        ).first()
        if not existe:
            db.add(Producto(
                nombre="Gas GLP",
                formato=formato.value,
                precio_unitario=PRECIO_DEFAULT[formato],
                stock_actual=0,
                kg_por_unidad=KG_POR_FORMATO[formato],
                comision_unitaria=COMISION_POR_FORMATO[formato],
                empresa_id=empresa_id,
            ))
    db.commit()


def seed_empresa_admin(db: Session):
    """Crea la empresa (tenant) inicial y el usuario admin. Idempotente.

    La empresa se crea siempre (todo usuario necesita una). El admin solo se
    crea si SEED_ADMIN_EMAIL y SEED_ADMIN_PASSWORD están en el .env: así no
    dejamos una credencial por defecto conocida en producción.

    Devuelve la empresa inicial (útil para el alta manual de usuarios luego).
    """
    empresa = db.query(Empresa).first()
    if empresa is None:
        empresa = Empresa(nombre="Mi Empresa GLP", rut="11111111-1", activo=True)
        db.add(empresa)
        db.commit()
        db.refresh(empresa)

    email = settings.SEED_ADMIN_EMAIL
    password = settings.SEED_ADMIN_PASSWORD
    if email and password:
        existe = db.query(Usuario).filter(Usuario.email == email).first()
        if existe is None:
            db.add(Usuario(
                email=email,
                hashed_password=hash_password(password),
                nombre="Administrador",
                rol="admin",
                empresa_id=empresa.id,
            ))
            db.commit()
    else:
        print(" Sin SEED_ADMIN_EMAIL/PASSWORD en .env: no se creó admin automático.")

    return empresa
