import pymysql

from .database import Database
from .models import Producto, Usuario


class UsuarioDuplicado(Exception):
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
    """Acceso a datos de la tabla productos."""

    COLUMNAS = "id, titulo, precio, descripcion, categoria, imagen"

    def __init__(self, db: Database) -> None:
        self._db = db

    def contar(self) -> int:
        with self._db.transaccion() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM productos")
            return int(cur.fetchone()["total"])

    def crear(self, titulo: str, precio, descripcion: str, categoria: str, imagen: str) -> Producto:
        with self._db.transaccion() as cur:
            cur.execute(
                "INSERT INTO productos (titulo, precio, descripcion, categoria, imagen) VALUES (%s, %s, %s, %s, %s)",
                (titulo, precio, descripcion, categoria, imagen),
            )
            nuevo_id = int(cur.lastrowid)
        return Producto(nuevo_id, titulo, precio, descripcion, categoria, imagen)

    def listar(self, categoria: str | None = None) -> list[Producto]:
        with self._db.transaccion() as cur:
            if categoria:
                cur.execute(f"SELECT {self.COLUMNAS} FROM productos WHERE categoria = %s ORDER BY id", (categoria,))
            else:
                cur.execute(f"SELECT {self.COLUMNAS} FROM productos ORDER BY id")
            return [Producto.desde_fila(f) for f in cur.fetchall()]

    def categorias(self) -> list[str]:
        with self._db.transaccion() as cur:
            cur.execute("SELECT DISTINCT categoria FROM productos ORDER BY categoria")
            return [f["categoria"] for f in cur.fetchall()]

    def obtener(self, producto_id: int) -> Producto | None:
        with self._db.transaccion() as cur:
            cur.execute(f"SELECT {self.COLUMNAS} FROM productos WHERE id = %s", (producto_id,))
            fila = cur.fetchone()
            return Producto.desde_fila(fila) if fila else None

    def actualizar(self, producto_id: int, titulo: str, precio, descripcion: str, categoria: str) -> None:
        with self._db.transaccion() as cur:
            cur.execute(
                "UPDATE productos SET titulo = %s, precio = %s, descripcion = %s, categoria = %s WHERE id = %s",
                (titulo, precio, descripcion, categoria, producto_id),
            )

    def eliminar(self, producto_id: int) -> bool:
        with self._db.transaccion() as cur:
            cur.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
            return cur.rowcount > 0
