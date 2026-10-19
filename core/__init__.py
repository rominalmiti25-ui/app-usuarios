from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .models import Rol
from .database import Database
from .repository import ProductoRepository, UsuarioRepository
from .semilla import PRODUCTOS_SEMILLA
from .services import ServicioAutenticacion, ServicioProductos, ServicioUsuarios
from .routes import registrar_rutas


def create_app() -> Flask:
    """Fábrica de la aplicación: arma las dependencias (POO) y registra las rutas."""
    app = Flask(__name__, template_folder="../templates")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # HTTPS detrás de Vercel
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    config = Config()
    base_datos = Database(config)
    repositorio = UsuarioRepository(base_datos)
    repositorio_productos = ProductoRepository(base_datos)
    auth = ServicioAutenticacion(config, repositorio)
    usuarios = ServicioUsuarios(repositorio, auth)
    productos = ServicioProductos(repositorio_productos)

    try:
        base_datos.inicializar_esquema()
        # Como el registro es solo para administradores, la primera cuenta sale del entorno
        if config.ADMIN_USUARIO and config.ADMIN_PASSWORD and repositorio.contar() == 0:
            usuarios.registrar(config.ADMIN_USUARIO, config.ADMIN_PASSWORD, Rol.ADMINISTRADOR)
            app.logger.info("Administrador inicial creado: %s", config.ADMIN_USUARIO)
    except Exception as error:  # la app arranca aunque la BD tarde en responder
        app.logger.error("No se pudo inicializar la base de datos: %s", error)

    try:
        # Catálogo inicial: solo se carga si la tabla productos está vacía
        if repositorio_productos.contar() == 0:
            for item in PRODUCTOS_SEMILLA:
                repositorio_productos.crear(**item)
            app.logger.info("Catálogo inicial creado: %d productos", len(PRODUCTOS_SEMILLA))
    except Exception as error:
        app.logger.error("No se pudo cargar el catálogo inicial: %s", error)

    registrar_rutas(app, auth, usuarios, productos)
    return app
