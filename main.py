from fastapi import FastAPI
from core.database import Base, engine, SessionLocal
from core.seed import seed_productos
from fastapi.middleware.cors import  CORSMiddleware
from config import settings
import models.producto
import models.movimiento
import models.ingreso_factura
import models.rendicion
from routers import productos, movimientos, inventario, rendiciones

# Configuración
app = FastAPI(title="Inventario de gas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),  # orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT, DELETE...
    allow_headers=["*"],
)

# Crear tablas (automático)
Base.metadata.create_all(bind=engine)

# Sembrar los 5 formatos de gas si no existen (idempotente)
with SessionLocal() as db:
    seed_productos(db)

# Incluir routers
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
