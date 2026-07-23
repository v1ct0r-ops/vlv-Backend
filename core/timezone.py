"""Manejo central de zona horaria.

Regla del proyecto:
- En la BD SIEMPRE se guarda UTC (aware). Neon/Docker corren en UTC.
- Al responder por la API se convierte a hora de Chile (America/Santiago),
  que maneja solo el cambio verano/invierno (UTC-3 / UTC-4).

Nota Windows: zoneinfo necesita el paquete `tzdata` (Windows no trae la base
de zonas). En Docker/Linux ya viene incluida.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CHILE_TZ = ZoneInfo("America/Santiago")


def ahora_utc() -> datetime:
    """Instante actual en UTC (aware). Usar como default de columnas fecha."""
    return datetime.now(timezone.utc)


def a_chile_naive(dt: datetime | None) -> datetime | None:
    """Convierte un datetime a hora de Chile y lo devuelve SIN tzinfo.

    Así la API responde con la misma estructura de siempre (sin sufijo de
    offset), solo con la hora ya corregida al huso de Chile.

    Filas históricas guardadas naive se asumen UTC (era el bug original).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CHILE_TZ).replace(tzinfo=None)
