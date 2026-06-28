# Gobernanza de datos y fuentes

> Estado: ratificado por el propietario en E0. Este documento no autoriza
> por sí solo contactos con terceros, scraping, servicios pagados ni publicación.

## 1. Propósito

Definir quién puede incorporar, revisar, usar y publicar información en Red de Ayuda
Venezuela. Aplica a formularios propios, APIs, feeds, archivos, organizaciones socias
y señales públicas encontradas en Internet.

En caso de conflicto prevalece la jerarquía de `docs/README.md`. Toda incorporación
mantiene el flujo obligatorio:

`origen → copia privada → normalización → control de calidad → revisión humana → proyección pública sanitizada`

## 2. Principios obligatorios

- Una fuente real no convierte automáticamente sus datos en información verificada.
- Ningún registro personal o comunitario externo se publica automáticamente.
- La procedencia original se conserva aunque el dato sea corregido, fusionado o retirado.
- La ausencia de reportes no significa ausencia de víctimas, daños o necesidades.
- Los agregados muestran unidad, territorio, período, fuente, frescura y nivel de certeza.
- Solo se recopila lo necesario para un propósito humanitario definido.
- La calidad y la seguridad prevalecen sobre la cantidad de puntos visibles en el mapa.
- Un moderador puede anular sugerencias deterministas; la decisión y el motivo quedan auditados.

## 3. Clasificación de información

### P0 — Pública agregada

Información estadística o territorial que no identifica personas: totales por zona,
brechas, cobertura, estado de servicios y recursos confirmados en unidades compatibles.
Puede publicarse únicamente desde una proyección pública aprobada.

### P1 — Pública sanitizada

Descripción de un caso aprobado, ubicación aproximada, categoría, frescura y estado de
verificación. Excluye contacto, dirección exacta, datos médicos, identidad del
reportante, evidencia privada y notas internas.

### R1 — Operativa restringida

Datos necesarios para coordinar una respuesta: ubicación más precisa, organización,
asignación, disponibilidad, evidencia y observaciones operativas. Acceso por rol,
organización y territorio; nunca se sirve desde endpoints públicos.

### R2 — Personal sensible

Teléfono, dirección exacta, identidad, información médica, datos de personas sin
contacto y cualquier detalle que pueda aumentar el riesgo de una persona. Acceso
mínimo, registro de auditoría, retención limitada y exportación excepcional.

### S1 — Secreto del sistema

Contraseñas, tokens, claves, credenciales de fuentes, secretos de sesión, copias de
seguridad y configuración privada. Nunca se almacena en Git ni se incluye en logs,
HTML, JSON o CSV de aplicación.

## 4. Roles y responsabilidades

- **Propietario del proyecto:** ratifica alcance, autoriza costos, contactos con
  terceros, acuerdos de intercambio, staging, DNS y lanzamiento.
- **Responsable de seguridad y privacidad:** puede vetar una fuente, publicación,
  exportación o lanzamiento; revisa incidentes, retención y controles.
- **Responsable de datos:** mantiene el registro de fuentes, esquema canónico,
  unidades, territorios, reglas de calidad y métricas de procedencia.
- **Administrador de plataforma:** gestiona accesos y configuración; no puede omitir
  auditoría ni controles de privacidad.
- **Revisor:** valida, sanitiza, fusiona y propone publicación dentro de su alcance.
- **Coordinador:** aprueba asignaciones y transiciones operativas; no cambia controles
  de seguridad.
- **Organización verificada:** mantiene sus recursos y acepta asignaciones según el
  acuerdo vigente; no modifica registros de otras entidades.
- **Voluntario verificado:** actualiza únicamente casos asignados dentro de su ámbito.
- **Visitante:** reporta, corrige o denuncia abuso; nunca confirma ni resuelve casos.

Una misma persona puede ejercer varios roles en el piloto, pero las acciones críticas
conservan el rol usado, fecha, motivo e historial. Cuando sea viable, publicación de
casos sensibles y exportación masiva requieren una segunda revisión.

