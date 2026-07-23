"""Migración idempotente: agrega empresa_id a las tablas de negocio existentes.

Por qué existe: Base.metadata.create_all() solo CREA tablas que faltan; nunca
ALTERa una tabla que ya existe. En una base con datos previos (tu postgres),
la columna empresa_id nueva no aparece sola. Esta función la agrega, rellena
(backfill) las filas viejas con la empresa inicial y fija la FK + NOT NULL.

Es idempotente: si la columna ya existe (base fresca creada por create_all, o
un segundo arranque), no hace nada.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

# Tablas raíz que llevan empresa_id. Las tablas hijas (detalles, ventas, ajustes)
# quedan aisladas por tenant a través de su FK al padre, no necesitan la columna.
TABLAS = ["productos", "movimientos_inventarios", "ingresos_factura", "rendiciones"]


def _tiene_columna(db: Session, tabla: str, columna: str) -> bool:
    dialecto = db.get_bind().dialect.name
    if dialecto == "sqlite":
        filas = db.execute(text(f"PRAGMA table_info({tabla})")).fetchall()
        return any(fila[1] == columna for fila in filas)
    # postgres (y compatibles): information_schema estándar
    q = text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    )
    return db.execute(q, {"t": tabla, "c": columna}).first() is not None


def migrate_add_empresa_id(db: Session, empresa_id: int) -> None:
    """Agrega empresa_id a las tablas que aún no la tienen y hace backfill al
    tenant dado. En bases frescas es no-op (la columna ya la creó create_all)."""
    dialecto = db.get_bind().dialect.name

    for tabla in TABLAS:
        if _tiene_columna(db, tabla, "empresa_id"):
            continue

        # 1) columna nullable para poder rellenar las filas existentes
        db.execute(text(f"ALTER TABLE {tabla} ADD COLUMN empresa_id INTEGER"))
        # 2) backfill: todo lo viejo pertenece a la empresa inicial
        db.execute(text(f"UPDATE {tabla} SET empresa_id = :eid"), {"eid": empresa_id})

        if dialecto == "postgresql":
            # 3) recién ahora NOT NULL (ya no hay filas con null) + FK
            db.execute(text(f"ALTER TABLE {tabla} ALTER COLUMN empresa_id SET NOT NULL"))
            db.execute(text(
                f"ALTER TABLE {tabla} ADD CONSTRAINT fk_{tabla}_empresa "
                f"FOREIGN KEY (empresa_id) REFERENCES empresas(id)"
            ))
        # sqlite no soporta ALTER para NOT NULL/FK, pero ahí las tablas se crean
        # frescas desde el modelo, así que esta rama casi nunca corre en sqlite.

        db.commit()
        print(f" Migración: empresa_id agregada a {tabla} (backfill empresa {empresa_id}).")

    _migrar_unique_producto_formato(db)
    _migrar_fechas_a_timestamptz(db)


# (tabla, columna) que guardan fechas y deben ser timestamptz (UTC en BD).
_COLUMNAS_FECHA = [
    ("movimientos_inventarios", "fecha"),
    ("rendiciones", "fecha"),
    ("ingresos_factura", "fecha"),
    ("usuarios", "creado_en"),
    ("empresas", "creado_en"),
]


def _migrar_fechas_a_timestamptz(db: Session) -> None:
    """Convierte las columnas de fecha de `timestamp` (naive) a `timestamptz`.

    Las filas viejas se guardaron con datetime.now() en un servidor UTC, o sea
    su hora naive YA es UTC. Por eso el USING reinterpreta el valor como UTC
    (`AT TIME ZONE 'UTC'`), sin desplazarlo. Idempotente: si la columna ya es
    timestamptz, no hace nada. Solo postgres (en sqlite no aplica el tipo)."""
    if db.get_bind().dialect.name != "postgresql":
        return

    for tabla, columna in _COLUMNAS_FECHA:
        q = text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        )
        fila = db.execute(q, {"t": tabla, "c": columna}).first()
        if fila is None or fila[0] == "timestamp with time zone":
            continue  # tabla nueva ya nace correcta, o no existe aún

        db.execute(text(
            f"ALTER TABLE {tabla} ALTER COLUMN {columna} "
            f"TYPE timestamptz USING {columna} AT TIME ZONE 'UTC'"
        ))
        db.commit()
        print(f" Migración: {tabla}.{columna} convertida a timestamptz (UTC).")


def _existe_constraint(db: Session, nombre: str) -> bool:
    q = text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = :n"
    )
    return db.execute(q, {"n": nombre}).first() is not None


def _migrar_unique_producto_formato(db: Session) -> None:
    """En postgres, cambia el UNIQUE global de productos.formato por uno
    compuesto (empresa_id, formato). Idempotente. No aplica en sqlite (ahí la
    tabla se crea fresca con el constraint correcto)."""
    if db.get_bind().dialect.name != "postgresql":
        return

    # nombre por defecto del UNIQUE de columna que crea postgres: <tabla>_<col>_key
    db.execute(text("ALTER TABLE productos DROP CONSTRAINT IF EXISTS productos_formato_key"))

    if not _existe_constraint(db, "uq_producto_empresa_formato"):
        db.execute(text(
            "ALTER TABLE productos ADD CONSTRAINT uq_producto_empresa_formato "
            "UNIQUE (empresa_id, formato)"
        ))
    db.commit()
