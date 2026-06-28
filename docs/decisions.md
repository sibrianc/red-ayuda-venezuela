# Registro de decisiones

## 2026-06-28 — Fase A.1, directorio de servicios real (OpenStreetMap)

- Arranca la expansión de élite (ver investigación de estándares abajo). El propietario
  eligió empezar por la **Fase A — modelo operativo + datos reales** para que el mapa nazca
  vivo. Primer corte: el **directorio de servicios**, la prioridad de personas.
- Fuente nueva: **OpenStreetMap vía Overpass API** (datos abiertos ODbL, gratis, sin clave).
  Trae hospitales, clínicas, farmacias, estaciones de bomberos, policía, refugios, centros
  comunitarios y puntos de agua dentro del recuadro de Venezuela. Esquema verificado contra
  el endpoint en vivo (nodos con lat/lon, vías con center, tags).
- Modelo nuevo `DirectoryEntry` (objeto canónico DirectoryEntry de `data-routing.md`,
  inspirado en OCHA 5W y EDXL-HAVE). Migración `c3d4e5f6a7b8`. Son instalaciones públicas:
  nombre, dirección y contacto son información pública (distinto de los reportes de
  personas, que siguen privados).
- Conector `parse_overpass` + `ingest_directory` (dedup idempotente por origen),
  comando `flask ingest-directory`. 6 pruebas nuevas (55 en total), sin deriva.
- Decisión de enfoque de datos reales: el directorio se llena con OSM ahora ($0); las
  cifras operativas (rescatados, bomberos, suministros) llegan después de ReliefWeb/curación;
  las zonas sin comunicación, de IODA. Sin scraping de redes.

## 2026-06-28 — Investigación de estándares de respuesta a desastres (primer mundo)

Para la expansión de élite se investigaron y adoptaron como referencia: **Google Person
Finder / PFIF** (registro interoperable de personas), **FEMA NIMS Resource Typing**
(taxonomía de recursos: excavadoras, caninos, rescatistas), **EDXL-HAVE / EDXL-RM**
(capacidad hospitalaria y mensajería de recursos), **OCHA 5W + HXL** (directorio y brecha
necesidad-vs-capacidad), **INSARAG** (sectorización y conteo de rescatados/fallecidos/sin
localizar) e **IODA / NetBlocks** (detección de zonas sin comunicación). Estos estándares
mapean 1:1 a los objetos canónicos ya definidos en `data-routing.md`. Lección de AfetHarita
(Turquía 2023): no depender de scraping de redes sociales.

## 2026-06-28 — E3.3, corrección de enfoque: SOLO el terremoto de Venezuela

- Corrección pedida por el propietario: el proyecto es para **un terremoto en Venezuela**
  (hace ~4 días), no un panel global multi-amenaza. Inundaciones, ciclones, volcanes,
  sequías e incendios del mundo son **ruido** y no deben recopilarse.
- El pipeline gana filtros `event_types` (p. ej. `{"earthquake"}`) y `since` (ventana
  temporal). El CLI ahora **por defecto** ingiere solo terremotos, solo en Venezuela:
  `flask ingest-usgs` y `flask ingest-gdacs` están enfocados; se amplía a propósito con
  `--all-world` / `--all-hazards` / `--since-days`.
- GDACS se conserva pero **filtrado a terremotos**: aporta el nivel de alerta oficial y la
  estimación de impacto de ESTE sismo para Venezuela, no desastres ajenos.
- "Masivo" se redefine correctamente: el volumen útil son las **réplicas (aftershocks)** del
  sismo en la región, que son cientos o miles, más la respuesta humanitaria — no catástrofes
  no relacionadas. Demo: de 1.380 eventos globales mezclados, el enfoque deja 300 réplicas
  de Venezuela en la ventana. 49/49 pruebas.

## 2026-06-28 — E3.2, segunda fuente (GDACS) y pipeline multi-amenaza

- Se agrega **GDACS** (Naciones Unidas / Comisión Europea) como segunda fuente real,
  demostrando que el motor es **agnóstico a la fuente**: el mismo pipeline limpia,
  deduplica y filtra eventos de cualquier conector. Responde a la pregunta del propietario
  de si se puede recopilar de otras plataformas (sí, vía sus feeds/APIs públicos).
- El esquema GDACS GeoJSON se **verificó contra el endpoint en vivo** antes de programar
  (no se adivinó). Es multi-amenaza: terremotos, inundaciones, ciclones, volcanes,
  incendios y sequías.
- `IngestedEvent` se extiende con campos genéricos multi-amenaza: `hazard_code`,
  `severity_value`, `severity_text`, `country`. Migración `b2c3d4e5f6a7`, sin deriva. El
  conector USGS se actualiza para poblarlos también (consistencia entre fuentes).
