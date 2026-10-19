import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from .config import Config
from .models import Producto, Rol, Usuario
from .repository import ProductoRepository, UsuarioDuplicado, UsuarioRepository


class ErrorValidacion(Exception):
    pass


class CredencialesInvalidas(Exception):
    pass


class ProductoNoEncontrado(Exception):
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


class ServicioProductos:
    """Casos de uso del catálogo: listar, filtrar por categoría, ver detalle, editar y eliminar."""

    def __init__(self, repositorio: ProductoRepository) -> None:
        self._repo = repositorio

    def listar(self, categoria: str | None = None) -> list[Producto]:
        return self._repo.listar((categoria or "").strip() or None)

    def categorias(self) -> list[str]:
        return self._repo.categorias()

    def obtener(self, producto_id: int) -> Producto:
        producto = self._repo.obtener(producto_id)
        if producto is None:
            raise ProductoNoEncontrado()
        return producto

    def actualizar(self, producto_id: int, datos: dict) -> Producto:
        self.obtener(producto_id)  # lanza ProductoNoEncontrado si no existe

        titulo = str(datos.get("titulo") or "").strip()
        descripcion = str(datos.get("descripcion") or "").strip()
        categoria = str(datos.get("categoria") or "").strip()

        if not 3 <= len(titulo) <= 150:
            raise ErrorValidacion("El título debe tener de 3 a 150 caracteres.")
        try:
            precio = Decimal(str(datos.get("precio")))
            if not precio.is_finite() or precio <= 0 or precio >= Decimal("100000000"):
                raise InvalidOperation()
            precio = precio.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            raise ErrorValidacion("El precio debe ser un número mayor que 0.")
        if not 1 <= len(descripcion) <= 2000:
            raise ErrorValidacion("La descripción es obligatoria (máximo 2000 caracteres).")
        if not 2 <= len(categoria) <= 50:
            raise ErrorValidacion("La categoría debe tener de 2 a 50 caracteres.")

        self._repo.actualizar(producto_id, titulo, precio, descripcion, categoria)
        return self.obtener(producto_id)

    def eliminar(self, producto_id: int) -> None:
        if not self._repo.eliminar(producto_id):
            raise ProductoNoEncontrado()
