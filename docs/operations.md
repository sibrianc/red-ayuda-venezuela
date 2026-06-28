# Operación, seguridad y lanzamiento

## Antes de incorporar una fuente externa

- Aplicar `docs/data-governance.md` y registrar propietario, licencia, propósito,
  clasificación, frecuencia, retención y responsable interno.
- Confirmar en `docs/source-register.md` y en `DataSource` que el estado sea
  `authorized_staging` o `active`, con permiso, fecha de autorización y revisión
  vigentes. El código debe rechazar cualquier otro estado.
- Guardar solo el nombre de la variable de entorno de una credencial; nunca su valor
  en base de datos, Git, documentación, logs o capturas.
- No contactar organizaciones, autenticar fuentes, importar datos ni crear servicios
  con costo sin la aprobación específica correspondiente.
- Probar primero en staging con datos privados, límites de tamaño, timeout,
  idempotencia, cuarentena y métricas de ejecución.
- Preservar origen, timestamp, hash/versión y transformaciones aplicadas.
- Mantener todo registro externo privado hasta completar limpieza y revisión humana.
- Publicar únicamente una proyección P0/P1 aprobada; nunca el payload original.

## Revisión horaria de ingestión

- Confirmar que solo se ejecutó una instancia por fuente y que los reintentos no
  produjeron duplicación acumulativa.
- Revisar fuentes fallidas, cambios de esquema, cuotas, payloads en cuarentena y datos
  obsoletos o contradictorios.
- Verificar que la fuente conserva permiso vigente y que la hora de actualización es
  visible para operaciones.
- Suspender el conector ante pérdida de autorización, filtración, contenido hostil o
  degradación material de calidad.
- La ejecución horaria puede crear candidatos privados; nunca publica casos por sí sola.

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
2. Activar modo ligero, recargar el mapa y confirmar que aparece el listado accesible
   sin descargar teselas; desactivarlo y confirmar que el mapa vuelve a funcionar.
3. Enviar un reporte y confirmar que queda pendiente y privado.
4. Confirmar que un visitante no puede verlo ni entrar a `/admin`.
5. Iniciar sesión, revisar, editar descripción pública y aprobar.
6. Confirmar que solo entonces aparece en inicio, listado y mapa.
7. Verificar manualmente que no aparecen teléfono, dirección exacta, notas médicas o internas.
8. Reportar abuso y resolverlo desde la cola administrativa.

## Respuesta operativa

- Revisar diariamente pendientes, críticos, abuso, duplicados y casos sin actualizar.
- No registrar información sensible en logs ni herramientas de soporte.
- Ante una filtración, ocultar el reporte, preservar auditoría, rotar accesos y documentar el incidente.
- Ante una migración fallida, detener escrituras, restaurar backup si es necesario y usar el downgrade revisado.
- Ante una fuente comprometida o incorrecta, suspenderla, conservar evidencia,
  identificar registros derivados, retirar proyecciones afectadas y documentar la
  corrección sin borrar silenciosamente el historial.

## Cierre de emergencia

- Pausar formularios si ya no se aceptan reportes.
- Ocultar o anonimizar información que ya no deba ser pública.
- Revocar accesos temporales y guardar un backup protegido.
- Documentar retención, correcciones y solicitudes de eliminación.
