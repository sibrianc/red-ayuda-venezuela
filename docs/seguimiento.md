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
- **Rama de trabajo:** `phase/e2-public-experience`
- **Base de E2:** `4c263b4` (`phase/e1-source-register`). Las ramas están apiladas; E2
  debe revisarse contra E1 mientras las fases anteriores no estén fusionadas.
- **Cuenta GitHub:** `sibrianc`
- **Commits hasta hoy:**
  - `964cd34` — implementación inicial del MVP privacy-first (14 fases).
  - `b487bd7` — fix: permitir íconos de Leaflet en el CSP (`img-src` incluía solo
    `self`, `data:` y `tile.openstreetmap.org`; faltaba `unpkg.com`, por lo que los
    pines del mapa salían rotos). Incluye test de regresión.
  - `47414ee` — E0/E0.1: gobernanza, formularios guiados y línea visual/mapa operativo.
  - `d591d34` — checkpoint E1: registro de fuentes, controles de autorización,
    migración, enrutamiento seguro y documentación operativa.

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
amplia para que el mapa nazca útil. La **ingesta masiva (parte de E3/E4) ya comenzó a
implementarse** en código: ver "Checkpoint E3.1" más abajo (conector USGS real, modelos
canónicos, limpieza, deduplicación y filtros, todo local y sin costo). El resto de las
fases sigue pendiente; cada una requiere rama, pruebas, revisión de privacidad y su puerta
de salida. Los costos, contactos con fuentes, cambios de infraestructura y despliegue
siguen requiriendo aprobación explícita.

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

**Última fase aprobada:** E1 — Registro y acuerdos de fuentes, rama
`phase/e1-source-register`. Se investigaron fuentes oficiales y humanitarias y se
crearon `docs/source-register.md`, `docs/data-routing.md`, el modelo interno
`DataSource`, su migración y controles que rechazan fuentes no autorizadas. No se ha
contactado a terceros, usado credenciales, importado datos ni activado cron. La fase
El propietario aclaró que trabaja como desarrollador independiente y prioriza fuentes
públicas dispersas. USGS y GDACS quedan ratificadas para staging P0. Un acuerdo con una
organización socia es opcional y ya no bloquea la salida de E1.

El propietario aprobó E1 y autorizó iniciar E2. También decidió continuar sin gastos:
dominio, correo, Cloudflare, ReliefWeb autenticado, Render y cualquier compra quedan
diferidos hasta contar con un demo/staging y revisar presupuesto.

**Fase en curso:** E4 — Experiencia de élite (tema oscuro, mapa vivo estilo Weather,
directorio y datos operativos del terremoto), rama `phase/e4-elite-experience` (apilada
sobre `phase/e3-data-engine` y `phase/e2-public-experience`). Ver el checkpoint Fase B/E4
más abajo y la hoja de ruta al deploy.

### Checkpoint E2.1 — tablero público y modo ligero

- El inicio ahora prioriza situación, métricas aprobadas, información reciente,
  preparación de fuentes y accesos a personas, necesidades, recursos y zonas.
- `public_summary()` agrega únicamente reportes aprobados y públicos. La portada no
  consulta ni renderiza campos privados.
- `app/static/js/preferences.js` conserva una preferencia local de ancho de banda.
  En modo ligero `map.js` no crea Leaflet ni descarga teselas, pero mantiene el JSON y
  el listado accesible.
- Archivos principales: `app/public/routes.py`, `app/services/reporting.py`,
  `app/templates/public/home.html`, `app/templates/base.html`,
  `app/static/css/main.css`, `app/static/js/preferences.js`, `app/static/js/map.js` y
  `scripts/browser_audit.py`.
- Validación: 34/34 pruebas, `compileall`, validación sintáctica de JavaScript,
  `git diff --check` y 19/19 comprobaciones visuales/E2E. Sin errores de consola,
  filtraciones privadas ni overflow a 375 px.
- Capturas locales: `/private/tmp/rav_browser_audit/desktop-home.png`,
  `mobile-home.png` y `desktop-map-low-bandwidth.png`.
