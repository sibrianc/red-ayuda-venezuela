# Propuesta: panel de administración y colaboradores

**Estado:** propuesta para decisión (no construido aún más allá de lo existente).
**Para:** el responsable del proyecto y personas de confianza. Acceso **hiper-privado**.

---

## 1. ¿Para qué sirve? (propósito)

El sitio público ya publica solo lo apto de forma autónoma. El panel **no** es para
operar el día a día público; es la **trastienda de confianza** para tres cosas:

1. **Velar por la calidad y la seguridad de los datos** — revisar lo que el pipeline
   automático resguarda (incompletos, posible spam/duplicado, **menores**), corregir,
   publicar u ocultar. Es el control humano sobre la automatización.
2. **Coordinar la respuesta** — una vista tipo **OCHA 3W/4W/5W** (Quién hace Qué, Dónde,
   Cuándo y para Quién): necesidades ↔ recursos, prioridades de rescate, zonas con más
   desaparecidos, brechas (necesidad sin recurso). Hoy esto vive disperso; el panel lo
   reúne para tomar decisiones.
3. **Gobernar el sistema con responsabilidad de datos** — gestionar fuentes/ingestas,
   reconocimientos, contactos verificados, exportaciones sensibles y la auditoría de
   quién hizo qué. Alineado con las *OCHA Data Responsibility Guidelines* (minimización,
   acceso por necesidad, trazabilidad).

> Principio rector: **lo público es abierto; lo sensible (PII, menores, contactos) es de
> acceso mínimo, auditado y solo para personas de confianza.**

## 2. ¿Quiénes lo usan? Roles (sobre los ya definidos)

El sistema ya define `UserRole`: ADMIN, REVIEWER, VOLUNTEER, VIEWER (los dos últimos sin
uso todavía). Propuesta de significado, inspirada en NIMS/ICS y la coordinación por
clústeres:

| Rol | Quién | Para qué |
|-----|-------|----------|
| **ADMIN** (Coordinador) | Tú | Todo: usuarios, fuentes/ingesta, reconocimientos, export sensible, configuración, auditoría. |
| **REVIEWER** (Revisor) | Confianza alta | Cola de revisión: aprobar/editar/ocultar reportes, abuso, ver coordinación. **Sin** export sensible ni gestión de usuarios. |
| **VOLUNTEER** (Colaborador) | Confianza media | Tareas acotadas: triage inicial, proponer cambios/notas, marcar duplicados/abuso — **sin** publicar ni ver PII completa. |
| **VIEWER** (Observador) | Aliados/instituciones | Solo lectura de tableros de coordinación agregados (sin PII). |

Mínimo privilegio: cada rol ve y hace **solo lo necesario**. La PII (contacto, dirección
exacta, notas médicas) se restringe a ADMIN/REVIEWER; VOLUNTEER trabaja sobre la
proyección saneada; VIEWER nunca ve PII.

## 3. Funciones por sección

**Ya existe (ADMIN/REVIEWER):** cola por estado + conteos; revisión de reporte
(estado/verificación/prioridad/público + edición de descripción + notas + historial +
duplicados + prioridad sugerida + match de recursos); cola y revisión de abuso; export
CSV (público/interno) **solo ADMIN**, a prueba de inyección CSV.

**Propuesto (por fases):**
- **Resumen operativo (4W):** necesidades vs recursos por zona y tipo, brechas, prioridades
  de rescate, zonas con más desaparecidos, frescura de datos. (Reusa `coordination_overview`.)
- **Gestión de fuentes/ingesta:** ver últimas ingestas (personas, incidentes, servicios,
  mascotas, reconocimientos), lanzar/auditar importaciones, estado de corroboración.
- **Reconocimientos y contactos:** alta/edición con atribución y fuente.
- **Cola de menores (protegida):** flujo separado y auditado; nunca sale a público.
- **Usuarios (solo ADMIN):** invitar/desactivar colaboradores, asignar rol.
- **Auditoría:** bitácora de acciones (quién aprobó/editó/exportó y cuándo).

## 4. Acceso hiper-privado y seguro (no negociable)

1. **Invitación únicamente** — sin registro público. Las cuentas las crea ADMIN
   (`flask create-admin` ya existe; añadir invitación de colaboradores).
2. **Contraseñas fuertes** (mín. 12, ya exigido) + **2FA/TOTP** para todas las cuentas del panel.
3. **Login con rate limit** (ya: 10/min → 429) y mensajes genéricos (sin enumerar usuarios).
4. **Sesiones endurecidas**: cookies `HttpOnly`+`Secure`+`SameSite`, expiración corta,
   `Cache-Control: no-store` en `/admin` y `/cuenta` (ya activo).
5. **(Opcional) Allowlist de IP** o ruta de acceso no adivinable para el panel.
6. **Auditoría** de todas las acciones sensibles (export, cambios de estado, edición de PII).
7. **Acceso por necesidad** a PII; export sensible solo ADMIN y marcado `X-Data-Classification`.
8. **HTTPS + HSTS** en producción (ya). 2FA es el añadido principal pendiente.

## 5. Plan por fases (sugerido)

- **F1 — Endurecer acceso: ENTREGADO.** 2FA/TOTP obligatorio (inscripción con QR +
  verificación, gate en `roles_required`), invitación de colaboradores (token de un solo
  uso, sin registro público, página `/admin/usuarios`) y bitácora de auditoría
  (`/admin/auditoria`: login, revisión, export, invitación, 2FA). Login con rate limit.
- **F2 — Resumen operativo (4W)** dentro del panel (necesidades/recursos/brechas/prioridades).
- **F3 — Gestión de fuentes/ingesta + reconocimientos/contactos** desde el panel.
- **F4 — Roles VOLUNTEER/VIEWER** con permisos acotados y vistas sin PII.

## Fuentes (marco)

- OCHA — *Who does What, Where, When* (3W/4W/5W): https://www.ochaopt.org/page/who-does-what-where-and-when
- OCHA — *We coordinate* (clústeres): https://www.unocha.org/we-coordinate
- OCHA Centre for Humanitarian Data — *Data Responsibility Guidelines (2025)*
- UNHCR — *Emergency Information Management Coordination*
