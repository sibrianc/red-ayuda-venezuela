# Red de Ayuda Venezuela

**[Español](#español) · [English](#english)**

Plataforma web humanitaria para una emergencia por terremoto en Venezuela: registra, limpia y publica de forma segura reportes de personas, ayuda, recursos, zonas y mascotas, con mapa, directorio y coordinación. Bilingüe (ES/EN). **No es un servicio oficial de emergencia.**

A humanitarian web platform for an earthquake emergency in Venezuela: it safely registers, cleans and publishes reports of people, help, resources, areas and pets, with a map, directory and coordination. Bilingual (ES/EN). **It is not an official emergency service.**

---

## Español

La plataforma puede operar de forma **autónoma** (sin revisión humana) gracias a una limpieza y verificación automática de datos; la revisión humana sigue disponible para quien se sume al proyecto. Usa **solo datos reales** con su atribución; **nunca** expone datos privados ni publica menores.

### Funciones

- **Formularios públicos**: persona sin contacto, solicitud de ayuda, oferta de recurso, zona afectada, zona sin comunicación y **mascota desaparecida**.
- **Pipeline autónomo** (`AUTO_PUBLISH`): los reportes limpios y completos se publican solos; los que fallan la verificación (incompletos, posible spam o duplicado, o que involucran a un menor) se resguardan en cola sin perderse.
- **Separación estricta público/privado**: contacto, dirección exacta y notas médicas nunca se publican; los menores nunca se publican automáticamente; las coordenadas públicas se redondean (~1 km).
- **Mapa "Centro de Operaciones"** con datos reales, calor por densidad de desaparecidos y filtros por radio.
- **Directorio por secciones** (cada una con su página y buscador): personas (desaparecidas/localizadas/fallecidas), edificios e incidentes, servicios, zonas sin comunicación y mascotas.
- **Ingesta desde fuentes verificadas** con atribución y deduplicación: personas (PFIF/listas), incidentes, servicios (OpenStreetMap) y **mascotas** (`flask import-pets-json`).
- **Centro de coordinación** (familias ↔ rescatistas ↔ recursos) y **red de contacto verificada** (911, instituciones, colectivos).
- **Reenvío automático opcional** de la proyección pública (sin datos privados) a instituciones.
- **Bilingüe ES/EN** con cambio de idioma en toda la interfaz.

### Stack

Python, Flask, SQLAlchemy, PostgreSQL, Flask-Migrate, Flask-Login, Flask-WTF, Jinja, Bootstrap, JavaScript, Leaflet y OpenStreetMap.

### Instalación local

Requiere Python 3.11+ y PostgreSQL (para una prueba rápida puede usarse SQLite temporalmente).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
flask db upgrade
flask create-admin
flask run
```

### Variables de entorno

- `SECRET_KEY`: valor largo y aleatorio; obligatorio en producción.
- `DATABASE_URL`: conexión PostgreSQL.
- `FLASK_ENV`: `development`, `testing` o `production`.
- `AUTO_PUBLISH`: `true` (default) publica reportes limpios sin revisión humana; `false` exige aprobación manual.
- `INSTITUTION_FORWARD_ENABLED` / `INSTITUTION_WEBHOOK_URL`: reenvío automático de la proyección pública (sin datos privados). Desactivado por defecto.

`.env` nunca debe subirse a GitHub.

### Idiomas (i18n)

El español es el idioma fuente; el inglés se sirve desde un catálogo (`app/i18n.py`), sin dependencias ni compilación. El idioma se elige con `?lang=es|en` (se recuerda en una cookie). Lo no traducido cae al español.

### Pruebas

```bash
pytest --cov=app
```

Cubren privacidad pública, permisos, moderación, mapa, automatización, mascotas, i18n y exportaciones.

### Privacidad

- Cada reporte se limpia y verifica automáticamente al ingresar (`app/services/intake.py`).
- Contacto, direcciones exactas, notas médicas y notas internas no aparecen en HTML ni JSON público.
- Solo un reporte `approved` y marcado como público es visible. Los menores nunca se publican automáticamente.

Consulta [docs/operations.md](docs/operations.md) para operación y seguridad, y la **guía de despliegue paso a paso** en [docs/deploy-paso-a-paso.md](docs/deploy-paso-a-paso.md) (GitHub → Render → dominio → datos → admin/2FA).

### Open source y contribución

Proyecto bajo licencia **[MIT](LICENSE)**. ¡Las contribuciones son bienvenidas!

- Cómo contribuir y **reglas de datos no negociables** (solo datos reales, nunca exponer datos privados, menores fuera del flujo público, atribuir fuentes): [CONTRIBUTING.md](CONTRIBUTING.md)
- Código de conducta: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Reportar vulnerabilidades en privado: [SECURITY.md](SECURITY.md)

---

## English

The platform can run **autonomously** (without human review) thanks to automatic data cleaning and verification; human review remains available for anyone who joins the project. It uses **real data only**, with attribution; it **never** exposes private data and **never** publishes minors.

### Features

- **Public forms**: person out of contact, help request, resource offer, affected area, area without communication, and **lost pet**.
- **Autonomous pipeline** (`AUTO_PUBLISH`): clean, complete reports publish themselves; those failing verification (incomplete, possible spam or duplicate, or involving a minor) are held in a queue and never lost.
- **Strict public/private separation**: contact, exact address and medical notes are never published; minors are never auto-published; public coordinates are rounded (~1 km).
- **"Operations Center" map** with real data, heat by density of missing people and radius filters.
- **Directory split into sections** (each with its own page and search): people (missing/located/deceased), buildings and incidents, services, areas without communication, and pets.
- **Ingestion from verified sources** with attribution and deduplication: people (PFIF/lists), incidents, services (OpenStreetMap) and **pets** (`flask import-pets-json`).
- **Coordination center** (families ↔ rescuers ↔ resources) and a **verified contact network** (911, institutions, collectives).
- **Optional automatic forwarding** of the public projection (no private data) to institutions.
- **Bilingual ES/EN** with a language switch across the whole interface.

### Stack

Python, Flask, SQLAlchemy, PostgreSQL, Flask-Migrate, Flask-Login, Flask-WTF, Jinja, Bootstrap, JavaScript, Leaflet and OpenStreetMap.

### Local setup

Requires Python 3.11+ and PostgreSQL (SQLite can be used temporarily for a quick test).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
flask db upgrade
flask create-admin
flask run
```

### Environment variables

- `SECRET_KEY`: long random value; required in production.
- `DATABASE_URL`: PostgreSQL connection.
- `FLASK_ENV`: `development`, `testing` or `production`.
- `AUTO_PUBLISH`: `true` (default) publishes clean reports without human review; `false` requires manual approval.
- `INSTITUTION_FORWARD_ENABLED` / `INSTITUTION_WEBHOOK_URL`: automatic forwarding of the public projection (no private data). Off by default.

`.env` must never be committed to GitHub.

### Languages (i18n)

Spanish is the source language; English is served from a catalog (`app/i18n.py`), with no dependencies or compilation. The language is chosen with `?lang=es|en` (remembered in a cookie). Untranslated text falls back to Spanish.

### Tests

```bash
pytest --cov=app
```

They cover public privacy, permissions, moderation, the map, automation, pets, i18n and exports.

### Privacy

- Every report is cleaned and verified automatically on intake (`app/services/intake.py`).
- Contact, exact addresses, medical notes and internal notes never appear in public HTML or JSON.
- Only an `approved`, explicitly public report is visible. Minors are never auto-published.

See [docs/operations.md](docs/operations.md) for operations and security, and the **step-by-step deployment guide** in [docs/deploy-paso-a-paso.md](docs/deploy-paso-a-paso.md) (GitHub → Render → domain → data → admin/2FA).

### Open source and contributing

Licensed under **[MIT](LICENSE)**. Contributions are welcome!

- How to contribute and the **non-negotiable data rules** (real data only, never expose private data, minors out of the public flow, attribute sources): [CONTRIBUTING.md](CONTRIBUTING.md)
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Report vulnerabilities privately: [SECURITY.md](SECURITY.md)
