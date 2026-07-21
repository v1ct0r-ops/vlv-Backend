from pydantic import BaseModel
from typing import Generic, List, TypeVar

PAGE_SIZE = 10 # tamaño fijo de pagina para no sobrecargar la base de datos

T = TypeVar("T")

class Pagina(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def paginar(query, page: int):
    """Aplica paginacion de 10 a cualquier query y arma la respuesta"""
    total = query.count()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    items = query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "total_pages": total_pages,
    }