- Costo e infraestructura: cero cambios externos, cero dependencias y cero gasto.
- Puerta pendiente: revisión visual del propietario antes de definir E2.2.

### Checkpoint E3.1 — motor de ingesta masiva (USGS), local y sin costo

Primer motor de **recopilación real** de datos públicos, en respuesta a la prioridad del
propietario: recopilar, limpiar y filtrar **de forma masiva**, no manejar reportes
manuales sueltos. Antes de esto, "USGS/GDACS autorizadas" eran solo fichas de metadatos;
ningún código descargaba ni procesaba datos.

- **Archivos nuevos:** `app/ingestion/connectors.py` (conector USGS GeoJSON con librería
  estándar; *fetch* separado del *parseo*), `app/ingestion/pipeline.py` (limpieza,
  normalización, deduplicación idempotente y filtros), `tests/test_ingestion.py` (9
  pruebas) y migración `a1b2c3d4e5f6`.
- **Modelos nuevos** (`app/models.py`): `SourceRecord` (copia cruda inmutable +
  procedencia) e `IngestedEvent` (hecho normalizado, limpio, deduplicado; objeto canónico
  `Event`). Índices y restricciones `UNIQUE(source_slug, external_id)` para idempotencia.
- **Pipeline determinista:** valida y descarta basura, normaliza (orden lon/lat, epoch ms
  → UTC, tipos), deduplica por `(source_slug, external_id)` + `content_hash`, y filtra por
  magnitud y por recuadro de Venezuela. Re-correr **no crea duplicados** (solo actualiza lo
  que cambió).
- **Privacidad/no autopublicar:** `IngestedEvent` es capa **interna**; NO se expone en
  ninguna vista pública/JSON/mapa todavía. Publicar agregados será un paso aparte con su
  puerta y atribución (U.S. Geological Survey).
- **Validación:** 43/43 pruebas, `compileall`, migración upgrade → downgrade → upgrade y
  `flask db check` sin deriva. Demostración con 2.000 eventos sintéticos: 2.000 nuevos en
  la primera corrida, 0 duplicados al repetir, 601 marcados en región y bandas de magnitud
  correctas. Sin red en pruebas, sin dependencias, sin costo, sin contacto con terceros.
- **Actualización E3.2 — segunda fuente (GDACS):** se agregó el conector GDACS (UN/EC,
  multi-amenaza: sismos, inundaciones, ciclones, volcanes, incendios, sequías), con esquema
  verificado contra el endpoint en vivo. `IngestedEvent` ganó campos genéricos
  (`hazard_code`, `severity_value`, `severity_text`, `country`); migración `b2c3d4e5f6a7`.
  Esto prueba que el motor es agnóstico a la fuente: el mismo pipeline limpia/deduplica/
  filtra cualquier conector. 47/47 pruebas. Demo unificada de 2.000 eventos USGS+GDACS,
  idempotente. Comando `flask ingest-gdacs`.
- **Pendiente del frente de datos:** índice de ReliefWeb por enlaces públicos (difer­ido
  hasta tener correo del dominio para el `appname`); luego la puerta de publicación de
  agregados y la capa de mapa pública para fuentes autoritativas (con atribución).

#### Cómo correr la ingesta en local

```bash
# Con el entorno y la base ya creados (ver sección 5), aplica la migración nueva:
flask db upgrade

# Descarga, limpia, deduplica y guarda sismos públicos de USGS:
flask ingest-usgs                      # feed por defecto: month_2.5 (miles de eventos)
flask ingest-usgs --feed month_4.5     # menos volumen, mayor magnitud
flask ingest-usgs --region-only        # solo dentro del recuadro de Venezuela
flask ingest-usgs --min-magnitude 4    # filtra por magnitud mínima

# Descarga la alerta oficial de GDACS del terremoto (por defecto solo EQ + Venezuela):
flask ingest-gdacs                     # ampliar con --all-hazards / --all-world

# Descarga el directorio de servicios de Venezuela desde OpenStreetMap:
flask ingest-directory                 # hospitales, refugios, bomberos, agua, etc.

# Ver el volumen acumulado en la base (eventos + directorio):
flask ingest-stats
```