## 5. Registro obligatorio de fuentes

Antes de escribir un conector o importar un archivo se debe registrar:

- nombre, propietario, URL y responsable interno;
- clase de fuente y método de acceso;
- licencia, permiso o acuerdo aplicable;
- propósito humanitario y categorías necesarias;
- campos recibidos, clasificación P0/P1/R1/R2/S1 y presencia de datos personales;
- frecuencia, cuota, zona, período y expectativa de frescura;
- identificador externo, estrategia de idempotencia y versión del transformador;
- reglas de retención, corrección, eliminación y suspensión;
- condiciones de publicación y atribución;
- estado de autorización y fecha de la última revisión.

## 6. Estados de una fuente

1. **Propuesta:** identificada, sin uso ni contacto autorizado.
2. **En evaluación:** revisión de términos, privacidad, utilidad y seguridad.
3. **Autorizada para staging:** puede probarse en entorno aislado y privado.
4. **Activa:** conector aprobado, monitoreado y sujeto a su frecuencia acordada.
5. **Suspendida:** se detiene por fallos, cambios de permiso, riesgo o calidad.
6. **Retirada:** no se consulta; se aplica la política de retención y corrección.

## 7. Métodos permitidos y prohibidos

Permitidos, con autorización registrada: API oficial, feed documentado, exportación de
un socio, archivo entregado para este propósito e importación manual controlada.

Requieren aprobación específica: contacto con una organización, firma de acuerdos,
autenticación en una fuente, cron de producción, almacenamiento adicional, proveedor
de mapas o cualquier servicio con costo.

Prohibidos sin una nueva decisión explícita:

- scraping indiscriminado de redes sociales, mensajería o directorios personales;
- scraping de Family Links u otros sistemas destinados a personas desaparecidas;
- eludir autenticación, robots, límites, términos o controles técnicos;
- inferir identidad, condición médica o veracidad mediante AI;
- republicar teléfonos, direcciones, fotografías o nombres personales;
- contar como corroboración dos portales que copiaron el mismo origen.

## 8. Puertas de control por conjunto de datos

### Entrada a staging

- Fuente autorizada para staging y responsable identificado.
- Esquema, licencia, clasificación y retención documentados.
- Datos de prueba sin secretos ni exposición pública.

### Entrada al repositorio privado

- Validación de tipos, tamaño, coordenadas, fechas y territorio.
- Copia original inmutable o hash verificable.
- Idempotencia, cuarentena y registro de errores.

### Entrada a revisión humana

- Normalización reproducible y valor original preservado.
- Duplicados, contradicciones, obsolescencia y sensibilidad marcados.
- Evidencia y fuentes realmente independientes distinguibles.

### Entrada a publicación

- Permiso compatible y atribución correcta.
- Decisión humana registrada.
- Proyección pública construida únicamente con P0/P1.
- Territorio y precisión seguros; frescura y certeza visibles.
- Pruebas negativas confirman que R1, R2 y S1 no aparecen en HTML, JSON, mapa,
  gráficos, caché ni exportaciones públicas.

## 9. Aprobaciones que E0 no concede

La ratificación de esta política permite diseñar las siguientes fases. No concede:

- permiso para contactar propietarios de fuentes;
- permiso para recopilar o importar datos de una fuente específica;
- presupuesto para Render, cron, almacenamiento, mapas, monitoreo o alta disponibilidad;
- autorización para activar PostGIS, cambiar Leaflet por MapLibre o desplegar;
- autorización para publicar datos personales o reducir la revisión humana.

Cada decisión se registra en `docs/decisions.md` antes de ejecutarse.

## 10. Criterios de salida de E0

- Jerarquía documental y alcance E0–E12 registrados.
- Clasificación de información y roles ratificados.
- Política de fuentes y matriz de aprobaciones ratificadas.
- `docs/operations.md` incluye controles para fuentes y datos.
- No se han creado conectores, contactos, costos ni cambios de producción.
- El propietario revisa esta fase y aprueba o solicita otra iteración.
