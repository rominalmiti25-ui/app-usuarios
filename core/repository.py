import time

import pymysql

from .database import Database
from .models import Producto, Rol, Usuario


class UsuarioDuplicado(Exception):
    pass


class UltimoAdministrador(Exception):
    pass


class ProductoDuplicado(Exception):
    pass


class CategoriaDuplicada(Exception):
    pass


class UsuarioRepository:
    """Acceso a datos de la tabla usuarios."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def listar(self) -> list[Usuario]:
        with self._db.transaccion() as cur:
            cur.execute("SELECT id, usuario, rol FROM usuarios ORDER BY id")
            return [Usuario.desde_fila(f) for f in cur.fetchall()]

    def contar(self) -> int:
        with self._db.transaccion() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM usuarios")
            return int(cur.fetchone()["total"])

    def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        with self._db.transaccion() as cur:
            cur.execute("SELECT id, usuario, rol FROM usuarios WHERE id = %s", (usuario_id,))
            fila = cur.fetchone()
            return Usuario.desde_fila(fila) if fila else None

    def eliminar(self, usuario_id: int) -> bool:
        """Elimina al usuario; nunca deja el sistema sin administradores (comprobación con bloqueo)."""
        with self._db.transaccion() as cur:
            cur.execute("SELECT rol FROM usuarios WHERE id = %s FOR UPDATE", (usuario_id,))
            fila = cur.fetchone()
            if not fila:
                return False
            if fila["rol"] == Rol.ADMINISTRADOR:
                cur.execute("SELECT COUNT(*) AS total FROM usuarios WHERE rol = %s FOR UPDATE", (Rol.ADMINISTRADOR,))
                if int(cur.fetchone()["total"]) <= 1:
                    raise UltimoAdministrador()
            cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
            return True

    def obtener_por_usuario(self, nombre: str) -> Usuario | None:
        with self._db.transaccion() as cur:
            cur.execute("SELECT id, usuario, rol, contrasena FROM usuarios WHERE usuario = %s", (nombre,))
            fila = cur.fetchone()
            return Usuario.desde_fila(fila) if fila else None

    def crear(self, nombre: str, hash_contrasena: str, rol: str) -> Usuario:
        """Inserta con id continuo (máximo + 1) dentro de una transacción bloqueante."""
        for _ in range(3):
            try:
                with self._db.transaccion() as cur:
                    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS siguiente FROM usuarios FOR UPDATE")
                    nuevo_id = int(cur.fetchone()["siguiente"])
                    cur.execute(
                        "INSERT INTO usuarios (id, usuario, rol, contrasena) VALUES (%s, %s, %s, %s)",
                        (nuevo_id, nombre, rol, hash_contrasena),
                    )
                return Usuario(nuevo_id, nombre, rol)
            except pymysql.err.IntegrityError as error:
                if "uq_usuario" in str(error):
                    raise UsuarioDuplicado() from error
                # choque de id por concurrencia: se reintenta con el siguiente número
        raise RuntimeError("No se pudo asignar un id; intenta de nuevo.")


class ProductoRepository:
    """Acceso a datos de productos, categorías e imágenes."""

    COLUMNAS = "id, titulo, precio, descripcion, categoria, imagen"

    def __init__(self, db: Database) -> None:
        self._db = db

    def preparar(self, semilla: list[dict]) -> None:
        """Migraciones del catálogo y carga inicial, todo en UNA conexión (rápido en serverless).

        Es seguro repetirlo: cada paso se ejecuta una sola vez y la carga usa INSERT IGNORE.
        """
        with self._db.transaccion() as cur:
            # 1) Índice único por título: impide duplicados aunque arranquen varias instancias a la vez
            cur.execute(
                "SELECT COUNT(*) AS n FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = 'productos' AND index_name = 'uq_titulo'"
            )
            if int(cur.fetchone()["n"]) == 0:
                cur.execute("DELETE p1 FROM productos p1 INNER JOIN productos p2 "
                            "ON p1.titulo = p2.titulo AND p1.id > p2.id")  # conserva el más antiguo
                try:
                    cur.execute("ALTER TABLE productos ADD UNIQUE KEY uq_titulo (titulo)")
                except Exception:  # otra instancia ya lo creó
                    pass

            cur.execute("SELECT clave FROM ajustes")
            hechos = {f["clave"] for f in cur.fetchall()}

            # 2) Las categorías que ya existían en los productos pasan a la tabla categorias
            if "categorias_migradas" not in hechos:
                cur.execute("INSERT IGNORE INTO categorias (nombre) SELECT DISTINCT categoria FROM productos")
                cur.execute("INSERT IGNORE INTO ajustes (clave, valor) VALUES ('categorias_migradas', '1')")

            # 3) Catálogo inicial (una sola vez; completa lo que falte sin duplicar)
            if "semilla_productos" not in hechos:
                for item in semilla:
                    cur.execute("INSERT IGNORE INTO categorias (nombre) VALUES (%s)", (item["categoria"],))
                    cur.execute(
                        "INSERT IGNORE INTO productos (titulo, precio, descripcion, categoria, imagen) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (item["titulo"], item["precio"], item["descripcion"], item["categoria"], item["imagen"]),
                    )
                cur.execute("INSERT IGNORE INTO ajustes (clave, valor) VALUES ('semilla_productos', '1')")

    # ── Productos ──
    def contar(self) -> int:
        with self._db.transaccion() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM productos")
            return int(cur.fetchone()["total"])

    def crear(self, titulo: str, precio, descripcion: str, categoria: str, imagen: str) -> Producto:
        try:
            with self._db.transaccion() as cur:
                cur.execute(
                    "INSERT INTO productos (titulo, precio, descripcion, categoria, imagen) VALUES (%s, %s, %s, %s, %s)",
                    (titulo, precio, descripcion, categoria, imagen),
                )
                nuevo_id = int(cur.lastrowid)
        except pymysql.err.IntegrityError as error:
            raise ProductoDuplicado() from error
        return Producto(nuevo_id, titulo, precio, descripcion, categoria, imagen)

    def listar(self, categoria: str | None = None) -> list[Producto]:
        with self._db.transaccion() as cur:
            if categoria:
                cur.execute(f"SELECT {self.COLUMNAS} FROM productos WHERE categoria = %s ORDER BY id", (categoria,))
            else:
                cur.execute(f"SELECT {self.COLUMNAS} FROM productos ORDER BY id")
            return [Producto.desde_fila(f) for f in cur.fetchall()]

    def obtener(self, producto_id: int) -> Producto | None:
        with self._db.transaccion() as cur:
            cur.execute(f"SELECT {self.COLUMNAS} FROM productos WHERE id = %s", (producto_id,))
            fila = cur.fetchone()
            return Producto.desde_fila(fila) if fila else None

    def actualizar(self, producto_id: int, titulo: str, precio, descripcion: str, categoria: str) -> None:
        try:
            with self._db.transaccion() as cur:
                cur.execute(
                    "UPDATE productos SET titulo = %s, precio = %s, descripcion = %s, categoria = %s WHERE id = %s",
                    (titulo, precio, descripcion, categoria, producto_id),
                )
        except pymysql.err.IntegrityError as error:
            raise ProductoDuplicado() from error

    def eliminar(self, producto_id: int) -> bool:
        with self._db.transaccion() as cur:
            cur.execute("DELETE FROM producto_imagenes WHERE producto_id = %s", (producto_id,))
            cur.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
            return cur.rowcount > 0

    # ── Imágenes ──
    def guardar_imagen(self, producto_id: int, tipo: str, datos: bytes) -> None:
        """Guarda la imagen y apunta productos.imagen a ella (el ?v= evita que se vea la versión vieja en caché)."""
        version = int(time.time() * 1000)
        with self._db.transaccion() as cur:
            cur.execute("DELETE FROM producto_imagenes WHERE producto_id = %s", (producto_id,))
            cur.execute(
                "INSERT INTO producto_imagenes (producto_id, tipo, datos, version) VALUES (%s, %s, %s, %s)",
                (producto_id, tipo, datos, version),
            )
            cur.execute("UPDATE productos SET imagen = %s WHERE id = %s",
                        (f"products/{producto_id}/image?v={version}", producto_id))

    def obtener_imagen(self, producto_id: int) -> tuple[str, bytes] | None:
        with self._db.transaccion() as cur:
            cur.execute("SELECT tipo, datos FROM producto_imagenes WHERE producto_id = %s", (producto_id,))
            fila = cur.fetchone()
            return (fila["tipo"], bytes(fila["datos"])) if fila else None

    # ── Categorías ──
    def categorias(self) -> list[str]:
        with self._db.transaccion() as cur:
            cur.execute("SELECT nombre FROM categorias ORDER BY nombre")
            return [f["nombre"] for f in cur.fetchall()]

    def crear_categoria(self, nombre: str) -> None:
        try:
            with self._db.transaccion() as cur:
                cur.execute("INSERT INTO categorias (nombre) VALUES (%s)", (nombre,))
        except pymysql.err.IntegrityError as error:
            raise CategoriaDuplicada() from error

    def contar_por_categoria(self, nombre: str) -> int:
        with self._db.transaccion() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM productos WHERE categoria = %s", (nombre,))
            return int(cur.fetchone()["total"])

    def eliminar_categoria(self, nombre: str) -> bool:
        with self._db.transaccion() as cur:
            cur.execute("DELETE FROM categorias WHERE nombre = %s", (nombre,))
            return cur.rowcount > 0
