# Documento de seguimiento (handoff)

> Última actualización: **2026-06-28**. Este documento existe para que otra persona o
> asistente de AI pueda continuar el proyecto sin perder contexto. Si haces cambios
> importantes, actualiza este archivo.

## 1. Qué es el proyecto

**Red de Ayuda Venezuela**: aplicación web Flask para registrar, revisar y publicar de
forma segura reportes humanitarios durante una emergencia por terremoto. Es
**privacy-first**: todo reporte entra `pending` y privado; **nada se publica
automáticamente**; **no se usa AI en producción**. No es un servicio oficial de
emergencia.

La documentación rectora vive en `docs/project/` (6 `.docx`) y el plan de expansión
E0–E12 vive en `docs/project/07 - Plan de Expansion Operativa, Datos y
Plataforma.docx`. Este séptimo documento amplía el MVP, pero está subordinado a los
seis documentos rectores. Jerarquía en caso de
ambigüedad: ver `docs/README.md`. Reglas y límites obligatorios en `docs/project/06 -
AI Coding Instructions - Prompt Pack.docx` (resumidas en la sección 7 de este
documento).

## 2. Dónde vive el código

- **Repositorio (privado):** https://github.com/sibrianc/red-ayuda-venezuela
- **Rama de trabajo:** `main`
- **Cuenta GitHub:** `sibrianc`
- **Commits hasta hoy:**
  - `964cd34` — implementación inicial del MVP privacy-first (14 fases).
  - `b487bd7` — fix: permitir íconos de Leaflet en el CSP (`img-src` incluía solo
    `self`, `data:` y `tile.openstreetmap.org`; faltaba `unpkg.com`, por lo que los
    pines del mapa salían rotos). Incluye test de regresión.

## 3. Estado actual: ¿en qué fase estamos?

El plan (Prompt Pack) define **14 fases**. **Las 14 están implementadas en código.**

| #  | Fase | Estado |
|----|------|--------|
| 1  | Estructura base Flask (app factory + Blueprints) | ✅ |
| 2  | Modelos + migraciones | ✅ |
| 3  | Formularios públicos (4 tipos) | ✅ |
| 4  | Auth y admin básico | ✅ |
| 5  | Panel admin de revisión (notas + historial) | ✅ |
| 6  | Publicación pública segura | ✅ |
| 7  | Búsqueda, filtros y paginación | ✅ |
| 8  | Mapa Leaflet + OpenStreetMap | ✅ |
| 9  | Automatización sin AI (prioridad / duplicados / matching) | ✅ |
| 10 | Offline básico (borradores en localStorage, sin campos sensibles) | ✅ |
| 11 | Reportar abuso | ✅ |
| 12 | Exportación CSV admin (pública e interna) | ✅ |
| 13 | Tests mínimos | ✅ (19 tests, 86% cobertura) |
| 14 | Deploy en Render | ⏳ **Config lista, NO desplegado** |

**Conclusión:** a nivel de código no falta prácticamente nada. Lo pendiente es el
**deploy real (Fase 14)** y, opcionalmente, una verificación visual del flujo completo
en navegador.

### Expansión aprobada conceptualmente (todavía no implementada)

El documento `07 - Plan de Expansion Operativa, Datos y Plataforma.docx` define una
nueva secuencia E0–E12 para convertir el MVP en una plataforma operativa de mayor
alcance: sistema visual institucional, formularios simplificados, MapLibre/H3,
PostGIS, ingestión horaria de fuentes autorizadas, limpieza y deduplicación,
procedencia, recursos, asignaciones y dashboards. También exige una carga inicial
amplia para que el mapa nazca útil. Ninguna de estas fases está implementada todavía;
cada una requiere rama, pruebas, revisión de privacidad y su puerta de salida. Los
costos, contactos con fuentes, cambios de infraestructura y despliegue siguen
requiriendo aprobación explícita.

**Última fase aprobada:** E0 — Ratificación y gobernanza, rama `phase/e0-governance`.
Se incorporó la propuesta `docs/data-governance.md` con clasificación de datos,
roles, ciclo de autorización de fuentes y puertas de publicación. El propietario
revisó y ratificó la fase antes de iniciar E1.

Validación E0.1: 24/24 pruebas de aplicación y 15/15 comprobaciones del flujo visual
local pasan. Por decisión del propietario se adelantó una iteración visual antes de
E1: formularios guiados de tres pasos, ubicación asistida sin coordenadas manuales,
precisión pública reducida, sistema visual institucional y mapa operativo con filtros,
panel accesible y concentración aproximada. No se añadieron dependencias, costos ni
servicios externos. E2 y E9 conservarán su alcance de evolución posterior.

## 4. Resultados de la revisión profunda (2026-06-27/28)

Se revisó infra, código, lógica y flujo contra los 6 documentos fuente. Veredicto:
**en muy buen estado.**

- **Privacidad (lo más crítico): OK.** Los campos privados (teléfono, dirección exacta,
  notas médicas/internas, datos del reportante) solo se renderizan en plantillas admin
  protegidas por rol o en el propio formulario del usuario. Las vistas públicas
  (`/reportes`, detalle) y el endpoint `/mapa/data` solo exponen una proyección pública.
  Hay tests que verifican incluso las claves exactas del JSON público.
