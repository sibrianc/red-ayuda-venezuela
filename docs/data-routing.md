# Modelo de información y enrutamiento seguro — E1

> Diseño para revisión. No habilita envío a terceros ni publicación automática.

## 1. La persona primero, no el punto del mapa

El sistema tendrá vistas complementarias y cada cifra deberá poder explicar de dónde
sale, a qué lugar y período corresponde y cuándo fue revisada:

- **Situación:** evento, alertas, daños, acceso y frescura de las fuentes.
- **Personas y protección:** casos sensibles separados de estadísticas agregadas.
- **Necesidades y brechas:** qué hace falta, cuánto, dónde, para quién y hasta cuándo.
- **Capacidad de respuesta:** recursos disponibles, comprometidos, en tránsito o fuera
  de servicio; nunca sumar promesas como inventario confirmado.
- **Directorio de servicios:** organización, servicio, cobertura, horario, estado y
  contacto público autorizado.
- **Mapa:** capas agregadas y sanitizadas; no la base privada.

### Qué verá el público

- índice consultable de fuentes con enlace, propietario y última actualización;
- hechos agregados aprobados con territorio, período, unidad y nivel de certeza;
- mapa, concentración aproximada, filtros, tablas y gráficos;
- directorio de servicios y recursos con contactos expresamente públicos;
- alertas de acceso y comunicación con sus límites claramente visibles.

La cuarentena privada contiene payloads originales, observaciones sin verificar,
direcciones exactas, contactos personales, notas internas y evidencia sensible. Es una
capa de seguridad previa a la publicación, no el producto final.

## 2. Objetos canónicos propuestos para E3

| Objeto | Propósito | Ejemplos | Privacidad inicial |
|---|---|---|---|
| `Event` | Emergencia y ventanas temporales | terremoto, réplica, activación | P0 |
| `SourceRecord` | Copia inmutable y procedencia | URL, ID externo, hash, fecha, versión | R1 |
| `Observation` | Afirmación exacta de una fuente | “12 rescatados en municipio X” | R1 hasta revisión |
| `OperationalFact` | Métrica normalizada | 12 personas, municipio X, período Y | P0 si se aprueba |
| `NeedGap` | Necesidad y déficit | 2.000 L/día faltantes de agua | P0/R1 |
| `ResourceCapacity` | Capacidad con estado | 3 excavadoras disponibles hasta 18:00 | R1; P0 agregada |
| `DirectoryEntry` | Servicio u organización | hospital, refugio, punto de agua | P0/P1 según contacto |
| `CommunicationSignal` | Anomalía o ausencia reportada | caída Internet, zona sin radio | P0/R1 |
| `PersonCase` | Caso individual | sin contacto, posible atrapamiento | R2; proyección P1 excepcional |

Toda observación conserva el valor original. Normalizar o fusionar crea una relación,
no borra el origen. Dos sitios que replican el mismo boletín cuentan como una sola
procedencia.

## 3. Catálogo mínimo de métricas

- Personas: `possibly_trapped`, `confirmed_trapped`, `rescued`, `injured`,
  `deceased`, `missing`, `no_contact`.
- Respuesta: bomberos, rescatistas USAR, equipos caninos, personal médico,
  ambulancias, excavadoras y vehículos; cada uno con `available`, `assigned`,
  `in_transit`, `needed` o `out_of_service`.
- Suministros: agua en litros/día, raciones/día, kits, medicamentos por unidad,
  camas, espacios de refugio, combustible y capacidad de transporte.
- Acceso: vía abierta, restringida, cerrada o desconocida; fuente y vigencia.
- Comunicaciones: normal, degradada, interrupción observada, sin información o
  restaurada.

No se calculará “víctimas probables” a partir de población, daño, calor del mapa o
falta de comunicación. Esas capas sirven para priorizar evaluación, no para afirmar
el estado de personas.

## 4. Alerta de zona sin comunicación

Una alerta puede nacer de una señal técnica, un reporte comunitario o un boletín. Su
estado será `advisory`, `under_review`, `corroborated` o `resolved` y mostrará:

- territorio y cobertura aproximada;
- tipo de comunicación afectada;
- inicio, última observación y fuente;
- confianza y limitaciones;
- último contacto comunitario conocido, solo de forma agregada y segura.

La corroboración requiere una segunda fuente realmente independiente o una entidad
autorizada. La alerta nunca revela contactos privados ni se transforma en conteo de
víctimas.

## 5. Enrutamiento hacia un sistema oficial o de socio

### Nivel 1 — Referencia

Mostrar el canal oficial verificado y explicar qué información tendrá que volver a
introducir la persona. Es el modo por defecto cuando no existe acuerdo técnico.

### Nivel 2 — Copia asistida

Preparar un resumen que la persona decide copiar o descargar. No abre sesión, no
simula clics y no envía datos por detrás.

### Nivel 3 — API autorizada

Solo para una implementación concreta con acuerdo, finalidad compatible y permiso de
la persona. El conector aplica lista blanca de campos, idempotencia, timeout, reintento
seguro, acuse externo y auditoría. El envío local permanece privado aunque el tercero
lo acepte.

### Nivel 4 — Intercambio entre organizaciones

Exportación o importación por lote según convenio, cifrado, alcance territorial,
retención, corrección y revocación definidos. Requiere responsable de ambas partes.

En todos los niveles:

1. guardar primero el reporte local como pendiente y privado;
2. mostrar destino, propietario, campos y finalidad;
3. obtener consentimiento específico, no una casilla genérica;
4. registrar intento, respuesta, ID externo y versión del mapeo;
5. impedir duplicados y permitir corregir o retirar cuando el acuerdo lo contemple;
6. no usar scraping, automatización del navegador ni credenciales de una persona.

## 6. Decisiones y trabajo posterior

- USGS y GDACS quedan ratificadas para staging P0 sin publicación automática.
- ReliefWeb requiere solicitar un `appname` preaprobado cuando exista correo del
  propietario; hasta entonces pueden usarse enlaces públicos, no la API de producción.
- Un acuerdo con organización socia es opcional para ampliar datos de campo, no una
  condición para indexar fuentes públicas permitidas.
- Definir responsable interno de datos y de seguridad/privacidad.
- Decidir qué contactos del directorio pueden ser públicos con consentimiento.
- Acordar umbrales y lenguaje de las alertas de conectividad.