> Nota macOS: si ves un error de certificado SSL al descargar, ejecuta el
> `Install Certificates.command` que viene con tu instalación de Python. Es un ajuste
> local de certificados, no un cambio del proyecto.

### Checkpoint Fase B / E4 — experiencia de élite (rama `phase/e4-elite-experience`)

Rediseño completo orientado al evento real: **terremotos de Venezuela del 24 jun 2026**
(Mw 7,2 + 7,5; La Guaira la zona más devastada). El propietario pidió calidad de élite,
no genérica, y datos reales verificados.

- **Tema oscuro en todo el sitio** por defecto + **modo "sol"** (claro, alto contraste)
  con toggle en vivo. Sistema de tokens de color (`app/static/css/main.css`), controles de
  vidrio esmerilado, acentos medidos de la bandera. `app/static/js/preferences.js`.
- **Mapa vivo de élite** (`app/templates/map/index.html`, `app/static/js/map.js`): base
  profesional **CARTO Dark Matter**; **mapa de calor (KDE)** de intensidad por zona
  afectada (La Guaira la más intensa) que **a zoom bajo manda y a zoom alto desaparece**
  dando paso a **clusters → incidentes exactos** (edificio + dirección). Sismos apagados
  por defecto. Plugins: leaflet.heat, leaflet.markercluster (CSP actualizado para CARTO).
- **Datos operativos** (`app/models.py`, `app/services/operational.py`): modelos
  `Incident` (colapsos, atrapados, sepultados…) y `SituationMetric`; migraciones
  `d4e5f6a7b8c9` y `e5f6a7b8c9d0`. Endpoint `/mapa/live` (situación, intensidad,
  incidentes, sismos, servicios).
- **Cifras REALES citadas** vía `flask load-official-figures` (ONU/OCHA): ~50.000
  desaparecidos (en disputa), 1.430 fallecidos, 3.238 heridos, 2.245 rescatistas, 140
  perros — cada una con fuente, fecha y "en verificación". **Regla nueva:** solo hechos
  verificados de fuentes oficiales; nada inventado.
- **Ruta `/directorio`** (`app/templates/public/directory.html`): personas (buscar/
  reportar, **menores protegidos**), incidentes de prioridad (búsqueda + filtros por
  categoría, orden por severidad), servicios, y **registros oficiales de reunificación**
  (Cruz Roja RFL, Trace the Face, VenApp 0800-RESCATE). Buscador global operations-grade
  que filtra personas + incidentes + servicios a la vez. Acceso desde el nav y un botón
  prominente en el inicio.
- **Personas desaparecidas**: proyección pública con nombre, edad y última ubicación para
  reunificación; nunca contacto privado; **menores siempre excluidos** del público.
- **Validación:** 62/62 pruebas, `compileall`, sintaxis JS. Commits `3bdf6d6` (datos
  operativos) y `38079af` (UI). Datos del mapa aún de **muestra** (preview) salvo las
  cifras, que son reales; los datos reales entran con la ingesta y el importador PFIF.

### ¿Cuánto falta para el deploy? (hoja de ruta)

Estado: **listo para correr en local**; el deploy a producción (Render) sigue pendiente y
requiere decisiones del propietario. Lo que falta, en orden:

1. **Datos reales conectados** (no muestra): correr `flask ingest-usgs` / `ingest-directory`
   en una máquina con red; conectar **importador PFIF** + listas oficiales de fallecidos;
   curaduría de incidentes reales. (Trabajo de datos, mayormente gratis.)
2. **Decisión de costo/hosting**: Render necesita un plan pagado + PostgreSQL. Hay que
   aprobar el gasto (pendiente desde E1). Alternativa: free tier para staging.
