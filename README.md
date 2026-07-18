# VLV Backend — API de Inventario de Gas

API REST construida con **FastAPI** para gestionar el inventario de una distribuidora de gas licuado (GLP): ingreso de stock por factura, rendiciones diarias de choferes y trazabilidad de movimientos.

## Stack

- **FastAPI** + **Uvicorn**
- **SQLAlchemy** — Postgres en producción/Docker, SQLite en tests
- **Pydantic v2** / `pydantic-settings` para configuración y validación
- **ReportLab** para generación de PDFs (facturas y rendiciones)
- **Pytest** + **httpx** para tests
- **Docker Compose** (API + Postgres + Adminer)

## Estructura del proyecto

```
main.py                # Punto de entrada FastAPI, CORS, seed, routers
config.py              # Settings (pydantic-settings) leídas desde .env
core/
  database.py           # Engine, SessionLocal, Base, get_db
  seed.py                # Seed idempotente de los 5 formatos de gas
models/                # Modelos SQLAlchemy (Producto, Movimiento, IngresoFactura, Rendicion)
schemas/               # Schemas Pydantic (request/response) + paginación genérica
routers/               # Endpoints: productos, movimientos, inventario, rendiciones
services/              # Lógica de negocio: facturas, rendiciones, PDFs
tests/                 # Suite pytest (fixtures con SQLite en memoria)
```

## Requisitos

- Docker y Docker Compose (recomendado), **o** Python 3.11+ y un Postgres local
- Copiar `.env.example` a `.env` y ajustar credenciales si es necesario

## Levantar con Docker (recomendado)

```powershell
docker-compose up -d
```

- **API Docs (Swagger)**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc
- **Health Check**: http://localhost:5000/health
- **Admin BD (Adminer)**: http://localhost:8080

### Comandos rápidos

```powershell
docker-compose up -d              # Levantar todo
docker-compose ps                 # Ver estado
docker-compose logs -f api        # Ver logs en tiempo real
```

```powershell
docker-compose stop               # Pausar (datos seguros)
docker-compose start              # Reanudar
docker-compose restart api        # Reiniciar API
docker-compose down               # Detener (datos seguros)
docker-compose down -v            # Detener y borrar datos ⚠️
```

```powershell
docker-compose logs api           # Últimos logs
docker-compose logs -f db         # Logs PostgreSQL
docker-compose exec api bash      # Terminal en API
docker-compose exec db psql -U gas_user -d gas_db  # PostgreSQL CLI
```

### Credenciales BD (docker-compose)

```
Servidor: db (o localhost:5434 desde el host)
Usuario:  gas_user
Contraseña: gas_password_secreta
BD: gas_db
```

## Levantar en local sin Docker

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# editar .env con tu DATABASE_URL local

uvicorn main:app --reload --port 5000
```

## Tests

```powershell
venv\Scripts\python -m pytest tests/ -q
```

Los tests usan una base SQLite propia (`test_gas.db`, se limpia en cada test) y no requieren Docker ni Postgres levantados.

## Módulos de negocio

El inventario trabaja **solo con los 5 formatos de gas**: `5kg`, `11kg`, `15kg`, `45kg` y `gruas` (una grúa pesa **15 kg**). Al arrancar la API se crean automáticamente (seed idempotente) con sus kilos y comisión por unidad:

| Formato | Kg/unidad | Comisión chofer |
|---------|-----------|-----------------|
| 5kg | 5 | $1.500 |
| 11kg | 11 | $1.500 |
| 15kg | 15 | $1.600 |
| 45kg | 45 | $3.500 |
| gruas | 15 | $1.500 |

### Endpoints

**Productos** (`/productos`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/productos/` | Crea un producto (uno por formato, máximo 5) |
| GET | `/productos/` | Lista todos los productos |
| GET | `/productos/{id}` | Detalle de un producto |
| PUT | `/productos/{id}` | Actualiza nombre/precio/stock/comisión (el formato no se puede cambiar) |
| DELETE | `/productos/{id}` | Elimina un producto (rechaza si tiene movimientos asociados) |

**Movimientos** (`/movimientos`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/movimientos/` | Registra una venta directa (descuenta stock) |
| GET | `/movimientos?page=1` | Listado paginado (10), más recientes primero |

**Inventario** (`/inventario`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/inventario/facturas` | Ingreso de stock por factura (grupo de formatos, sube stock) |
| GET | `/inventario/facturas?page=1` | Listado paginado (10) |
| GET | `/inventario/facturas/{id}` | Detalle de una factura |
| GET | `/inventario/facturas/{id}/pdf` | PDF de respaldo del ingreso |

**Rendiciones** (`/rendiciones`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/rendiciones/chofer/{nombre}` | Rendición completa del día: ventas por formato, tarjetas (lista), descuentos (lista), bencina, comisión, efectivo a rendir |
| GET | `/rendiciones?page=1` | Todas las rendiciones, paginado (10) |
| GET | `/rendiciones/chofer/{nombre}?page=1` | Historial por chofer (seguimiento de ventas), paginado (10) |
| GET | `/rendiciones/chofer/{nombre}/cerradas` | Detalle completo sin paginar; filtro opcional `mes`/`anio` |
| GET | `/rendiciones/{id}` | Detalle de una rendición |
| GET | `/rendiciones/{id}/pdf` | PDF con el detalle completo de la rendición |

### Reglas de negocio

- El stock **nunca puede quedar negativo**: si la rendición declara más vendido que el stock disponible, se rechaza completa (HTTP 400) y no se guarda nada.
- La rendición es un **documento independiente por día/chofer**: no requiere ningún paso previo (la antigua "cuenta del chofer" fue eliminada).
- `comision_pagada: true` descuenta la comisión del efectivo a rendir; `false` la deja registrada como retenida.
- `efectivo_a_rendir = total_ventas - tarjetas - bencina - descuentos - (comisión si fue pagada)`.
- Los PDFs se generan en el **backend** (ReportLab); el frontend solo descarga desde los endpoints `.../pdf`.

### Cambios de esquema (sin Alembic)

`create_all` no altera tablas existentes. Si el esquema cambió, recrear la BD de desarrollo:

```powershell
docker-compose down -v && docker-compose up -d --build
```
