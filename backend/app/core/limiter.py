from slowapi import Limiter
from slowapi.util import get_remote_address

# Límites estrictos por endpoint (login, portal…). El tope general por IP de toda la API está en core/ip_limit.py.
limiter = Limiter(key_func=get_remote_address)