3. **Infra de producción**: `SECRET_KEY` y `DATABASE_URL` reales, migraciones en Postgres,
   `flask create-admin`, revisar CSP/headers, dominio/correo (diferidos).
4. **Recopilación automática**: cron para refrescar fuentes (local gratis; en nube = costo).
5. **Prueba de humo + revisión de privacidad** final, y **fusionar las ramas apiladas**
   (e2 → e3 → e4) o abrir PRs en orden.

Resumen honesto: a nivel de **código y experiencia** estamos muy avanzados; para
**desplegar y que sea útil de verdad** falta sobre todo **conectar datos reales** y
**aprobar el hosting/costo**. Todo lo demás (motor, mapa, directorio, privacidad) ya está.

### EN CURSO (WIP) — Importador PFIF y registro de personas (sin terminar)

> Estado al pausar (créditos bajos). Esta es la fase #2 del orden recomendado:
> importar personas desaparecidas/fallecidas **ya publicadas** (PFIF, listas oficiales)
> para reunificación familiar. **Lo siguiente que toca: terminar el directorio y probar.**

**Ya hecho y committeado en commits previos / por commitear como WIP:**
- Modelo `PersonRecord` (`app/models.py`): personas publicadas con nombre, edad, última
  ubicación, `person_status` (missing/found/deceased), fuente, e `is_minor` (los menores
  se excluyen del público). Migración `f6a7b8c9d0e1`.
- Parser/conector PFIF (`app/ingestion/pfif.py`): agnóstico al namespace (soporta PFIF
  1.1–1.4: `full_name`, `given_name/family_name`, `first_name/last_name`); estado desde
  las notas (`believed_dead`→deceased, etc.); `fetch_pfif` + `parse_pfif`; detecta menores
  por edad < 18.
- Ingesta `ingest_persons` (`app/ingestion/pipeline.py`), idempotente por
  `(source_slug, external_id)`.
- Proyección `public_person_records(status, q)` (`app/services/operational.py`), **excluye
  menores**.
- Comando `flask import-pfif <URL|archivo> [--source-slug] [--attribution]`.
- 62/62 pruebas siguen verdes; `compileall` OK. (Estos archivos pueden estar SIN commitear
  si la sesión se cortó: revisar `git status`.)

