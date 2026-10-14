import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # en Vercel las variables ya vienen del entorno
    pass


class Config:
    """Lee toda la configuración desde variables de entorno."""

    def __init__(self) -> None:
        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-cambia-esta-clave")
        self.DB_HOST = os.getenv("DB_HOST", "localhost")
        self.DB_PORT = int(os.getenv("DB_PORT", "3306"))
        self.DB_USER = os.getenv("DB_USER", "root")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "")
        self.DB_NAME = os.getenv("DB_NAME", "usuarios_app")
        self.DB_SSL = os.getenv("DB_SSL", "true").lower() == "true"
        self.DB_SSL_CA = os.getenv("DB_SSL_CA") or None
        self.TOKEN_HORAS = int(os.getenv("TOKEN_HORAS", "8"))
        # Administrador inicial: solo se crea si la tabla usuarios está vacía
        self.ADMIN_USUARIO = os.getenv("ADMIN_USUARIO") or None
        self.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or None
