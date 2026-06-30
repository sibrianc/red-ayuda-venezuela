# Deploy paso a paso (al 100%) — GitHub + Render + dominio

Guía mínima y específica para poner la plataforma en vivo. La app **ya está lista
para producción**: trae `render.yaml`, `wsgi.py`, `gunicorn`, Postgres (`psycopg`),
migraciones (`flask db upgrade`) y `app/config.py` que valida `SECRET_KEY` y
`DATABASE_URL` en producción. Solo falta seguir estos pasos.

> Resumen del flujo: **GitHub (código) → Render (servidor + base de datos) → dominio (DNS) → cargar datos reales → cron**.

---

## 0. Qué vas a montar y cuánto cuesta

| Pieza | Dónde | Costo |
|---|---|---|
| Código | GitHub (repo público `sibrianc/red-ayuda-venezuela`, MIT) | $0 |
| Servidor web (Flask + gunicorn) | Render Web Service | Free $0 (se duerme) · **Starter $7/mes** (recomendado) |
| Base de datos | Render PostgreSQL | Free $0 (expira ~30–90 días) · **Basic ~$7/mes** (con backups) |
| Actualización de datos | Render Cron Job | incluido / ~$1/mes |
| Dominio | Namecheap / Cloudflare / Porkbun | **~$12/año** (`.org`) |

**Mínimo serio para producción: ~$14/mes + ~$12/año de dominio.** Para *probar* primero, todo puede ir en planes Free.

---

## 1. Cuentas que necesitas (una sola vez)
1. **GitHub** — ya tienes el repo `sibrianc/red-ayuda-venezuela` (privado).
2. **Render** — crea cuenta en https://render.com (entra con GitHub).
3. **Registrador de dominio** — recomendado **Cloudflare** (permite dominio raíz por CNAME) o **Namecheap/Porkbun**.
4. (Tarjeta de crédito solo si eliges planes pagos.)

---

## 2. Preparar el repositorio (verificación rápida)
En tu máquina, dentro del proyecto:

1. Confirma que NO subes secretos: el archivo `.env` debe estar en `.gitignore` (ya lo está).
2. Sube todo a GitHub:
   ```bash
   git checkout main           # o tu rama de release
   git pull
   git push origin main
   ```
3. Verifica que en el repo están: `requirements.txt`, `wsgi.py`, `render.yaml`, la carpeta `migrations/`. (Ya están.)

---

## 3. Crear la base de datos PostgreSQL en Render
**Opción manual (recomendada para controlar costos):**
1. En Render: **New ➜ PostgreSQL**.
2. Name: `red-ayuda-venezuela-db`. Region: la más cercana (ej. *Ohio* / *Oregon*).
3. Plan: **Free** para probar, o **Basic** para producción (trae backups).
4. **Create Database**. Espera a que diga *Available*.
5. Copia el **Internal Database URL** (empieza con `postgres://…`). Lo usarás en el paso 4.

> Nota: Render entrega `postgres://…`; la app lo convierte sola a `postgresql+psycopg://` (en `app/config.py`). No tienes que tocar nada.

---

## 4. Crear el Web Service en Render
1. En Render: **New ➜ Web Service** y **conecta el repo de GitHub** (autoriza a Render a ver `sibrianc/red-ayuda-venezuela`).
2. Configura:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn wsgi:app`
   - **Pre-Deploy Command:** `flask db upgrade`  ← aplica las migraciones en cada deploy
   - **Health Check Path:** `/`
   - **Plan:** Free (se duerme ~15 min sin tráfico) o **Starter $7/mes** (siempre activo).
3. **Environment Variables** (Add Environment Variable):
   | Key | Value |
   |---|---|
   | `FLASK_ENV` | `production` |
   | `FLASK_APP` | `wsgi.py` |
   | `SECRET_KEY` | una cadena larga aleatoria (ver abajo) |
   | `DATABASE_URL` | el *Internal Database URL* del paso 3 |
   - Generar un `SECRET_KEY`:
     ```bash
     python -c "import secrets; print(secrets.token_urlsafe(48))"
     ```
4. **Create Web Service**. Render hará build → `flask db upgrade` → arranca gunicorn.
5. Cuando termine, abre la URL `https://red-ayuda-venezuela.onrender.com` (o la que te asignen).

> **Atajo con Blueprint:** en vez de los pasos 3–4, puedes hacer **New ➜ Blueprint** y apuntar al repo: Render leerá `render.yaml` y creará el web + la base. **Ojo:** ese archivo define planes **pagos** (`starter` + `basic-256mb`). Si quieres Free, usa la opción manual o edita `render.yaml`.

---

## 5. Cargar los datos reales (una vez, tras el primer deploy)

