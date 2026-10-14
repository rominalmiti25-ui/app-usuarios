# App Usuarios (Flask + MySQL en la nube)

App móvil (web responsiva instalable) en Python con POO. Login, registro, cierre de sesión y
JSON de usuarios en `/usuarios`. Base de datos MySQL **en la nube** (nada local).

## Estructura
- `app.py` – punto de entrada (Vercel busca la variable `app`)
- `core/config.py` – `Config` (variables de entorno)
- `core/database.py` – `Database` (conexión MySQL, transacciones, creación de tabla)
- `core/models.py` – `Usuario`, `Rol`, `AsignadorDeRoles` (IDs 1-2 Admin, 3 Auditor, resto Cliente)
- `core/repository.py` – `UsuarioRepository` (SQL; id continuo = MAX(id)+1 en transacción)
- `core/services.py` – `ServicioAutenticacion` (hash + JWT) y `ServicioUsuarios`
- `core/routes.py` – rutas
- `templates/` – pantallas login, registro y home

## Rutas
| Ruta | Método | Descripción |
|---|---|---|
| `/login`, `/registro`, `/home` | GET | Pantallas (`/home` requiere sesión) |
| `/auth/login` | POST | `{usuario, password}` → 200 o 401 |
| `/auth/registro` | POST | `{usuario, password}` → 201 con id continuo |
| `/auth/logout` | POST | Borra el token |
| `/usuarios` | GET | JSON con id, usuario y rol (sin contraseñas) |

## 1. Base de datos en la nube
Crea una base MySQL gratuita (Aiven, TiDB Cloud Serverless, Railway, etc.) y copia host, puerto,
usuario, contraseña y nombre. La tabla `usuarios` se crea sola al arrancar (o usa `schema.sql`).

## 2. Ejecutar en PyCharm
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env        # y completa tus datos
python app.py                 # http://localhost:5000
```

## 3. GitHub
```bash
git init && git add . && git commit -m "App usuarios"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

## 4. Vercel
1. En vercel.com: **Add New → Project** → importa el repositorio.
2. En **Environment Variables** agrega: `SECRET_KEY`, `DB_HOST`, `DB_PORT`, `DB_USER`,
   `DB_PASSWORD`, `DB_NAME`, `DB_SSL=true`.
3. **Deploy**. Abre `https://tu-app.vercel.app/registro` para crear usuarios.

> Los primeros usuarios que registres serán: ID 1 y 2 → Administrador, ID 3 → Auditor, siguientes → Cliente.
> Si tu proveedor MySQL restringe IPs, habilita acceso desde cualquier IP (Vercel usa IPs dinámicas).
