from pydantic import BaseModel, EmailStr, Field


class UsuarioBase(BaseModel):
    """Campos comunes y seguros de exponer. Nunca incluye password ni hash."""
    email: EmailStr
    nombre: str = Field(min_length=3, max_length=120)
    rol: str = Field(default="operador")


class UsuarioCreate(UsuarioBase):
    # Contraseña en claro SOLO de entrada: llega en el request, se hashea en el
    # service y jamás se persiste ni se devuelve tal cual.
    password: str = Field(min_length=8, max_length=72)  # bcrypt trunca sobre 72 bytes
    # empresa_id la fija el backend (usuario autenticado que crea), no el cliente,
    # para que nadie cree usuarios en una empresa ajena. Por eso no va aquí.


class UsuarioRead(UsuarioBase):
    """Lo que devolvemos al cliente. Sin hashed_password: el hash nunca sale de la DB."""
    id: int
    activo: bool
    empresa_id: int

    class Config:
        from_attributes = True  # permite construir el schema desde el objeto ORM
