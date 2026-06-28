# Registro de decisiones

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
