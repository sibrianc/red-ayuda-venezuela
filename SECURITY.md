# Política de seguridad

Esta plataforma maneja datos sensibles de personas en una emergencia. La seguridad y la
privacidad son críticas.

## Reportar una vulnerabilidad

Si encuentras una vulnerabilidad —especialmente cualquier forma de **fuga de datos
privados** (contacto del reportante, dirección exacta, notas médicas, datos de menores)—
**no abras un issue público**. Escribe en privado a:

**carlosssibrian@gmail.com**

Incluye, si puedes: pasos para reproducir, impacto y una propuesta de mitigación. Daremos
acuse de recibo lo antes posible.

## Alcance prioritario

- Exposición de campos privados en proyecciones o respuestas públicas.
- Publicación de reportes que involucran a menores.
- Sorteo de autenticación o de los controles del panel administrativo.
- Inyección (SQL, plantillas), XSS o CSRF.
- Reenvío de datos a terceros sin sanitizar.

## Buenas prácticas para despliegues

- Define `SECRET_KEY` y `DATABASE_URL` propios; nunca uses los valores de ejemplo.
- Sirve siempre por HTTPS (`ProductionConfig` fuerza cookies seguras).
- Si activas `INSTITUTION_FORWARD_ENABLED`, usa un endpoint propio y confiable: solo se
  envía la proyección pública, pero verifica el destino.

## Auditoría de seguridad (Fase 5 — antes del deploy)

Revisión defensiva del código y la configuración. Resumen para auditores y operadores.

### Verificado correcto

- **Separación público/privado.** Las proyecciones públicas (`public_report_dict`,
  `public_person_records`, mascotas, reconocimientos) nunca incluyen contacto, dirección
  exacta, notas médicas ni notas internas. Cubierto por pruebas (`test_public`,
  `test_directory_page`, `test_lost_pets`).
- **Menores.** Nunca se publican de forma automática (intake) ni aparecen en vistas
  públicas (filtro `is_minor`). Cubierto por pruebas.
- **Control de acceso.** Todas las rutas de administración usan `roles_required`
  (`@login_required` + verificación de rol → `abort(403)`). La exportación CSV es solo
  ADMIN. Cubierto por pruebas (`test_admin`).
- **CSRF.** Flask-WTF activo en todos los formularios; `form-action 'self'`.
- **XSS.** Autoescape de Jinja en todo; `|safe` solo se usa con SVG estáticos del propio
  macro de iconos (no entra dato de usuario). `script-src` **sin** `'unsafe-inline'`. No
  hay `<script>` inline ni manejadores `on*=` en las plantillas.
- **Inyección SQL.** Solo ORM SQLAlchemy parametrizado; sin SQL crudo ni `text()` con
  interpolación.
- **Open redirect.** El login no acepta `next`; el cambio de idioma usa `request.path`.
- **Cabeceras.** CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy`, `Permissions-Policy`, `object-src 'none'`, `frame-src 'none'`,
  `base-uri 'self'`; HSTS en producción; `Cache-Control: no-store` en admin/auth.
- **Secretos.** `ProductionConfig.validate()` exige `SECRET_KEY` y `DATABASE_URL` reales;
  `.env` está en `.gitignore`. Cookies de sesión `HttpOnly`+`SameSite=Lax`, `Secure` en prod.
- **Subida de archivos.** No hay; las fotos son solo enlaces https validados.
- **SSRF.** El reenvío a instituciones usa una URL fijada por el operador (off por defecto);
  las fotos se cargan en el navegador, no en el servidor.

### Hallazgos corregidos en esta fase

1. **CSP bloqueaba las fotos externas** (mascotas/reconocimientos). Se ajustó `img-src` a
   `'self' data: https:` (imágenes https inertes; nunca http; `referrerpolicy=no-referrer`
   en cada `<img>`). Se añadió `object-src 'none'` y `frame-src 'none'`.
2. **Cookie de idioma** ahora `HttpOnly` + `Secure` (en prod) + `SameSite=Lax`.

### Límite de tasa (rate limiting): implementado

Flask-Limiter por IP: **login 10/min** (anti-fuerza bruta, responde 429), **formularios
de reporte 30/hora**, **reporte de abuso 20/hora**; junto a honeypot, heurísticas
anti-spam y deduplicación. Storage en memoria por defecto (apto para un proceso/local);
en producción multi-worker usar **Redis** con `RATELIMIT_STORAGE_URI`.

### Riesgo residual / recomendaciones antes de exponer al público

- **Rate limiting en multi-worker.** Si se despliega con varios procesos, configurar
  `RATELIMIT_STORAGE_URI` apuntando a Redis (el storage en memoria no se comparte).
- **Fotos por enlace https.** Un enlace podría apuntar a una imagen externa de seguimiento
  o inapropiada; mitigado por validación de extensión, `no-referrer` y el flujo de abuso.
  Para máximo endurecimiento: alojar/proxyar imágenes propias con verificación de tipo.
- **`FLASK_ENV=production` es obligatorio en el despliegue** (lo fija `render.yaml`). Sin
  esa variable se usa la config de desarrollo (DEBUG y clave por defecto): nunca desplegar así.
- **Dependencias.** Ejecutar `pip-audit`/`safety` periódicamente y fijar versiones.

### Lista de verificación pre-deploy

1. `FLASK_ENV=production`, `SECRET_KEY` y `DATABASE_URL` propios (no los de ejemplo).
2. Servir siempre por HTTPS (cookies `Secure` + HSTS activos).
3. `flask db upgrade` y crear el administrador por consola segura.
4. Ejecutar `pytest` (todo verde) y las pruebas de humo de `docs/operations.md`.
5. Revisar que `AUTO_PUBLISH` y `INSTITUTION_FORWARD_ENABLED` estén en el valor deseado.
6. Considerar rate limiting antes de difundir el enlace públicamente.