> **¿Dónde corro estos comandos?** Hay dos formas; elige una:
> - **A) Shell de Render** (recomendado, requiere plan de pago **Starter $7/mes**):
>   Render ➜ tu Web Service ➜ pestaña **Shell**. Es una terminal dentro del servidor.
>   En el plan **Free no existe Shell** (por eso conviene Starter; ver §0).
> - **B) Desde tu Mac, sin pagar Shell** (plan Free): exporta la **External Database URL**
>   de Render (Render ➜ tu base de datos ➜ *Connections* ➜ *External Database URL*) y corre
>   los comandos contra ella, en tu `.venv`:
>   ```bash
>   export FLASK_APP=wsgi.py SECRET_KEY="loquesea"
>   export DATABASE_URL="postgresql://...EXTERNAL...?sslmode=require"
>   flask db upgrade        # crea las tablas si aún no existen
>   ```

Con cualquiera de las dos, corre:
```bash
flask load-official-figures      # cifras oficiales (ONU/OCHA) citadas
flask ingest-all                 # USGS + GDACS + OSM + Localizados + Venezuela Reporta + corroboración
# Reconocimientos REALES (unidades + perros, con fuentes) que vienen en el repo:
flask import-recognitions-json data/recognitions_venezuela_2026.json \
      --source-slug venezuela-2026 --attribution "Cobertura de prensa verificada"
```
Verifica abriendo: `/` (inicio), `/mapa` (peligro + servicios), `/directorio` (conteos reales) y `/reconocimientos` (unidades + perros con bandera).

> **Si el mapa sale vacío** no es un bug: significa que aún no se ingirieron datos en esa
> base. Corre el bloque de arriba. **Si ves `relation ... does not exist`**, faltó migrar:
> asegúrate de que el **Start Command** del Web Service sea
> `flask db upgrade && gunicorn wsgi:app` (en Free el *Pre-Deploy Command* no se ejecuta).

> No siembres datos de muestra (`seed-sample`) en producción: son de demostración.
> El reporte de **personas desaparecidas** se delega al registro ciudadano externo
> (`desaparecidosterremotovenezuela.com`); nosotros solo agregamos y presentamos.

---

## 5.1. Crear TU cuenta de administrador y activar 2FA

El panel es **hiper-privado** (solo tú + gente de confianza) y exige **doble factor (2FA)**.

1. Crea tu cuenta (en la **Shell** de Render, o localmente como en §5 opción B):
   ```bash
   flask create-admin            # te pedirá nombre, correo y contraseña (mín. 12)
   ```
2. Abre `https://tudominio.org/cuenta/login` e inicia sesión con ese correo/contraseña.
3. Te pedirá **configurar 2FA**: escanea el **código QR** con una app autenticadora
   (Google Authenticator, Microsoft Authenticator, etc.) y escribe el código de 6 dígitos.
   - Desde ahí, cada inicio de sesión pedirá la contraseña **y** el código de la app.
4. Ya dentro verás el **Panel** (`/admin`): cola de revisión, **Operación 4W**,
   **Reconocimientos**, **Fuentes**, **Usuarios** y **Auditoría**.

> Guarda la cuenta de la app autenticadora; sin ella no podrás entrar. Si la pierdes,
> entra por **Shell** y crea otra cuenta admin con `flask create-admin`.

## 5.2. Invitar colaboradores (sin registro público)

1. En el panel ➜ **Usuarios** ➜ rellena nombre, correo y **rol**:
   - **Revisor**: revisa y publica reportes (ve datos privados).
   - **Colaborador**: triage por notas; **no** ve datos personales ni publica.
   - **Observador**: solo lectura del tablero y de la Operación 4W.
   - **Administrador**: control total.
2. Se genera un **enlace de invitación de un solo uso** (expira en 72 h). **Cópialo y
   compártelo por un canal seguro** (no hay registro abierto ni correos automáticos).
3. La persona abre el enlace, fija su contraseña y configura su propio 2FA.

---

## 6. Mantener los datos frescos automáticamente (cron) — "tiempo casi-real"

El mapa y el directorio se actualizan solos con un **Cron Job** que vuelve a ingerir cada
pocas horas. **No hace falta abrir la Shell ni hacer nada manual**: lo programas una vez.

1. Render ➜ **New ➜ Cron Job**.
2. Conecta el **mismo repo**, **mismas variables de entorno** (`FLASK_APP`, `DATABASE_URL`,
   `SECRET_KEY`, `FLASK_ENV`). Build Command: `pip install -r requirements.txt`.
3. **Command:** `flask ingest-all`
4. **Schedule:** cada 6 horas → `0 */6 * * *` (o cada 3 h `0 */3 * * *` si lo quieres más fresco).
5. (Opcional) un segundo cron `flask export-contributions` para regenerar el export a compartir con venezuelareporta.

