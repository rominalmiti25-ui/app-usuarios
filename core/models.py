class Rol:
    ADMINISTRADOR = "Administrador"
    AUDITOR = "Auditor"
    CLIENTE = "Cliente"
    TODOS = (ADMINISTRADOR, AUDITOR, CLIENTE)


class Usuario:
    def __init__(self, id: int, usuario: str, rol: str, contrasena: str | None = None) -> None:
        self.id = id
        self.usuario = usuario
        self.rol = rol
        self._contrasena = contrasena  # hash; nunca se expone

    @property
    def hash_contrasena(self) -> str | None:
        return self._contrasena

    def a_dict(self) -> dict:
        return {"id": self.id, "usuario": self.usuario, "rol": self.rol}

    @classmethod
    def desde_fila(cls, fila: dict) -> "Usuario":
        return cls(fila["id"], fila["usuario"], fila["rol"], fila.get("contrasena"))
