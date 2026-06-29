# Borrador — Solicitud de intercambio de datos de personas (reunificación)

> Para enviar a plataformas ciudadanas de búsqueda (Venezuela Te Busca, CIVIS, etc.).
> Objetivo: obtener una **exportación o feed** (JSON/CSV/PFIF) de los reportes públicos
> de personas, para indexarlos también en Red de Ayuda Venezuela y ayudar a más familias
> a encontrar a los suyos. NO se piden datos privados ni se hace scraping. **No enviado.**

## Por qué la vía limpia (no scraping)

`venezuelatebusca.com/robots.txt` permite la recolección para **búsqueda** (`search=yes`),
pero el sitio **no expone un API/JSON público** estable. En vez de hacer ingeniería inversa
frágil de su frontend, pedimos una **exportación oficial**: es más sólido, respetuoso y
evita datos obsoletos. La infraestructura para ingerirla ya está lista
(`flask import-persons-json <archivo|URL>` y `flask import-pfif`).

## Contactos identificados

- **Venezuela Te Busca** → creadora **Julia Alessandra Mariano**, en redes **@juliaamariano**
  (Instagram). Es el canal público para escribirle (la plataforma no publica un correo).
- **CIVIS Venezuela**, **Desaparecidos Terremoto Venezuela** → buscar su cuenta oficial en
  Instagram/X o el "Contacto" de su web y escribirles igual.

## Versión corta para DM (Instagram a @juliaamariano)

> Hola Julia 👋 Soy Carlos, desarrollador independiente. Construí **Red de Ayuda Venezuela**,
> un mapa y directorio público para reunificación tras el terremoto, y admiro lo que hicieron
> con Venezuela Te Busca. ¿Sería posible que me compartan una **exportación (JSON/CSV)** de los
> reportes **públicos**? La indexaría **con atribución a ustedes y enlace a su ficha**, marcada
> como "reporte ciudadano, no verificado", y **excluyendo menores**. La idea es sumar esfuerzos
> para que más familias encuentren a los suyos. Mi correo: **carlosssibrian@gmail.com**. ¡Gracias!

## Mensaje largo (correo, una vez en contacto)

Asunto: Intercambio de datos para reunificación familiar — terremoto de Venezuela

Hola [nombre/equipo]:

Soy un desarrollador independiente que construyó **Red de Ayuda Venezuela**, una plataforma
pública para que familias y rescatistas encuentren personas, servicios y zonas afectadas
tras el terremoto del 24 de junio. Vimos su gran trabajo en [plataforma] y queremos
**sumar esfuerzos, no duplicarlos**.

¿Sería posible que nos compartan una **exportación o feed** (JSON, CSV o PFIF) de los
reportes **públicos** de personas que ya publican? La indexaríamos en nuestro directorio
**con atribución a [plataforma] y enlace a su ficha original**, claramente marcada como
"reporte ciudadano, no verificado", y **excluyendo a menores** de las vistas públicas por
protección. El objetivo es que más gente encuentre a sus seres queridos.

Por supuesto, respetaremos cualquier término que indiquen (frecuencia, campos, atribución,
retiro de registros). Si prefieren, podemos también enviarles nuestros reportes para que
los integren. Gracias por lo que hacen.

Carlos Sibrián · carlosssibrian@gmail.com · Red de Ayuda Venezuela

---

### Cómo enviarlo (lo haces tú; yo no puedo enviar correos)

1. Encuentra el contacto de la plataforma (en su web suelen tener correo, formulario o
   redes; p. ej. el pie de página o "Contacto" de venezuelatebusca.com).
2. Copia el mensaje de arriba, pégalo en Gmail desde **carlosssibrian@gmail.com** y envíalo.
3. Cuando respondan con un archivo o enlace de exportación, córrelo con
   `flask import-persons-json` o `flask import-pfif` y entran los nombres.

## Cómo ingerir su respuesta

```bash
# JSON o CSV-export de la plataforma (claves en español o inglés):
flask import-persons-json export.json --source-slug venezuela-te-busca \
  --attribution "Venezuela Te Busca (reporte ciudadano, no verificado)"

# O si ofrecen un feed PFIF estándar:
flask import-pfif https://.../feed.xml --source-slug venezuela-te-busca \
  --attribution "Venezuela Te Busca"
```

Los registros entran a `PersonRecord` con su procedencia; los menores quedan fuera de las
vistas públicas; el directorio los muestra en "Personas desaparecidas" y "Fallecidos" con
su fuente.