- **Seguridad: OK.** CSRF en todos los formularios, contraseñas hasheadas (Werkzeug),
  rutas admin con `roles_required`, honeypot anti-bots, login que **no revela si el email
  existe**, headers de seguridad (CSP, HSTS en prod, X-Frame-Options, etc.), CSV con
  protección anti-inyección (`csv_safe`). Rate limiting **no es requisito del MVP** según
  el Security Checklist ("se considera si hay abuso"); no se agregó ninguna dependencia.
- **Infraestructura / deploy: OK.** Verificado con Alembic que **la migración coincide
  exactamente con los modelos (sin deriva)**: `flask db upgrade` genera el esquema
  correcto. `render.yaml` + gunicorn correctos; `ProductionConfig.validate()` exige
  `SECRET_KEY` y `DATABASE_URL`.
- **Lógica / flujo: OK.** Estados inician `pending` + privado; aprobar y publicar son
  decisiones separadas; cada cambio de estado crea historial; nada se publica
  automáticamente. El dashboard admin y sus filtros de estado responden 200.

**Único bug encontrado y ya corregido:** marcadores del mapa rotos por el CSP (commit
`b487bd7`).

## 5. Cómo correr el proyecto localmente

Requiere Python 3.11+ (el repo se ha probado con la venv incluida). Para una prueba
rápida **sin PostgreSQL** se puede usar SQLite (producción debe usar PostgreSQL).

```bash
# 1) Entorno
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 2) Variables (para prueba rápida con SQLite)
export FLASK_APP=wsgi.py
export FLASK_ENV=development
export SECRET_KEY="cualquier-valor-largo-para-local"
export DATABASE_URL="sqlite:///$(pwd)/instance/demo.sqlite3"

# 3) Base de datos
flask db upgrade            # crea el esquema desde la migración

# 4) Crear admin inicial (interactivo: pide email, nombre y contraseña >= 12 chars)
flask create-admin

# 5) Levantar
flask run                   # http://127.0.0.1:5000
```

> Para una demo automatizada existe `scripts/browser_audit.py` (requiere
> `requirements-ui.txt`, Playwright con navegador instalado y el servidor en el puerto
> 5010). Es auditoría visual opcional.

### Pruebas

```bash
pytest --cov=app           # 19 tests, ~86% cobertura
python -m compileall -q app
```

## 6. Cómo subir cambios a GitHub (sin código 2FA)

> El problema original era que `git push` por HTTPS pedía un "código de la app" (2FA)
> que el dueño no recibe. **Solución ya aplicada:** el CLI `gh` está autenticado con un
> token y git usa ese token como credential helper. **No vuelve a pedir código.**

```bash
git add -A
git commit -m "mensaje"
git push
```

Si el token caduca algún día: `gh auth login` (autenticación por navegador, tampoco usa
el código 2FA por SMS/app). Crear repos nuevos: `gh repo create <nombre> --private
--source=. --remote=origin --push`.

## 7. Reglas obligatorias que el próximo AI DEBE respetar

Del Prompt Pack (`docs/project/06`). No violar sin aprobación explícita del dueño:

- **No agregar AI en producción** (ni OpenAI/Claude/Gemini API). La AI es solo
  herramienta de desarrollo.
- **No agregar servicios pagados** sin aprobación: Google Maps, Twilio, WhatsApp API,
  SMS/email masivo, Stripe/PayPal, geocoding/mapas/almacenamiento pagados.
- Usar **Leaflet + OpenStreetMap** (no Google Maps).
- **No publicar reportes automáticamente**; siempre revisión humana.
- **No exponer datos privados** (teléfonos, direcciones exactas, notas internas/médicas,
  datos del reportante) en HTML/JSON público.
- Sin pagos, donaciones, chat en tiempo real, app móvil nativa, likes/ranking,
  scraping de redes.
- **Trabajar por fases pequeñas**, explicar antes de cambiar, hacer el **cambio mínimo**,
  no agregar dependencias innecesarias, no romper la arquitectura (app factory +
  Blueprints + `services/` para lógica).
- Privacidad y seguridad **prevalecen** sobre conveniencia o visibilidad.
- Cada cambio de alcance se registra en `docs/decisions.md`.

## 8. Próximos pasos sugeridos (en orden)

1. **(Opcional) Verificación visual del flujo completo** en navegador: enviar reporte →
   queda pendiente/privado → login admin → revisar/aprobar/publicar → aparece en listado
   y mapa → reportar abuso → revisar abuso → exportar CSV → logout. Seguir la "prueba de
   humo" de `docs/operations.md`.
2. **Fase 14 — Deploy en Render.** Requiere **aprobación explícita del costo** (el
   `render.yaml` usa plan de pago `starter` + Postgres `basic-256mb`). Pasos en
   `README.md` (sección Despliegue) y `docs/operations.md` (antes de cada deploy). Crear
   backup/snapshot antes de migraciones; correr `flask db upgrade`; crear admin por
   consola segura; correr la prueba de humo; conectar `redayudave.org` solo tras validar
   staging.
3. Mantener tests verdes y revisar exposición de datos en cada fase.

## 9. Decisiones tomadas en esta sesión

- Repo creado **privado** (datos humanitarios sensibles) con nombre
  `red-ayuda-venezuela`, rama `main`.
- Fix de CSP para íconos de Leaflet (`b487bd7`).
- No se agregó rate limiting (no requerido por el MVP según el Security Checklist).
- No se realizó deploy (pendiente de aprobación de costo).
