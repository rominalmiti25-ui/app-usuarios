-- Opcional: la app crea estas tablas sola al arrancar. Úsalo si prefieres crearlas a mano.
CREATE TABLE IF NOT EXISTS usuarios (
    id         INT          NOT NULL,            -- sin AUTO_INCREMENT: el id continuo lo asigna la app
    usuario    VARCHAR(50)  NOT NULL,
    rol        VARCHAR(20)  NOT NULL,
    contrasena VARCHAR(255) NOT NULL,            -- hash, nunca texto plano
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuario (usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Catálogo de productos (la app carga 12 productos de ejemplo si la tabla está vacía)
CREATE TABLE IF NOT EXISTS productos (
    id          INT           NOT NULL AUTO_INCREMENT,
    titulo      VARCHAR(150)  NOT NULL,
    precio      DECIMAL(10,2) NOT NULL,
    descripcion TEXT          NOT NULL,
    categoria   VARCHAR(50)   NOT NULL,
    imagen      VARCHAR(255)  NOT NULL,          -- ruta relativa (static/productos/p1.jpg) o URL completa
    PRIMARY KEY (id),
    KEY idx_categoria (categoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
