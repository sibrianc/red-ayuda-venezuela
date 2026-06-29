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