- Conector GDACS: maneja geometría `Point` y centroide aproximado de `Polygon`, fechas ISO
  a UTC, mapeo de códigos de amenaza a tipos legibles e identidad estable
  `eventtype+eventid`. Comando `flask ingest-gdacs`.
- Distinción de automatización registrada: la **ingesta** se puede automatizar con cron
  local ($0) o en la nube (requiere deploy y costo). La **publicación** de fuentes
  autoritativas de dominio público (USGS/GDACS) puede ser automática con atribución y
  etiqueta de "no verificado localmente"; los **reportes de personas** siempre requieren
  revisión humana. No se hace scraping de webs arbitrarias ni de redes sociales (regla del
  proyecto, además de términos de servicio y privacidad).
- Validación: 47/47 pruebas. Demo unificada de 2.000 eventos (USGS+GDACS, 6 tipos de
  amenaza, 494 en región): idempotente (0 nuevos al re-correr). Sin dependencias ni costo.

## 2026-06-28 — E3.1, motor de ingesta masiva (USGS), local y sin costo

- Se construye el **primer motor de recopilación real** en respuesta a la prioridad del
  propietario: la plataforma debe recopilar, limpiar y filtrar datos **de forma masiva**,
  no manejar un puñado de reportes manuales. Hasta ahora las fuentes solo existían como
  metadatos en el registro; nada descargaba ni procesaba datos.
- Conector USGS (feeds GeoJSON, dominio público) con **librería estándar** (urllib + json):
  cero dependencias nuevas, cero costo, corre en local. El *fetch* de red se separa del
  *parseo* para que las pruebas no toquen Internet.
- Modelos canónicos nuevos: `SourceRecord` (copia cruda inmutable + procedencia, capa de
  auditoría) e `IngestedEvent` (hecho normalizado, limpio y deduplicado; realiza el objeto
  `Event` del modelo de datos). Migración `a1b2c3d4e5f6`, sin deriva.
- Pipeline determinista: limpieza/validación, normalización, **deduplicación idempotente**
  por `(source_slug, external_id)` + `content_hash`, y filtros de magnitud y región
  (recuadro de Venezuela). Re-correr la ingesta no crea duplicados.
- `IngestedEvent` es una **capa interna saneada; NO se publica automáticamente** y todavía
  no se expone en ninguna vista pública/JSON/mapa. Mostrar agregados al público será un
  paso aparte con su propia puerta de revisión y atribución. Se respeta la regla de no
  autopublicar.
- Comandos: `flask ingest-usgs` (descarga + procesa + reporta estadísticas) y
  `flask ingest-stats` (volumen acumulado). Pruebas nuevas: 9 (43 en total). Sin AI, sin
  servicios pagados, sin contacto con terceros.
- Pendiente inmediato del frente de datos: conectores GDACS y un índice de ReliefWeb por
  enlaces públicos; luego la puerta de publicación de agregados y una capa de mapa.

## 2026-06-28 — E2.1, tablero público y modo ligero real

- El inicio deja de presentarse principalmente como una colección de formularios y se
  convierte en un tablero público de situación. Los formularios permanecen como apoyo
  secundario.
- Las métricas se calculan exclusivamente desde reportes `approved` y `is_public`; no
  se muestran estimaciones inventadas ni registros pendientes.
- El modo ligero es una preferencia local y reversible. Conserva contenido, filtros y
  listados, elimina decoración costosa y evita descargar teselas del mapa.
- El estado de fuentes distingue “preparada para staging” de “conectada/verificada”
  para no aparentar integraciones que todavía no existen.
- Esta iteración no añade dependencias, servicios, credenciales ni costos.

## 2026-06-28 — Desarrollo sin costo y cierre de E1

- El propietario decide continuar sin comprar dominio, correo, hosting, cron ni otros
  servicios. Cloudflare, `redayudave.org` y el `appname` de ReliefWeb quedan diferidos.
- El trabajo seguirá localmente con SQLite, Flask y servicios públicos gratuitos que
  no exijan credenciales o contratación.
- Los gastos se evaluarán después de disponer de un demo/staging revisable, con
  presupuesto separado y aprobación explícita antes de cualquier compra.
- E1 queda aprobada con USGS y GDACS autorizadas solo para staging P0 y sin conectores
  activos. Se autoriza iniciar E2.

## 2026-06-28 — E1 adopta una estrategia pública primero

- El propietario aclara que actúa como desarrollador independiente y que la plataforma
  debe indexar información pública dispersa; no se condicionará el inicio a fuentes
  privadas ni a una alianza institucional.
- USGS y GDACS quedan autorizadas para staging P0, sin conectores activos, publicación
  automática ni inferencias sobre víctimas.
- Los acuerdos con organizaciones siguen siendo valiosos, pero dejan de ser la puerta
  de salida de E1. Cada API autenticada o conjunto privado requerirá permiso propio.
