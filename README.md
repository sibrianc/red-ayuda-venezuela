# Red de Ayuda Venezuela

Aplicación web para registrar, revisar y publicar de forma segura reportes humanitarios durante una emergencia por terremoto en Venezuela.

La plataforma **no es un servicio oficial de emergencia** y no publica reportes automáticamente. El MVP funciona sin AI en producción.

## Funciones del MVP

- Cuatro formularios públicos: personas sin contacto, solicitudes, recursos y zonas afectadas.
- Revisión humana y separación estricta entre datos públicos y privados.
- Login y cola administrativa con notas e historial.
- Búsqueda, filtros y mapa de ubicaciones aproximadas.
- Reglas deterministas para prioridad, duplicados y coincidencias.
- Reportes de abuso, exportación administrativa y borradores locales no sensibles.

## Stack

Python, Flask, SQLAlchemy, PostgreSQL, Flask-Migrate, Flask-Login, Flask-WTF, Jinja, Bootstrap, JavaScript, Leaflet y OpenStreetMap.

## Instalación local

Requiere Python 3.11+ y PostgreSQL.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
flask db upgrade
flask create-admin
flask run
```

Para una prueba rápida sin PostgreSQL se puede reemplazar temporalmente `DATABASE_URL` por una URL SQLite local. Producción debe usar PostgreSQL.

## Variables de entorno

- `SECRET_KEY`: valor largo y aleatorio; obligatorio en producción.
- `DATABASE_URL`: conexión PostgreSQL.
- `FLASK_ENV`: `development`, `testing` o `production`.
- `APP_NAME`: nombre visible.
- `APP_BASE_URL`: URL canónica cuando se despliegue.

`.env` nunca debe subirse a GitHub.

## Base de datos

```bash
flask db migrate -m "descripción"
flask db upgrade
flask db downgrade
```

Las migraciones destructivas requieren revisión y backup previo.

## Pruebas

```bash
pytest --cov=app
```

Las pruebas cubren privacidad pública, permisos, moderación, mapa, automatización y exportaciones.

La auditoría visual opcional requiere `requirements-ui.txt`, un navegador instalado con Playwright y el servidor local en el puerto 5010:

```bash
python scripts/browser_audit.py
```

## Despliegue

`render.yaml` describe una propuesta de servicio web y PostgreSQL. Antes de crear recursos:

1. Aprobar expresamente el costo del plan.
2. Crear backup o snapshot antes de migraciones importantes.
3. Ejecutar `flask db upgrade`.
4. Crear el administrador inicial mediante consola segura.
5. Ejecutar las pruebas de humo de `docs/operations.md`.
6. Conectar `redayudave.org` únicamente después de validar staging.

## Privacidad

- Todos los reportes empiezan `pending` y `is_public = false`.
- Los datos de contacto, direcciones exactas, notas médicas y notas internas no aparecen en HTML o JSON público.
- Solo un reporte `approved` y marcado explícitamente como público es visible.
- Las exportaciones internas requieren rol administrador y se marcan como contenido sensible.

Consulta [docs/README.md](docs/README.md) para la jerarquía documental y [docs/operations.md](docs/operations.md) para operación y seguridad.
