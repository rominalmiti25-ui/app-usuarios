from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .models import Rol
from .database import Database
from .repository import UsuarioRepository
from .services import ServicioAutenticacion, ServicioUsuarios
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
    auth = ServicioAutenticacion(config, repositorio)
    usuarios = ServicioUsuarios(repositorio, auth)

    try:
        base_datos.inicializar_esquema()
        # Como el registro es solo para administradores, la primera cuenta sale del entorno
        if config.ADMIN_USUARIO and config.ADMIN_PASSWORD and repositorio.contar() == 0:
            usuarios.registrar(config.ADMIN_USUARIO, config.ADMIN_PASSWORD, Rol.ADMINISTRADOR)
            app.logger.info("Administrador inicial creado: %s", config.ADMIN_USUARIO)
    except Exception as error:  # la app arranca aunque la BD tarde en responder
        app.logger.error("No se pudo inicializar la base de datos: %s", error)

    registrar_rutas(app, auth, usuarios)
    return app
