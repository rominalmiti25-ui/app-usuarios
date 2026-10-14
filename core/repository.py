import pymysql

from .database import Database
from .models import Usuario


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
