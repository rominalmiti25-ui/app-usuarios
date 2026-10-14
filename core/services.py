import re
from datetime import datetime, timedelta, timezone

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from .config import Config
from .models import Rol, Usuario
from .repository import UsuarioDuplicado, UsuarioRepository


class ErrorValidacion(Exception):
    pass


class CredencialesInvalidas(Exception):
    pass


class ServicioAutenticacion:
    """Hash de contraseñas, inicio de sesión y manejo del token (JWT)."""

    def __init__(self, config: Config, repositorio: UsuarioRepository) -> None:
        self._config = config
        self._repo = repositorio

    def hashear(self, contrasena: str) -> str:
        return generate_password_hash(contrasena, method="pbkdf2:sha256")

    def iniciar_sesion(self, nombre: str, contrasena: str) -> tuple[Usuario, str]:
        usuario = self._repo.obtener_por_usuario((nombre or "").strip())
        if not usuario or not check_password_hash(usuario.hash_contrasena, contrasena or ""):
            raise CredencialesInvalidas()
        if usuario.rol not in Rol.TODOS:  # rol desconocido en la BD: se aplica el mínimo privilegio
            usuario.rol = Rol.CLIENTE
        return usuario, self._crear_token(usuario)

    def _crear_token(self, usuario: Usuario) -> str:
        ahora = datetime.now(timezone.utc)
        carga = {
            "sub": str(usuario.id), "usuario": usuario.usuario, "rol": usuario.rol,
            "iat": ahora, "exp": ahora + timedelta(hours=self._config.TOKEN_HORAS),
        }
        return jwt.encode(carga, self._config.SECRET_KEY, algorithm="HS256")

    def leer_token(self, token: str | None) -> dict | None:
        if not token:
            return None
        try:
            return jwt.decode(token, self._config.SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None


class ServicioUsuarios:
    """Casos de uso sobre usuarios: listar y registrar."""

    PATRON_USUARIO = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")

    def __init__(self, repositorio: UsuarioRepository, auth: ServicioAutenticacion) -> None:
        self._repo = repositorio
        self._auth = auth

    def listar(self) -> list[dict]:
        return [u.a_dict() for u in self._repo.listar()]

    def registrar(self, nombre: str, contrasena: str, rol: str) -> Usuario:
        nombre = (nombre or "").strip()
        if not self.PATRON_USUARIO.match(nombre):
            raise ErrorValidacion("El usuario debe tener de 3 a 50 caracteres (letras, números, . _ -).")
        if rol not in Rol.TODOS:
            raise ErrorValidacion("Elige un rol válido: Administrador, Auditor o Cliente.")
        if len(contrasena or "") < 6:
            raise ErrorValidacion("La contraseña debe tener al menos 6 caracteres.")
        try:
            return self._repo.crear(nombre, self._auth.hashear(contrasena), rol)
        except UsuarioDuplicado:
            raise ErrorValidacion("Ese nombre de usuario ya existe.")
