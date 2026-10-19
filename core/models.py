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


class Producto:
    """Artículo del catálogo. El JSON que devuelve la API coincide con estos campos."""

    def __init__(self, id: int, titulo: str, precio, descripcion: str, categoria: str, imagen: str) -> None:
        self.id = id
        self.titulo = titulo
        self.precio = precio
        self.descripcion = descripcion
        self.categoria = categoria
        self.imagen = imagen

    def a_dict(self, base_url: str = "") -> dict:
        imagen = self.imagen or ""
        # Las imágenes guardadas como ruta relativa se convierten en URL completa para cualquier cliente
        if imagen and not imagen.startswith(("http://", "https://")):
            imagen = base_url.rstrip("/") + "/" + imagen.lstrip("/")
        return {
            "id": self.id,
            "titulo": self.titulo,
            "precio": float(self.precio),
            "descripcion": self.descripcion,
            "categoria": self.categoria,
            "imagen": imagen,
        }

    @classmethod
    def desde_fila(cls, fila: dict) -> "Producto":
        return cls(fila["id"], fila["titulo"], fila["precio"], fila["descripcion"],
                   fila["categoria"], fila["imagen"])
