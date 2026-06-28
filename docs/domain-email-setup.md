# Dominio, correo oficial y ReliefWeb — runbook

> Estado: **en preparación, requiere intervención del propietario**. Última revisión:
> 2026-06-28. No contiene ni debe contener contraseñas, tarjetas, OTP, códigos de
> recuperación o el correo personal de destino.

## 1. Estado verificado

- La consulta RDAP de Public Interest Registry devolvió `404 Object not found` para
  `redayudave.org` el 2026-06-28.
- No existen registros públicos NS, A ni MX para el dominio.
- Esto indica que el dominio no está registrado/configurado en este checkpoint.
- Proveedor recomendado: Cloudflare Registrar, que admite `.org`, cobra a precio de
  registro y ofrece DNS, DNSSEC, SSL/CDN y redacción WHOIS.
- Email Routing entrante está disponible en el plan gratuito. No es un buzón completo:
  reenvía el correo recibido a una dirección personal verificada.

## 2. Propiedad y seguridad de la cuenta

La cuenta Cloudflare debe pertenecer al propietario del proyecto, no a un asistente ni
a una cuenta compartida.

1. Usar un correo personal permanente como propietario de Cloudflare.
2. Crear una contraseña única en un gestor de contraseñas.
3. Activar 2FA con passkey o aplicación TOTP.
4. Guardar códigos de recuperación en el gestor de contraseñas, fuera de Git.
5. Verificar el correo de registrante exigido por ICANN.
6. Confirmar precio y renovación antes de comprar; no aceptar productos adicionales.
7. Mantener bloqueo de registrador, privacidad WHOIS y renovación automática.

## 3. Compra propuesta

- Dominio: `redayudave.org`.
- Plazo inicial: un año.
- Proveedor: Cloudflare Registrar.
- Costo: el valor exacto debe confirmarse en checkout; Cloudflare declara precio de
  costo del registro/ICANN. Cualquier pago necesita aprobación del propietario.
- No comprar variantes, hosting, certificados ni correo adicional durante este paso.

## 4. Correo oficial mínimo

Tras activar el dominio:

1. Abrir **Email → Email Routing** en Cloudflare.
2. Activar los registros MX propuestos por Cloudflare.
3. Verificar como destino el correo personal del propietario.
4. Crear `datos@redayudave.org` y reenviarlo al destino verificado.
5. Crear `seguridad@redayudave.org` para reportes de privacidad/seguridad.
6. Probar recepción desde otra cuenta y confirmar encabezados/destino.

Email Routing resuelve recepción. El envío saliente con identidad del dominio se
configurará por separado si llega a ser necesario; no se debe improvisar SMTP ni
publicar credenciales.

## 5. Solicitud de `appname` a ReliefWeb

Formulario oficial:
`https://docs.google.com/forms/d/e/1FAIpQLScR5EE_SBhweLLg_2xMCnXNbT6md4zxqIB00OL0yZWyrqX_Nw/viewform`

Campos propuestos para revisión:

- **Your name:** nombre legal del propietario.
- **Organization:** `Red de Ayuda Venezuela — https://redayudave.org`.
- **Your email address:** `datos@redayudave.org`.
- **Purpose:** `Index public humanitarian reports about the June 2026 Venezuela
  earthquake for an attributed, privacy-first public map and directory. External
  records remain under human review before publication; no personal data is requested.`
- **Preferred appname:** `RedAyudaVE-reports-A7K9`.

ReliefWeb indica que revisa solicitudes en aproximadamente dos días laborables y que
no procesa direcciones Gmail/Yahoo/Hotmail. No enviar el formulario hasta comprobar
que `datos@redayudave.org` recibe correo.

## 6. Datos que nunca se guardan en el proyecto

- contraseña o passkey de Cloudflare;
- códigos TOTP, OTP o recuperación;
- número de tarjeta, CVV o dirección de facturación;
- correo personal usado como destino de reenvío;
- cookies, sesiones o tokens de la cuenta;
- respuestas de seguridad o documentos de identidad.

Solo se documentan proveedor, dominio, direcciones públicas por función, estado de
verificación y referencias a variables de entorno cuando correspondan.

## 7. Checklist de finalización

- [ ] Cuenta Cloudflare creada y correo de cuenta verificado.
- [ ] Precio mostrado y compra aprobada por el propietario.
- [ ] `redayudave.org` registrado a nombre del propietario.
- [ ] 2FA, recuperación, bloqueo, privacidad WHOIS y renovación revisados.
- [ ] Email Routing activado.
- [ ] `datos@redayudave.org` recibe mensajes.
- [ ] Solicitud de ReliefWeb revisada y enviada por el propietario.
- [ ] Respuesta/appname registrada sin secretos en `docs/source-register.md`.
