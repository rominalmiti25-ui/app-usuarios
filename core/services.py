import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from .config import Config
from .models import Producto, Rol, Usuario
from .repository import (
    CategoriaDuplicada, ProductoDuplicado, ProductoRepository, UltimoAdministrador, UsuarioDuplicado,
    UsuarioRepository,
)


class ErrorValidacion(Exception):
    pass


class CredencialesInvalidas(Exception):
    pass


class ProductoNoEncontrado(Exception):
    pass


class UsuarioNoEncontrado(Exception):
    pass


class CategoriaNoEncontrada(Exception):
    pass


class ConflictoCategoria(Exception):
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

    def eliminar(self, usuario_id: int, solicitante_id: int) -> None:
        if usuario_id == solicitante_id:
            raise ErrorValidacion("No puedes eliminar tu propia cuenta.")
        try:
            if not self._repo.eliminar(usuario_id):
                raise UsuarioNoEncontrado()
        except UltimoAdministrador:
            raise ErrorValidacion("No se puede eliminar al último administrador.")

    def sigue_siendo_administrador(self, usuario_id) -> bool:
        """El token dura horas: antes de una acción de administración se confirma que la cuenta sigue existiendo."""
        try:
            identificador = int(usuario_id)
        except (TypeError, ValueError):
            return False
        usuario = self._repo.obtener_por_id(identificador)
        return usuario is not None and usuario.rol == Rol.ADMINISTRADOR


IMAGEN_POR_DEFECTO = "static/productos/sin_imagen.jpg"
IMAGEN_MAX_BYTES = 3 * 1024 * 1024


def detectar_tipo_imagen(datos: bytes) -> str | None:
    """El tipo se deduce de los primeros bytes del archivo, nunca de lo que diga el cliente."""
    if datos.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    return None


class ServicioProductos:
    """Casos de uso del catálogo: consultar, crear, editar y eliminar productos y categorías."""

    def __init__(self, repositorio: ProductoRepository) -> None:
        self._repo = repositorio

    # ── Consulta ──
    def listar(self, categoria: str | None = None) -> list[Producto]:
        return self._repo.listar((categoria or "").strip() or None)

    def categorias(self) -> list[str]:
        return self._repo.categorias()

    def obtener(self, producto_id: int) -> Producto:
        producto = self._repo.obtener(producto_id)
        if producto is None:
            raise ProductoNoEncontrado()
        return producto

    # ── Productos ──
    def _validar(self, datos: dict) -> tuple[str, Decimal, str, str]:
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
        # La categoría debe existir; se guarda con el nombre exacto registrado
        existente = next((c for c in self._repo.categorias() if c.casefold() == categoria.casefold()), None)
        if existente is None:
            raise ErrorValidacion("Elige una categoría existente.")
        return titulo, precio, descripcion, existente

    def crear(self, datos: dict) -> Producto:
        titulo, precio, descripcion, categoria = self._validar(datos)
        try:
            return self._repo.crear(titulo, precio, descripcion, categoria, IMAGEN_POR_DEFECTO)
        except ProductoDuplicado:
            raise ErrorValidacion("Ya existe un producto con ese título.")

    def actualizar(self, producto_id: int, datos: dict) -> Producto:
        self.obtener(producto_id)  # lanza ProductoNoEncontrado si no existe
        titulo, precio, descripcion, categoria = self._validar(datos)
        try:
            self._repo.actualizar(producto_id, titulo, precio, descripcion, categoria)
        except ProductoDuplicado:
            raise ErrorValidacion("Ya existe un producto con ese título.")
        return self.obtener(producto_id)

    def eliminar(self, producto_id: int) -> None:
        if not self._repo.eliminar(producto_id):
            raise ProductoNoEncontrado()

    # ── Imágenes ──
    def subir_imagen(self, producto_id: int, datos: bytes) -> Producto:
        self.obtener(producto_id)
        if not datos:
            raise ErrorValidacion("No se recibió ninguna imagen.")
        if len(datos) > IMAGEN_MAX_BYTES:
            raise ErrorValidacion("La imagen es demasiado grande (máximo 3 MB).")
        tipo = detectar_tipo_imagen(datos)
        if tipo is None:
            raise ErrorValidacion("La imagen debe ser JPG, PNG o WEBP.")
        self._repo.guardar_imagen(producto_id, tipo, datos)
        return self.obtener(producto_id)

    def obtener_imagen(self, producto_id: int) -> tuple[str, bytes]:
        imagen = self._repo.obtener_imagen(producto_id)
        if imagen is None:
            raise ProductoNoEncontrado()
        return imagen

    # ── Categorías ──
    def crear_categoria(self, nombre: str) -> str:
        nombre = (nombre or "").strip()
        if not 2 <= len(nombre) <= 50:
            raise ErrorValidacion("La categoría debe tener de 2 a 50 caracteres.")
        try:
            self._repo.crear_categoria(nombre)
        except CategoriaDuplicada:
            raise ErrorValidacion("Esa categoría ya existe.")
        return nombre

    def eliminar_categoria(self, nombre: str) -> None:
        existente = next((c for c in self._repo.categorias() if c.casefold() == (nombre or "").strip().casefold()), None)
        if existente is None:
            raise CategoriaNoEncontrada()
        cantidad = self._repo.contar_por_categoria(existente)
        if cantidad > 0:
            raise ConflictoCategoria(
                f"No se puede eliminar «{existente}»: tiene {cantidad} producto(s). "
                "Elimínalos o cámbialos de categoría primero."
            )
        self._repo.eliminar_categoria(existente)
