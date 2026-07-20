from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from core.database import Base, engine, SessionLocal
from core.seed import seed_productos, seed_empresa_admin
from core.migrate import migrate_add_empresa_id
from core.limiter import limiter
from fastapi.middleware.cors import  CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from config import settings
import models.producto
import models.movimiento
import models.ingreso_factura
import models.rendicion
import models.empresa
import models.usuario
from routers import productos, movimientos, inventario, rendiciones, auth, usuarios

# Configuración
app = FastAPI(title="Inventario de gas")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),  # orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT, DELETE...
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def excepcion_no_manejada(request: Request, exc: Exception):
    """Red de seguridad: si algo revienta sin ser un HTTPException, no se
    filtra traceback ni detalle interno al cliente cuando DEBUG=False."""
    if settings.DEBUG:
        raise exc
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})

# Crear tablas (automático)
Base.metadata.create_all(bind=engine)

# Orden importante:
# 1) empresa/admin inicial (crea el tenant 1)
# 2) migrar: agrega empresa_id a tablas viejas y hace backfill al tenant 1
# 3) recién ahora sembrar productos (necesitan empresa_id)
with SessionLocal() as db:
    empresa = seed_empresa_admin(db)
    migrate_add_empresa_id(db, empresa.id)
    seed_productos(db, empresa.id)

# Incluir routers
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(productos.router)
app.include_router(movimientos.router)
app.include_router(inventario.router)
app.include_router(rendiciones.router)

@app.get("/", tags=["Home"])
def home():
    return {
        "mensaje": "API de inventario de gas funcionando",
        "estado": "Activo",
        "version": "1.0.0"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
