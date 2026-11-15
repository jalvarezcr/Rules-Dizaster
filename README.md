# Dizaster · sitio de consulta (Reglamento v1.5 + Cartas)

Sitio **estático** en español y modo oscuro: HTML + CSS + JS, sin paso de compilación ni dependencias externas (las tipografías y las gemas van incluidas). Se puede publicar en **Cloudflare Pages** o en **GitHub Pages** tal cual.

## Secciones
1. **Inicio**: qué es Dizaster, tableros, modos, piezas, mazos y mazos.
2. **Inicio rápido**: preparación, ronda, turno, Fase de Resolución y victoria, paso a paso (modo Primigenio, con dado).
3. **Reglamento v1.5**: el texto íntegro por apartados, con buscador (resaltado, sin importar acentos) e índice. Cada apartado tiene un ancla `#r-<número>` (p. ej. `#r-11-9`).
4. **Glosario**: 56 términos de la A a la Z que enlazan a sus reglas.
5. **Cartas**: las 97 cartas (20 de Asalto, 34 de Dominio y 43 Eventos) con buscador y filtros por mazo, clase, tipo, modificador y modo. Al abrir una carta ves su render en CSS, el texto oficial, su uso, recomendaciones, la habilidad Necrovante, avisos, reglas relacionadas y la comparación de textos. Cada carta tiene enlace directo: `#carta-D02`.

## Estructura
```
web/
├── index.html              página única (secciones con anclas)
├── assets/css/site.css     identidad del sitio
├── assets/css/card.css     carta renderizada en CSS (estilo final de impresión)
├── assets/js/app.js        reglamento, glosario, cartas, búsqueda, detalle
├── assets/js/card.js       render de carta (DZCard.html)
├── assets/js/fx.js         fondo de partículas y relámpagos (se apaga con ✦ o con prefers-reduced-motion)
├── assets/fonts/           woff2 en subconjunto (Germania One, Barlow Semi Condensed, Michroma, Noto Bamum/Carian/Symbols) + licencias OFL
├── assets/gems/            19 gemas recortadas (webp de 240 px con transparencia)
├── data/rules.json         161 apartados del Reglamento v1.5
├── data/cards.json         97 cartas + metadatos (mazos, clases, tipos, modificadores)
├── data/glossary.json      glosario
├── tools/build_data.py     genera los 3 JSON desde los .md/.jsx de referencias/
├── tools/build_assets.py   genera fuentes y gemas
├── tools/glosario.py       términos del glosario
├── tools/recomendaciones.py  consejos por carta y avisos de inconsistencias
├── tools/check_site.py     verificación con Playwright y capturas
├── capturas/               capturas de verificación
├── _headers                cabeceras de caché y seguridad (Cloudflare Pages)
├── wrangler.toml           configuración de Cloudflare Pages
└── .nojekyll               para GitHub Pages
```

## Probar en local
```bash
cd web
python3 -m http.server 8000
# abre http://localhost:8000
```
Al abrir `index.html` directamente (file://) no carga, porque los datos se leen con `fetch`.

## Desplegar en Cloudflare Pages
**Opción A: arrastrar y soltar (dashboard)**
1. Entra a Cloudflare → *Workers & Pages* → *Create* → *Pages* → *Upload assets*.
2. Ponle nombre al proyecto (p. ej. `dizaster`) y arrastra la carpeta `web/` (o un zip de ella).
3. *Deploy*. Queda en `https://dizaster.pages.dev`.

**Opción B: CLI con Wrangler**
```bash
npx wrangler login
# desde la carpeta que contiene web/
npx wrangler pages deploy web --project-name dizaster
# o desde web/ (usa wrangler.toml)
cd web && npx wrangler pages deploy
```
Para conectarlo a Git: *Create → Pages → Connect to Git*, con *Build command* vacío y *Build output directory* `web` (o `/` si el repositorio es la propia carpeta).

No hace falta ningún Worker: el sitio es 100 % estático. Si más adelante quieres una API (por ejemplo, para votar textos), puedes añadir Pages Functions en `web/functions/`.

> `tools/` y `capturas/` también se suben. No contienen nada sensible, pero si no los quieres publicados, despliega una copia sin ellos: `rsync -a --exclude tools --exclude capturas web/ dist/ && npx wrangler pages deploy dist --project-name dizaster`.

## Desplegar en GitHub Pages
1. Sube el contenido de `web/` a un repositorio (en la raíz o en `/docs`).
2. *Settings → Pages → Build and deployment → Deploy from a branch*: elige la rama y la carpeta (`/root` o `/docs`).
3. Queda en `https://<usuario>.github.io/<repo>/`. Todas las rutas son relativas, así que funciona dentro de un subdirectorio. `.nojekyll` evita el procesado de Jekyll. GitHub Pages ignora `_headers`.

## Regenerar los datos
```bash
python3 tools/build_assets.py   # fuentes y gemas (pillow, numpy, scipy, fonttools, brotli)
python3 tools/build_data.py     # rules.json, cards.json, glossary.json
python3 tools/check_site.py http://localhost:8000/   # verificación (playwright + Chrome)
```
Fuentes: `manual/Dizaster-Manual-v1.5.md` (reglamento), `textos/set-completo-textos.md` (textos finales de carta), `referencias/Dizaster-Cartas-Referencia-v1.4.md`, `referencias/dz-elevate-data-v14.jsx` y `cartas/frontales/colores.json`.

## Textos de carta intercambiables
Cada carta de `data/cards.json` guarda varias versiones en `texts`:
- `final`: **oficial vigente**, el texto del set impreso (`textos/set-completo-textos.md`), con las referencias a reglas en el pie.
- `referencia`: la redacción «Ahora» de la Referencia de Cartas v1.4 (anterior).
- `catalogo`: el texto de `dz-elevate-data-v14.jsx`, con su versión en inglés.
- `original`: el texto «Antes».

La carta se dibuja con `meta.texto_activo` (hoy `"final"`). En la vista de detalle se pueden comparar todas las versiones.

## Notas
- Las **Recomendaciones** son consejos de juego, no reglas. Salen del texto de la carta y del reglamento, y la página las marca así.
- Los IDs de los Eventos (EV01–EV43) son provisionales, igual que en el catálogo JSX.
- Las inconsistencias conocidas (C02/C03, C16, C01, X01/X02, I05, EV21…) aparecen como avisos en cada carta. Para verlas todas, activa el filtro «Solo con avisos».