- “Privado” describe la cuarentena y revisión de datos personales o no verificados, no
  el sitio final. Los agregados aprobados, filtros, directorio, gráficos y mapa serán
  públicos.

## 2026-06-28 — E1, registro y límites de fuentes

- Se separan señales automáticas, hechos operativos y casos de personas; una señal de
  daño o conectividad nunca se convierte en conteo de víctimas.
- El registro técnico almacena permiso, clasificación, frecuencia, retención,
  responsable y referencia de secreto, pero nunca credenciales ni payloads.
- Family Links queda como canal de referencia, no como fuente de ingestión.
- El enrutamiento a sistemas oficiales o de socios empieza por referencia o copia
  asistida. Un envío por API exige acuerdo, consentimiento específico, minimización,
  idempotencia, acuse y auditoría.
- Ninguna fuente queda activa en E1. La puerta de salida requiere ratificar una fuente
  oficial para staging y obtener permiso verificable de una fuente socia.

## 2026-06-28 — Iteración E0.1 de calidad visual antes de E1

- Por decisión del propietario se adelanta una base de calidad visual y UX antes de
  comenzar E1; no se considera aceptable conservar temporalmente coordenadas manuales,
  un formulario extenso o un mapa meramente básico.
- Los cuatro formularios conservan el mismo modelo y flujo privado, pero se presentan
  como un proceso guiado de tres pasos con campos opcionales progresivos.
- La geolocalización solo se solicita por acción explícita del usuario. La precisión
  original permanece privada y la proyección pública redondea coordenadas antes de
  llegar a HTML, JSON o mapa.
- El mapa continúa usando Leaflet + OpenStreetMap, sin nuevas dependencias ni costos,
  pero incorpora filtros, panel accesible, métricas y concentración aproximada.
- Esta iteración establece una línea visual profesional; no sustituye el alcance futuro
  de E2 ni la arquitectura geoespacial avanzada prevista para E9.
- El propietario revisó la demostración local y aprobó el cierre de E0/E0.1 para
  continuar con E1.

## 2026-06-28 — Plan de expansión operativa, datos y plataforma

- Se incorpora `docs/project/07 - Plan de Expansion Operativa, Datos y Plataforma.docx`
  como plan de ejecución subordinado a los seis documentos rectores.
- La expansión se divide en E0–E12 y cubre fuentes autorizadas, ingestión horaria,
  limpieza determinista, procedencia, organizaciones, recursos, asignaciones,
  dashboards y un mapa operativo avanzado.
- El lanzamiento deberá comenzar con el universo amplio de datos reales que esté
  autorizado y disponible, no con datos decorativos. Los registros externos siguen
  siendo privados hasta completar los controles de licencia, privacidad, limpieza y
  revisión aplicables.
- “Mapa vivo” significa refresco frecuente de agregados aprobados y trazables; no
  seguimiento GPS de víctimas ni publicación automática.
- Se mantiene la prohibición de AI en producción y de votos públicos para confirmar,
  priorizar o resolver incidentes.
- MapLibre, PostGIS, servicios de teselas, cron, almacenamiento, fuentes externas y
  cualquier costo o contacto con terceros requieren la aprobación específica indicada
  en el plan antes de implementarse.

## 2026-06-28 — Repositorio, revisión y handoff

- Repositorio publicado **privado** en GitHub como `sibrianc/red-ayuda-venezuela`, rama `main` (datos humanitarios sensibles).
- `git push` usa el token del CLI `gh` como credential helper: no requiere código 2FA.
- Revisión profunda de infra/código/lógica/flujo: sin hallazgos críticos. Único bug corregido: CSP bloqueaba los íconos de Leaflet (`b487bd7`).
- No se agregó rate limiting (no requerido por el MVP según el Security Checklist).
- Deploy en Render (Fase 14) queda pendiente de aprobación explícita del costo.
- Se añade `docs/seguimiento.md` como documento de handoff vivo.

## 2026-06-27 — Documento rector

`Documento Madre del Proyecto-2.docx` se reconoce como Documento Madre vigente, aunque su contenido coincida con la copia anterior.

## 2026-06-27 — Arquitectura del MVP

- Flask modular con app factory y Blueprints.
- PostgreSQL en producción; SQLite solo para pruebas aisladas.
- Jinja y JavaScript sin framework frontend.
- Leaflet y OpenStreetMap; el mapa se carga únicamente en su página.
- IDs internos nunca se usan como identificadores públicos.

## 2026-06-27 — Privacidad

- Estado inicial `pending`; visibilidad inicial falsa.
- Aprobar y publicar son decisiones explícitas y separadas.
- Los borradores locales requieren activación del usuario y excluyen campos sensibles.
- La automatización solo sugiere; una persona conserva la decisión final.
