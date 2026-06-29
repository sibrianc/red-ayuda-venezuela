# Contribuir a Red de Ayuda Venezuela

¡Gracias por querer ayudar! Este proyecto es software humanitario: prioriza salvar
vidas y proteger a las personas por encima de cualquier otra cosa. Lee estas reglas
antes de enviar cambios.

## Reglas de datos (no negociables)

1. **Solo datos reales.** Nunca presentes datos inventados como reales. Si necesitas
   datos de ejemplo, márcalos claramente como muestra (`source_slug = "sample"`).
2. **Nunca expongas datos privados.** Contacto del reportante, dirección exacta y
   notas médicas/internas jamás aparecen en proyecciones públicas. Usa
   `public_report_dict` / `public_*` y respeta la separación público/privado.
3. **Menores fuera del flujo público.** Los reportes que involucran a un menor nunca
   se publican automáticamente.
4. **Atribuye las fuentes.** Toda información de cara al público debe poder rastrearse
   a su fuente.
5. **Respeta los controles de acceso.** No sortees un 403 ni accedas a una API
   restringida; usa los canales de autorización (`docs/`, registro de fuentes).

## Pipeline autónomo

La plataforma puede operar **sin revisión humana** (`AUTO_PUBLISH=true`): los reportes
limpios y completos se publican solos y los que fallan la verificación automática
(`app/services/intake.py`) quedan en cola. La cola de revisión y el panel admin siguen
disponibles para quien se sume. Cualquier cambio al pipeline debe mantener intactas las
reglas de datos de arriba.

## Entorno de desarrollo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # ajusta SECRET_KEY y DATABASE_URL
flask db upgrade
flask run
```

## Antes de abrir un Pull Request

- `python -m compileall -q app` (sin errores de sintaxis).
- `python -m pytest -q` (toda la suite en verde). Agrega pruebas para lo que cambies.
- Escribe el código y los comentarios en el idioma y estilo del archivo que tocas.
- Commits pequeños y descriptivos. Un PR = un cambio coherente.

## Cómo ayudar

- Revisa los `issues` etiquetados como `good first issue`.
- Aporta contactos/links **verificados** de instituciones o unidades de rescate (con su
  fuente) para `app/services/contacts.py`.
- Mejora la limpieza/verificación automática de datos.
- Traduce o mejora accesibilidad.

Al contribuir aceptas que tu aporte se publique bajo la licencia MIT del proyecto.
