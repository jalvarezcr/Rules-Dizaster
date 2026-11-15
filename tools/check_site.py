#!/usr/bin/env python3
"""Verificación + capturas con Playwright (Chrome del sistema).
Uso: (cd web && python3 -m http.server 8765 &) ; python3 tools/check_site.py [http://localhost:8765/]"""
import sys, os, json
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'capturas')
os.makedirs(OUT, exist_ok=True)
errors, report = [], {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
    pg.on('console', lambda m: errors.append(f'console.{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    pg.on('requestfailed', lambda r: errors.append(f'requestfailed: {r.url}'))
    pg.on('response', lambda r: errors.append(f'http {r.status}: {r.url}') if r.status >= 400 else None)
    pg.goto(URL, wait_until='networkidle'); pg.wait_for_selector('.cbtn')
    pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(600)
    report['cartas_en_rejilla'] = pg.locator('.cbtn').count()
    report['reglas_renderizadas'] = pg.locator('.rule').count()
    report['terminos_glosario'] = pg.locator('.gterm').count()
    # todas las referencias #r-… apuntan a un id existente
    report['refs_rotas'] = pg.evaluate("""() => { const ids=new Set([...document.querySelectorAll('[id]')].map(e=>e.id));
        return [...new Set([...document.querySelectorAll('a[href^="#r-"]')].map(a=>a.getAttribute('href').slice(1)))].filter(h=>!ids.has(h)); }""")
    report['refs_total'] = pg.evaluate("""() => new Set([...document.querySelectorAll('a[href^="#r-"]')].map(a=>a.getAttribute('href'))).size""")
    # fuentes de glifos cargadas
    report['fuentes'] = pg.evaluate("""() => ['Germania One','Barlow SC','DZ Glyphs','Michroma'].map(f=>[f, document.fonts.check('16px "'+f+'"', f==='DZ Glyphs' ? '\\u{16A30}\\u{102C4}\\u26B6\\u{16917}\\u{16891}' : 'Áb')])""")
    pg.screenshot(path=f'{OUT}/01-inicio.png')
    pg.goto(URL + '#inicio-rapido'); pg.wait_for_timeout(500); pg.screenshot(path=f'{OUT}/02-inicio-rapido.png')
    # búsqueda en reglamento
    pg.goto(URL + '#reglamento'); pg.wait_for_timeout(300)
    pg.fill('#rq', 'muralla bloques'); pg.wait_for_timeout(400)
    report['busqueda_reglas_muralla_bloques'] = pg.locator('.rule:not(.hide)').count(); report['marcas'] = pg.locator('#rules mark').count()
    pg.evaluate("document.querySelector('#reglamento').scrollIntoView()"); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{OUT}/03-reglamento-busqueda.png')
    pg.fill('#rq', ''); pg.wait_for_timeout(300)
    # ancla directa 11.9
    pg.goto(URL + '#r-11-9'); pg.wait_for_timeout(700)
    report['ancla_11_9_visible'] = pg.evaluate("(()=>{const r=document.getElementById('r-11-9').getBoundingClientRect();return r.top>=0&&r.top<300})()")
    pg.screenshot(path=f'{OUT}/04-regla-11-9.png')
    pg.goto(URL + '#glosario'); pg.wait_for_timeout(500); pg.screenshot(path=f'{OUT}/05-glosario.png')
    # búsqueda de cartas
    pg.goto(URL + '#cartas'); pg.wait_for_timeout(300)
    tests = {'D02': None, 'fénix': None, 'fenix': None, 'muralla': None, 'xyzzy': None}
    for q in tests:
        pg.fill('#cq', q); pg.wait_for_timeout(250); tests[q] = pg.locator('.cbtn').count()
    report['busqueda_cartas'] = tests
    pg.fill('#cq', ''); pg.select_option('#ftipo', 'nexo'); pg.wait_for_timeout(250); report['filtro_nexo'] = pg.locator('.cbtn').count()
    pg.select_option('#ftipo', ''); pg.click('#fdeck [data-v=dominio]'); pg.wait_for_timeout(250); report['filtro_dominio'] = pg.locator('.cbtn').count()
    pg.click('#fdeck [data-v=""]'); pg.select_option('#fmodo', 'primigenio'); pg.wait_for_timeout(250); report['filtro_primigenio'] = pg.locator('.cbtn').count()
    pg.select_option('#fmodo', ''); pg.wait_for_timeout(250)
    pg.evaluate("document.querySelector('#cartas').scrollIntoView()"); pg.wait_for_timeout(600)
    pg.screenshot(path=f'{OUT}/06-cartas.png')
    # abrir las 97 cartas
    codes = pg.evaluate("[...document.querySelectorAll('.cbtn')].map(a=>a.dataset.code)")
    opened = 0
    for c in codes:
        pg.evaluate(f"location.hash='carta-{c}'"); pg.wait_for_function(f"document.querySelector('#detail').open && document.querySelector('#d-title') && document.querySelector('#d-face .dzc')")
        if pg.locator('#d-info .kicker').inner_text().startswith(c): opened += 1
    report['detalles_abiertos'] = opened
    for c, name in [('D02', '07-detalle-D02'), ('X02', '08-detalle-X02'), ('EV30', '09-detalle-EV30'), ('I04', '10-detalle-I04')]:
        pg.evaluate(f"location.hash='carta-{c}'"); pg.wait_for_timeout(500); pg.screenshot(path=f'{OUT}/{name}.png')
    # pestaña del texto anterior y clic en referencia de regla desde el detalle
    pg.evaluate("location.hash='carta-D02'"); pg.wait_for_timeout(300); pg.click('#d-tabs [data-text=referencia]'); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{OUT}/11-detalle-D02-referencia-anterior.png')
    pg.click('#d-info a.rref[href="#r-11-9"]'); pg.wait_for_timeout(700)
    report['clic_regla_desde_detalle'] = pg.evaluate("!document.querySelector('#detail').open && location.hash==='#r-11-9'")
    # móvil
    m = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    m.on('pageerror', lambda e: errors.append(f'pageerror(mobile): {e}'))
    m.goto(URL, wait_until='networkidle'); m.wait_for_timeout(600); m.screenshot(path=f'{OUT}/12-movil-inicio.png')
    m.goto(URL + '#cartas'); m.wait_for_timeout(600); m.screenshot(path=f'{OUT}/13-movil-cartas.png')
    m.goto(URL + '#carta-C12'); m.wait_for_timeout(800); m.screenshot(path=f'{OUT}/14-movil-detalle-C12.png')
    # hoja de las 97 cartas (render CSS)
    s = b.new_page(viewport={'width': 1600, 'height': 900}); s.goto(URL + '#cartas', wait_until='networkidle'); s.wait_for_timeout(800)
    s.add_style_tag(content='.topbar,.filters,.sec:not(#cartas),.foot,#fx{display:none!important}.cgrid{grid-template-columns:repeat(10,1fr)!important;gap:10px!important}')
    s.wait_for_timeout(800); s.locator('#cartas').screenshot(path=f'{OUT}/15-hoja-97-cartas.png')
    b.close()
report['errores'] = errors
print(json.dumps(report, ensure_ascii=False, indent=1))
