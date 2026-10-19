from functools import wraps

from flask import Flask, g, jsonify, make_response, redirect, render_template, request, send_from_directory

from .models import Rol
from .services import (
    CredencialesInvalidas, ErrorValidacion, ProductoNoEncontrado,
    ServicioAutenticacion, ServicioProductos, ServicioUsuarios,
)

COOKIE = "token"

# Cada rol ve una pantalla distinta después de iniciar sesión
PANTALLAS = {
    Rol.ADMINISTRADOR: "home_admin.html",
    Rol.AUDITOR: "home_auditor.html",
    Rol.CLIENTE: "home_cliente.html",
}


def registrar_rutas(app: Flask, auth: ServicioAutenticacion, usuarios: ServicioUsuarios,
                    productos: ServicioProductos) -> None:

    def requiere_sesion(vista):
        """Para pantallas: sin sesión redirige al login."""
        @wraps(vista)
        def envoltura(*args, **kwargs):
            datos = auth.leer_token(request.cookies.get(COOKIE))
            if not datos:
                return redirect("/login")
            g.sesion = datos
            return vista(*args, **kwargs)
        return envoltura

    def requiere_rol(*roles):
        """Para la API: 401 si no hay sesión, 403 si el rol no tiene permiso."""
        def decorador(vista):
            @wraps(vista)
            def envoltura(*args, **kwargs):
                datos = auth.leer_token(request.cookies.get(COOKIE))
                if not datos:
                    return jsonify(error="Sesión no válida. Inicia sesión."), 401
                if datos.get("rol") not in roles:
                    return jsonify(error="No tienes permiso para esta acción."), 403
                g.sesion = datos
                return vista(*args, **kwargs)
            return envoltura
        return decorador

    def producto_json(producto) -> dict:
        # La imagen se entrega como URL completa para que web y app la descarguen igual
        return producto.a_dict(request.url_root)

    @app.after_request
    def sin_cache(resp):
        # Las imágenes públicas del catálogo sí se pueden guardar en caché (rendimiento)
        if request.path.startswith("/static/productos/"):
            resp.headers["Cache-Control"] = "public, max-age=86400"
            return resp
        # Evita que el botón "Atrás" muestre vistas protegidas guardadas en caché (US02)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        return resp

    @app.get("/")
    def inicio():
        return redirect("/home" if auth.leer_token(request.cookies.get(COOKIE)) else "/login")

    @app.get("/login")
    def vista_login():
        if auth.leer_token(request.cookies.get(COOKIE)):
            return redirect("/home")
        return render_template("login.html")

    @app.get("/home")
    @requiere_sesion
    def vista_home():
        plantilla = PANTALLAS.get(g.sesion.get("rol"), "home_cliente.html")
        return render_template(plantilla, sesion=g.sesion)

    @app.get("/usuarios")
    @requiere_rol(Rol.ADMINISTRADOR, Rol.AUDITOR)
    def ver_usuarios():
        return jsonify(usuarios.listar())

    # ───────────────────────── Catálogo de productos (US03, US04, US05) ─────────────────────────

    @app.get("/products")
    @requiere_rol(*Rol.TODOS)
    def api_productos():
        return jsonify([producto_json(p) for p in productos.listar()])

    @app.get("/products/categories")
    @requiere_rol(*Rol.TODOS)
    def api_categorias():
        return jsonify(productos.categorias())

    @app.get("/products/category/<categoria>")
    @requiere_rol(*Rol.TODOS)
    def api_productos_por_categoria(categoria):
        return jsonify([producto_json(p) for p in productos.listar(categoria)])

    @app.get("/products/<int:producto_id>")
    @requiere_rol(*Rol.TODOS)
    def api_producto(producto_id):
        try:
            return jsonify(producto_json(productos.obtener(producto_id)))
        except ProductoNoEncontrado:
            return jsonify(error="Producto no disponible"), 404

    @app.put("/products/<int:producto_id>")
    @requiere_rol(Rol.ADMINISTRADOR)
    def api_actualizar_producto(producto_id):
        cuerpo = request.get_json(silent=True) or {}
        try:
            return jsonify(producto_json(productos.actualizar(producto_id, cuerpo)))
        except ProductoNoEncontrado:
            return jsonify(error="Producto no disponible"), 404
        except ErrorValidacion as error:
            return jsonify(error=str(error)), 400

    @app.delete("/products/<int:producto_id>")
    @requiere_rol(Rol.ADMINISTRADOR)
    def api_eliminar_producto(producto_id):
        try:
            productos.eliminar(producto_id)
        except ProductoNoEncontrado:
            return jsonify(error="Producto no disponible"), 404
        return jsonify(ok=True)

    # ───────────────────────── Autenticación ─────────────────────────

    @app.post("/auth/login")
    def api_login():
        cuerpo = request.get_json(silent=True) or {}
        try:
            usuario, token = auth.iniciar_sesion(cuerpo.get("usuario"), cuerpo.get("password"))
        except CredencialesInvalidas:
            return jsonify(error="Usuario o contraseña inválidos"), 401
        resp = make_response(jsonify(usuario.a_dict()), 200)
        resp.set_cookie(COOKIE, token, httponly=True, secure=request.is_secure, samesite="Lax",
                        max_age=60 * 60 * 24)
        return resp

    @app.post("/auth/registro")
    @requiere_rol(Rol.ADMINISTRADOR)
    def api_registro():
        cuerpo = request.get_json(silent=True) or {}
        try:
            nuevo = usuarios.registrar(cuerpo.get("usuario"), cuerpo.get("password"), cuerpo.get("rol"))
        except ErrorValidacion as error:
            return jsonify(error=str(error)), 400
        return jsonify(nuevo.a_dict()), 201

    @app.post("/auth/logout")
    def api_logout():
        resp = make_response(jsonify(ok=True))
        resp.delete_cookie(COOKIE, samesite="Lax")
        return resp

    @app.get("/manifest.json")
    def manifest():
        return jsonify(
            id="/", name="App Usuarios", short_name="Usuarios",
            start_url="/login", scope="/", display="standalone",
            background_color="#0f172a", theme_color="#2563eb",
            icons=[
                {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": "/static/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
            ],
        )

    @app.get("/sw.js")
    def service_worker():
        # Se sirve desde la raíz para que controle todo el sitio
        return send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")

    @app.errorhandler(500)
    def error_interno(_):
        return jsonify(error="Error interno del servidor"), 500
