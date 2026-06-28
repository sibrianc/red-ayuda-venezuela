# Registro de fuentes externas — E1

> Revisión: 2026-06-28. Estado de la fase: **inventario técnico completo; USGS y
> GDACS autorizadas solo para staging P0**. No hay conectores, cron, publicación ni
> contacto con terceros activos. Los estados se rigen por `data-governance.md`.

## 1. Resultado de la investigación

No existe una API pública única que entregue en tiempo real personas atrapadas,
rescatadas, rescatistas disponibles, maquinaria, suministros y brechas. El producto
debe unir tres clases de información sin confundirlas:

1. **Señales automáticas públicas:** sismos, alertas, conectividad, cartografía y
   productos satelitales. Describen contexto; no prueban víctimas.
2. **Hechos operativos:** cifras y brechas de boletines oficiales, clústeres y socios.
   Conservan territorio, período, unidad, procedencia y frescura.
3. **Casos de personas:** información sensible que exige acuerdo, minimización y
   revisión humana. Nunca se extrae de Family Links ni de redes sociales.

La ejecución cada hora será una frecuencia de **consulta**, no una garantía de que la
fuente cambió ni permiso para publicar automáticamente.

## 2. Inventario priorizado

| ID | Fuente y propietario | Aporta | Acceso / cadencia de consulta propuesta | Datos / permiso | Estado E1 y decisión |
|---|---|---|---|---|---|
| S-001 | [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) | Evento, magnitud, profundidad, hora y geometría sísmica | GeoJSON oficial; consultar cada 5 min | P0; datos USGS generalmente de dominio público, con atribución y avisos por ítem | **Autorizada para staging.** Contexto sísmico, nunca conteo de personas. Sin conector activo. |
| S-002 | [GDACS](https://www.gdacs.org/feed_reference.aspx), ONU/Comisión Europea | Alertas, severidad y metadatos de desastre | Feed público; origen se actualiza aprox. cada 6 min; consultar cada 10 min | P0; términos y descargo GDACS | **Autorizada para staging.** Mostrar incertidumbre; no sustituye autoridades. Sin conector activo. |
| S-003 | [ReliefWeb API](https://apidoc.reliefweb.int/endpoints), OCHA | Informes curados, fuentes y cronología | API oficial; consultar 60 min | Metadatos P0; texto/hechos quedan R1; exige `appname` preaprobado | **En evaluación.** No pedir `appname` ni activar hasta contar con correo del propietario. |
| S-004 | [IFRC GO](https://goadmin.ifrc.org/docs/) | Emergencias, operaciones, financiación y beneficiarios publicados | API pública; consultar 60 min | P0/R1 según campo; verificar términos y granularidad | **En evaluación.** No asumir que contiene inventario local actualizado. |
| S-005 | [HDX HAPI](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/coordination_and_context/) y datasets HDX | Presencia operacional, límites, población y datasets humanitarios | API/dataset; diario o según actualización de origen | Licencia por dataset; P0/R1 | **En evaluación.** La presencia 3W/4W puede ser trimestral o irregular; mostrar fecha. |
| S-006 | [Copernicus EMS Rapid Mapping](https://mapping.emergency.copernicus.eu/about/how-to-harvest-cems-mapping-data/emergency-response-data/) | Áreas de interés, productos y capas de daño | API/ArcGIS/descarga; 30–60 min solo si existe activación | P0; atribución/licencia del producto | **En evaluación.** Daño probable requiere validación de campo; no localiza víctimas. |
| S-007 | [HOT / OpenStreetMap](https://docs.hotosm.org/diagrams/) | Vías, edificios, hospitales, estaciones y base cartográfica | API/export; diario o por campaña | ODbL y atribución; P0 | **En evaluación.** Directorio físico, no prueba personal, horario ni disponibilidad actual. |
| S-008 | [IODA](https://ioda.inetintel.cc.gatech.edu/about), Georgia Tech | Señales macroscópicas de interrupción de Internet | API de investigación; proponer 15 min | P0 agregado; revisar términos/cuotas | **En evaluación.** Etiquetar “anomalía de conectividad”; nunca inferir víctimas. |
| S-009 | [Cloudflare Radar Outage Center](https://developers.cloudflare.com/radar/investigate/outages/) | Interrupciones por territorio/ASN, alcance y causa publicada | API con token; proponer 15 min | P0; revisar cuenta, términos, cuota y costo | **Propuesta.** No solicitar token hasta aprobación específica. |
| S-010 | [Logistics Cluster — Venezuela](https://logcluster.org/en/where-we-work/ven), WFP/IASC | Coordinación, acceso, logística, brechas, documentos y operación del terremoto 2026 | Metadatos, enlaces y documentos públicos; revisión cada 60 min | P0/R1; respetar derechos de cada documento | **Descubrimiento público permitido.** Indexar título, fecha, fuente y enlace; extracción de hechos queda privada y humana. El contacto es opcional. |
| S-011 | [WHO HeRAMS](https://www.who.int/initiatives/herams) | Operatividad y disponibilidad de servicios/recursos de salud | Reportes/API según implementación nacional | P0/R1; acceso y permiso dependen del proyecto | **Propuesta.** Confirmar si existe implementación/dataset autorizado para Venezuela. |
| S-012 | INSARAG ICMS / Virtual OSOCC | Equipos USAR, despliegues, sitios y coordinación | Sistema restringido por rol | R1/R2; acuerdo y acceso formal | **Propuesta restringida.** Prohibido raspar o eludir autenticación. |
| S-013 | [ICRC Family Links](https://familylinks.icrc.org/es/normas-de-privacidad) | Canal especializado para restablecer contacto familiar | Referencia/enlace únicamente | R2; consentimiento y reglas estrictas | **Solo referencia.** Prohibida la ingestión, copia o publicación de personas. |
| S-014 | Protección Civil, FUNVISIS, bomberos, alcaldías y autoridades venezolanas | Boletines, rescate, víctimas, capacidades y cierres oficiales | Fuente específica aún no verificada; captura manual controlada o API formal | P0/R1/R2 según boletín | **Descubrimiento pendiente.** No inventar API ni usar cuentas no verificadas. |
| S-015 | ONG, iglesias, redes vecinales y organizaciones de rescate verificadas | Necesidades, recursos, directorio, personal y actualizaciones de campo | Exportación/API/archivo de socio | R1/R2; acuerdo, contacto y esquema obligatorios | **Socio pendiente.** Ninguna organización ha sido contactada o autorizada. |
| S-016 | [KoboToolbox API v2](https://support.kobotoolbox.org/api.html) / [Ushahidi API v5](https://docs.ushahidi.com/v3-ushahidi-platform-rest-api-documentation/v5/posts) de un socio | Intercambio estructurado y acuse de recibo | API autenticada de una implementación concreta | R1/R2; contrato, token y permisos por proyecto | **Patrón de integración, no fuente.** Solo con dueño del sistema y consentimiento. |

## 3. Cobertura por necesidad crítica

| Necesidad | Fuentes candidatas | Lo que falta para considerarla operativa |
|---|---|---|
| Evento sísmico y alertas | USGS, GDACS | Autorizar staging y atribución. |
| Personas atrapadas, rescatadas, heridas o fallecidas | Autoridades, INSARAG, socio de campo, boletines ReliefWeb | Acuerdo o fuente oficial específica; definición de período y eliminación de duplicados. |
| Personas desaparecidas o sin contacto | Formulario privado, socio especializado, referencia Family Links | Protocolo R2, consentimiento, retención y equipo de revisión. |
| Bomberos, rescatistas, caninos, ambulancias y maquinaria | INSARAG, autoridades, organizaciones verificadas | Datos autorizados de capacidad, disponibilidad y turno; no existe feed público general. |
| Agua, comida, medicinas, refugio y transporte | Logistics Cluster, IFRC GO, HDX, socio de campo | Unidades compatibles, inventario vs. promesa, ubicación, período y propietario del recurso. |
| Hospitales y capacidad sanitaria | WHO HeRAMS, autoridades sanitarias, OSM como directorio base | Dataset venezolano vigente y autorización; OSM no confirma capacidad. |
| Acceso vial y daño | Copernicus EMS, Logistics Cluster, HOT/OSM, reportes revisados | Activación/producto vigente y validación de campo. |
| Zona sin comunicación | IODA, Cloudflare Radar, reportes comunitarios y autoridad | Umbrales, cobertura y corroboración; nunca traducir señal en número de víctimas. |
| Directorio de atención | OSM, autoridades y socios | Consentimiento para contacto público, horario, servicio, cobertura y fecha de verificación. |

## 4. Campos obligatorios del registro técnico

El modelo `DataSource` registra propietario, URLs, clase, método, permiso, propósito,
categorías, presencia de PII, clasificación máxima, frecuencia, cuota, retención,
atribución, versión de esquema, responsable y fechas de revisión/autorización. Solo
guarda el **nombre** de la variable de entorno de una credencial; nunca su valor.

Los controles de `app/ingestion/registry.py` rechazan una fuente propuesta,
suspendida o sin permiso/revisión. Los conectores y snapshots pertenecen a E4.

## 5. Puerta de salida E1

- [x] Inventario, categorías, riesgos y cadencias documentados.
- [x] Registro técnico y migración creados sin credenciales.
- [x] Pruebas negativas para fuentes no autorizadas.
- [x] Una fuente oficial pública ratificada para staging: USGS.
- [x] Una fuente humanitaria pública ratificada para staging: GDACS.

E1 queda técnicamente lista para revisión del propietario. Los acuerdos privados o de
socios pueden ampliar calidad y cobertura, pero no bloquean el inicio con fuentes
públicas. Cada nueva fuente mantiene su propia autorización.

El borrador de solicitud a la primera fuente socia candidata vive en
`docs/outreach/logistics-cluster-draft.md`. Es opcional y no se ha enviado.
