# Operación, seguridad y lanzamiento

## Antes de cada deploy

- Ejecutar todas las pruebas y revisar la migración pendiente.
- Confirmar `FLASK_ENV=production`, `SECRET_KEY` y `DATABASE_URL`.
- Confirmar que debug está apagado y HTTPS activo.
- Revisar que no existan secretos en Git o logs.
- Hacer backup antes de migraciones relevantes.
- Verificar que reportes pendientes no sean públicos.
- Probar `/mapa/data` y exportaciones con cuentas de permisos distintos.

## Prueba de humo

1. Cargar inicio, formularios, reportes, mapa y páginas de error.
2. Enviar un reporte y confirmar que queda pendiente y privado.
3. Confirmar que un visitante no puede verlo ni entrar a `/admin`.
4. Iniciar sesión, revisar, editar descripción pública y aprobar.
5. Confirmar que solo entonces aparece en listado y mapa.
6. Verificar manualmente que no aparecen teléfono, dirección exacta, notas médicas o internas.
7. Reportar abuso y resolverlo desde la cola administrativa.

## Respuesta operativa

- Revisar diariamente pendientes, críticos, abuso, duplicados y casos sin actualizar.
- No registrar información sensible en logs ni herramientas de soporte.
- Ante una filtración, ocultar el reporte, preservar auditoría, rotar accesos y documentar el incidente.
- Ante una migración fallida, detener escrituras, restaurar backup si es necesario y usar el downgrade revisado.

## Cierre de emergencia

- Pausar formularios si ya no se aceptan reportes.
- Ocultar o anonimizar información que ya no deba ser pública.
- Revocar accesos temporales y guardar un backup protegido.
- Documentar retención, correcciones y solicitudes de eliminación.
