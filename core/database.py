from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from .config import Config


class Database:
    """Maneja la conexión a MySQL en la nube (una conexión por solicitud, ideal para serverless)."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def _conectar(self):
        c = self._config
        opciones = dict(
            host=c.DB_HOST, port=c.DB_PORT, user=c.DB_USER, password=c.DB_PASSWORD,
            database=c.DB_NAME, charset="utf8mb4", cursorclass=DictCursor,
            autocommit=False, connect_timeout=10,
        )
        if c.DB_SSL:
            opciones["ssl"] = {"ca": c.DB_SSL_CA}
        return pymysql.connect(**opciones)

    @contextmanager
    def transaccion(self):
        """Entrega un cursor; confirma al salir bien y revierte si hay error."""
        conexion = self._conectar()
        try:
            with conexion.cursor() as cursor:
                yield cursor
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def inicializar_esquema(self) -> None:
        with self.transaccion() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT NOT NULL,
                    usuario VARCHAR(50) NOT NULL,
                    rol VARCHAR(20) NOT NULL,
                    contrasena VARCHAR(255) NOT NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_usuario (usuario)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS productos (
                    id INT NOT NULL AUTO_INCREMENT,
                    titulo VARCHAR(150) NOT NULL,
                    precio DECIMAL(10,2) NOT NULL,
                    descripcion TEXT NOT NULL,
                    categoria VARCHAR(50) NOT NULL,
                    imagen VARCHAR(255) NOT NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_titulo (titulo),
                    KEY idx_categoria (categoria)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS categorias (
                    nombre VARCHAR(50) NOT NULL,
                    PRIMARY KEY (nombre)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            # Las imágenes subidas por el administrador se guardan aquí (el disco de Vercel es de solo lectura)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS producto_imagenes (
                    producto_id INT NOT NULL,
                    tipo VARCHAR(30) NOT NULL,
                    datos MEDIUMBLOB NOT NULL,
                    version BIGINT NOT NULL,
                    PRIMARY KEY (producto_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            # Marcas de tareas que se hacen una sola vez (migraciones y catálogo inicial)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ajustes (
                    clave VARCHAR(50) NOT NULL,
                    valor VARCHAR(100) NOT NULL,
                    PRIMARY KEY (clave)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
