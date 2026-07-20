"""Limiter compartido (slowapi). Vive en su propio módulo para que
main.py y los routers lo importen sin import circular."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
