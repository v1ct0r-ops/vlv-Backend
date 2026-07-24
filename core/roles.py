"""Catálogo canónico de roles del sistema.

Centralizar los roles en un solo lugar evita "strings mágicos" dispersos
("admin", "chofer") por routers y schemas: si mañana entra un rol nuevo, se
agrega aquí y todo el resto (validación de alta, dependencias de permiso) lo
hereda sin cazar cadenas por el código.
"""


class Rol:
    """Roles válidos. Usar Rol.ADMIN en vez del literal "admin"."""
    ADMIN = "admin"        # gestión total: usuarios, precios, inventario
    OPERADOR = "operador"  # operación diaria sin tocar precios
    CHOFER = "chofer"      # solo consulta precios y registra rendiciones


# Conjunto usado por el schema para rechazar roles inexistentes en el alta.
ROLES_VALIDOS = frozenset({Rol.ADMIN, Rol.OPERADOR, Rol.CHOFER})