**FALTA (para cerrar la fase #2):**
1. **Directorio**: integrar `public_person_records(status="missing")` en la sección de
   Personas (junto a los reportes propios) y **agregar la sección "Fallecidos"**
   (`status="deceased"`) en `app/templates/public/directory.html` y la ruta
   `app/public/routes.py` (pasar `deceased=...` y un buscador `q` que también filtre
   personas PFIF). CSS si hace falta.
2. **Pruebas**: parseo PFIF (un fixture XML 1.4 con una persona adulta + un menor + una
   nota `believed_dead`), exclusión de menores, mapeo de estado, dedup de `ingest_persons`.
   Crear `tests/test_pfif.py`.
3. **QA**: `pytest`, `compileall`, ciclo de migración `f6a7b8c9d0e1` upgrade/downgrade.
4. **Relanzar** server (puerto 5015) y **commitear** la fase. Actualizar este checkpoint.
5. **Dato real**: no hay feed PFIF público confirmado del evento; el importador queda listo
   y se llena cuando se conecte un feed (Google Person Finder si activa uno) o una lista
   oficial. NO sembrar personas falsas (regla del propietario: solo datos verificados).

**Cómo continuar en una nueva sesión:** revisar `git status` y `git log` en la rama
`phase/e4-elite-experience`; leer este WIP; terminar el punto 1, luego 2–4. El servidor de
revisión corre con `flask run --port 5015 --no-reload` usando
`DATABASE_URL=sqlite:///instance/demo_review.sqlite3` (tras `flask db upgrade` + `flask
seed-sample` + `flask load-official-figures`).

### Checkpoint técnico E1

- Archivos nuevos: `app/ingestion/registry.py`, `app/ingestion/catalog.py`,
  `docs/source-register.md`, `docs/data-routing.md`, migración `8d6f3b2c1a90` y
  `tests/test_source_registry.py`.
- Modelo nuevo: `DataSource`, exclusivamente interno. Registra permiso, clasificación,
  frecuencia, retención, responsable, revisión y el nombre de una variable de entorno;
  no guarda tokens, contraseñas ni payloads.
- Controles: una fuente solo entra a staging con estado `authorized_staging` o
  `active`, permiso documentado y fechas de autorización/revisión. Producción exige
  `active`.
- Validación local: 32/32 pruebas, `compileall`, `git diff --check`, migración
  upgrade → downgrade → upgrade y `flask db check` sin deriva.
- Estado externo: cero conectores, cero cron, cero descargas/importaciones, cero
  contactos con organizaciones y cero cambios en producción.
- Publicación: commit `d591d34` enviado a `origin/phase/e1-source-register`. La GitHub
  App devolvió 404 para el repositorio privado y `gh` conserva un token inválido; la
  comparación apilada se abrió en Safari para crear manualmente el PR E1 contra
  `phase/e0-governance`.
- Decisión vigente: USGS y GDACS autorizadas para staging P0; no existen conectores ni
  publicación automática. La siguiente acción es revisión final de E1 por el
  propietario y luego E2.
- Siguiente artefacto listo: `docs/outreach/logistics-cluster-draft.md`, dirigido a los
  contactos públicos de coordinación y gestión de información de la operación. Está
  incompleto en los datos del remitente y **no fue enviado**.
- Dominio/correo: RDAP devolvió `404 Object not found` para `redayudave.org`; no hay
  NS/A/MX. Se abrió el alta oficial de Cloudflare y se creó
  `docs/domain-email-setup.md`. El propietario debe introducir en Safari su correo,
  contraseña, 2FA, datos de registrante y pago. Ningún secreto se guarda en el repo.
  **Actualización:** el proceso quedó diferido antes de confirmar una compra; no se
  registró gasto ni configuración DNS/correo. Si el propietario alcanzó a crear una
  cuenta gratuita, queda sin uso hasta nueva aprobación.

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

> El problema original era que HTTPS/`gh` pedía autenticación que el dueño no recibía.
> **Solución vigente:** el remoto usa SSH y este repositorio tiene `core.sshCommand`
> apuntando a `~/.ssh/id_ed25519_redayudave` con `IdentitiesOnly=yes`. La llave pública
> ya está agregada a la cuenta `sibrianc` y `ssh -T` fue verificado. No modificar esta
> configuración ni volver a iniciar device login salvo que el dueño lo solicite.

```bash
git add -A
git commit -m "mensaje"
git push -u origin "$(git branch --show-current)"
```

El remoto esperado es `git@github.com:sibrianc/red-ayuda-venezuela.git`. En este
checkpoint, la sesión de `gh` no es confiable y la GitHub App no puede leer el repo
privado; para abrir un PR se usa temporalmente la página Compare de GitHub en el
navegador. No confundir esa limitación con el push: `git push` por SSH sí funciona.
URL de comparación E1:
`https://github.com/sibrianc/red-ayuda-venezuela/compare/phase/e0-governance...phase/e1-source-register?expand=1`.

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

1. Iniciar E2 en una rama nueva y priorizar la experiencia pública profesional:
   arquitectura de información, dashboard, directorio y sistema visual.
2. Mantener los PR apilados y fusionarlos según el orden de
   fases.
3. Mostrar el sitio local al propietario al final de cada iteración de E2.
4. Conservar la prueba de humo completa y el deploy en Render para la puerta de
   lanzamiento correspondiente. Costo, staging, DNS y producción siguen requiriendo
   aprobación explícita.

## 9. Decisiones tomadas en esta sesión

- Repo creado **privado** (datos humanitarios sensibles) con nombre
  `red-ayuda-venezuela`, rama `main`.
- Fix de CSP para íconos de Leaflet (`b487bd7`).
- No se agregó rate limiting (no requerido por el MVP según el Security Checklist).
- No se realizó deploy (pendiente de aprobación de costo).