> **Shell vs Cron — para qué es cada uno:**
> - La **Shell** es para comandos **manuales y de una vez** (crear admin, primera carga,
>   depurar). Viene incluida en planes de pago (Starter).
> - El **Cron Job** es lo que mantiene los datos **frescos en automático** (lo que pediste:
>   que el mapa/directorio se actualicen solos). Es independiente del Web Service.
>
> **Abaratar costos:** las fuentes (USGS/GDACS/OSM) cambian cada minutos-horas, así que un
> cron cada 3–6 h da datos "casi en vivo" **sin** instancias caras ni websockets. El Cron
> Job de Render se cobra **por segundos de ejecución** (centavos/mes para un `ingest-all`
> que tarda segundos). El gasto fijo real es el Web Service Starter ($7) + la base
> ($0 mientras dure el plan Free de DB; ~$7 si la pasas a Basic para que no expire).

---

## 7. Comprar el dominio
1. Entra a tu registrador (Cloudflare / Namecheap / Porkbun).
2. Busca y compra, por ejemplo, **`redayudavenezuela.org`** (`.org` es apropiado para una iniciativa humanitaria; ~$12/año).
3. Completa la compra (datos de contacto; activa la protección de privacidad WHOIS si está gratis).

---

## 8. Conectar el dominio a Render (DNS)
1. En Render ➜ tu Web Service ➜ **Settings ➜ Custom Domains ➜ Add Custom Domain**.
2. Agrega **dos**: `redayudavenezuela.org` y `www.redayudavenezuela.org`.
3. Render te mostrará los registros DNS a crear. Típicamente:
   - **www** → un registro **CNAME** apuntando a `red-ayuda-venezuela.onrender.com`.
   - **raíz (apex)** → un **ALIAS/ANAME** (o los **A records** que Render indique). En **Cloudflare** puedes poner un **CNAME** en la raíz (CNAME flattening) apuntando a tu `.onrender.com`.
4. Ve al panel **DNS** de tu registrador y crea esos registros exactamente como los pide Render.
5. Espera la propagación (minutos; hasta 48 h). Render emite el **certificado HTTPS** (Let's Encrypt) automáticamente cuando el DNS resuelve.
6. Marca tu dominio raíz o el `www` como **principal** (redirige uno al otro en Settings).

---

## 9. Checklist final (verifica todo)
- [ ] `https://tudominio.org` carga con candado (HTTPS) verde.
- [ ] `/` muestra el inicio; `/mapa` muestra **⚠ zonas de peligro** + servicios; `/directorio` muestra conteos **reales**; `/reconocimientos` muestra unidades + perros.
- [ ] Un formulario (`/reportes/ayuda`) envía correctamente.
- [ ] Iniciaste sesión en `/cuenta/login` y **activaste 2FA** (QR); ves `/admin`.
- [ ] Migraciones aplicadas: en Shell, `flask db current` muestra la última revisión.
- [ ] El **cron** corrió al menos una vez (revisa *Logs* del cron).
- [ ] `robots.txt` accesible en `/robots.txt`.

---

## 10. Operación y seguridad
- **`SECRET_KEY`**: fuerte y secreto. Si se filtra, genera otro y reinícialo en Render.
- **No subas `.env`** ni claves al repo.
- **Backups**: el plan Basic de Postgres los incluye; en Free haz `pg_dump` manual de vez en cuando.
- **Logs**: Render ➜ tu servicio ➜ *Logs* para errores.
- **Escalar**: si crece el tráfico, sube el plan del Web Service; la app es *stateless* (todo el estado vive en Postgres).
- **Rate limiting**: hay límites por IP (login 10/min, formularios 30/h). El almacén por
  defecto es en memoria — funciona con **un** worker de gunicorn (lo normal en Starter). Si
  aumentas a varios workers/instancias, crea un **Redis** y pon `RATELIMIT_STORAGE_URI=redis://…`.
- **2FA**: obligatorio para el panel; ver §5.1. Guarda tu app autenticadora.

---

## 11. Si algo falla (problemas típicos)
- **502 / no arranca:** revisa que `Start Command` sea `gunicorn wsgi:app` y que `DATABASE_URL` esté puesto.
- **Error de migración en deploy:** el `Pre-Deploy` corre `flask db upgrade`; verifica `FLASK_APP=wsgi.py` en las env vars.
- **"SECRET_KEY debe configurarse":** falta la variable `SECRET_KEY` (la valida `ProductionConfig`).
- **Dominio sin HTTPS:** el DNS aún no propaga o el registro apunta mal; revisa en *Custom Domains* el estado (debe decir *Verified*).
- **El sitio Free "tarda en abrir":** es el *cold start* del plan Free (se durmió); sube a Starter para evitarlo.
