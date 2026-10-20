-- Opcional: la app crea estas tablas sola al arrancar. Úsalo si prefieres crearlas a mano.
CREATE TABLE IF NOT EXISTS usuarios (
    id         INT          NOT NULL,            -- sin AUTO_INCREMENT: el id continuo lo asigna la app
    usuario    VARCHAR(50)  NOT NULL,
    rol        VARCHAR(20)  NOT NULL,
    contrasena VARCHAR(255) NOT NULL,            -- hash, nunca texto plano
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuario (usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS productos (
    id          INT           NOT NULL AUTO_INCREMENT,
    titulo      VARCHAR(150)  NOT NULL,
    precio      DECIMAL(10,2) NOT NULL,
    descripcion TEXT          NOT NULL,
    categoria   VARCHAR(50)   NOT NULL,
    imagen      VARCHAR(255)  NOT NULL,          -- ruta relativa (static/productos/p1.jpg, products/3/image?v=...) o URL completa
    PRIMARY KEY (id),
    UNIQUE KEY uq_titulo (titulo),
    KEY idx_categoria (categoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS categorias (
    nombre VARCHAR(50) NOT NULL,
    PRIMARY KEY (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Imágenes subidas por el administrador
CREATE TABLE IF NOT EXISTS producto_imagenes (
    producto_id INT        NOT NULL,
    tipo        VARCHAR(30) NOT NULL,
    datos       MEDIUMBLOB NOT NULL,
    version     BIGINT     NOT NULL,
    PRIMARY KEY (producto_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Marcas de tareas de una sola vez (migraciones y catálogo inicial)
CREATE TABLE IF NOT EXISTS ajustes (
    clave VARCHAR(50)  NOT NULL,
    valor VARCHAR(100) NOT NULL,
    PRIMARY KEY (clave)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
