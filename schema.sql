-- Opcional: la app crea esta tabla sola al arrancar. Úsalo si prefieres crearla a mano.
CREATE TABLE IF NOT EXISTS usuarios (
    id         INT          NOT NULL,            -- sin AUTO_INCREMENT: el id continuo lo asigna la app
    usuario    VARCHAR(50)  NOT NULL,
    rol        VARCHAR(20)  NOT NULL,
    contrasena VARCHAR(255) NOT NULL,            -- hash, nunca texto plano
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuario (usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
