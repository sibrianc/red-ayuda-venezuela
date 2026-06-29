# Red de Ayuda Venezuela

Aplicación web para registrar, revisar y publicar de forma segura reportes humanitarios durante una emergencia por terremoto en Venezuela.

La plataforma **no es un servicio oficial de emergencia**. Puede operar de forma
**autónoma** (sin revisión humana) gracias a una limpieza y verificación automática de
datos; la revisión humana sigue disponible para quien se sume al proyecto.

## Funciones

- Cuatro formularios públicos: personas sin contacto, solicitudes, recursos y zonas afectadas.
- **Pipeline autónomo** (`AUTO_PUBLISH`): los reportes limpios y completos se publican
  solos; los que fallan la verificación automática (incompletos, posible spam o duplicado,
  o que involucran a un menor) se resguardan en cola sin perderse.
- Separación estricta público/privado: contacto, dirección exacta y notas médicas nunca
  se publican; los menores nunca se publican automáticamente.
- **Mapa "Centro de Operaciones"** con datos reales, calor por densidad de desaparecidos,
  GPS y filtros por radio.
- **Directorio / buscador de personas** (Person Finder) y **centro de coordinación**
  (familias ↔ rescatistas ↔ recursos).
- **Red de contacto verificada**: 911, instituciones de rescate y colectivos de búsqueda.
- Ingesta de fuentes reales (sismos, daños estructurales, registros de personas) con
  atribución y corroboración.
- Reenvío automático opcional de la proyección pública a instituciones.
- Login y cola administrativa con notas e historial; reportes de abuso y exportación.

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
- `AUTO_PUBLISH`: `true` (default) publica reportes limpios sin revisión humana; `false`
  exige aprobación manual.
- `INSTITUTION_FORWARD_ENABLED` / `INSTITUTION_WEBHOOK_URL`: reenvío automático de la
  proyección pública (sin datos privados) a un endpoint propio. Desactivado por defecto.

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

- Cada reporte se limpia y verifica automáticamente al ingresar (`app/services/intake.py`).
  Con `AUTO_PUBLISH=true` los limpios y completos se publican; el resto queda en cola.
- Los datos de contacto, direcciones exactas, notas médicas y notas internas no aparecen en HTML o JSON público.
- Solo un reporte `approved` y marcado explícitamente como público es visible.
- Los reportes que involucran a un menor nunca se publican automáticamente.
- Las exportaciones internas requieren rol administrador y se marcan como contenido sensible.

Consulta [docs/README.md](docs/README.md) para la jerarquía documental y [docs/operations.md](docs/operations.md) para operación y seguridad.

## Open source y contribución

Proyecto bajo licencia **[MIT](LICENSE)**. ¡Las contribuciones son bienvenidas!

- Cómo contribuir y reglas de datos: [CONTRIBUTING.md](CONTRIBUTING.md)
- Código de conducta: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Reportar vulnerabilidades (en privado): [SECURITY.md](SECURITY.md)

Antes de aportar, lee las **reglas de datos no negociables** (solo datos reales, nunca
exponer datos privados, menores fuera del flujo público, atribuir fuentes) en
`CONTRIBUTING.md`.
