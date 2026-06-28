# Documentación del proyecto

Los documentos fuente viven en `docs/project/`. En caso de ambigüedad se aplica esta jerarquía:

1. **Documento Madre vigente**: visión, límites y decisiones rectoras.
2. **Security + Operations Checklist**: veto de seguridad y condición de lanzamiento.
3. **Product Requirements Document**: comportamiento y criterios de aceptación.
4. **MVP Document**: alcance funcional.
5. **Especificación Técnica**: arquitectura e implementación.
6. **AI Coding Instructions / Prompt Pack**: método incremental de desarrollo.

El documento **Plan de Expansión Operativa, Datos y Plataforma** amplía el MVP y
define el programa E0–E12. Es un plan de ejecución subordinado a los seis documentos
anteriores: no altera por sí solo sus límites, ni autoriza costos, contactos con
terceros o despliegues.

La política operativa de clasificación, fuentes, roles y aprobaciones vive en
`docs/data-governance.md` y también está subordinada a esta jerarquía.

La copia `Documento Madre del Proyecto-2.docx` fue confirmada como vigente. El informe exploratorio y la copia anterior no forman parte de la documentación canónica.

## Reglas de cambio

- Un cambio de alcance debe registrarse en `decisions.md`.
- Seguridad y privacidad prevalecen sobre conveniencia o visibilidad.
- No se agregan APIs pagadas, AI en producción, pagos, donaciones o mensajería sin aprobación explícita.
- Cada fase debe incluir pruebas y revisión de exposición de datos.
- La integración de datos externos requiere procedencia, permiso de uso, limpieza,
  revisión humana y una separación estricta entre registros privados y proyecciones
  públicas.
