#!/usr/bin/env python3
"""Dizaster web · genera data/rules.json, data/cards.json y data/glossary.json
a partir de las fuentes de /workspace/dizaster/referencias/ (no inventa reglas: todo texto
de regla sale del Reglamento v1.5 (manual final); todo texto de carta, de la Referencia de Cartas v1.4).
Uso: python3 tools/build_data.py
"""
import os, re, json, html, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from glosario import GLOSARIO
from recomendaciones import TIPS, AVISOS, USO

REF = '/workspace/dizaster/referencias/'
F_RULES = '/workspace/dizaster/manual/Dizaster-Manual-v1.5.md'
F_CARDS = REF + 'Dizaster-Cartas-Referencia-v1.4.md'
F_JSX = REF + 'dz-elevate-data-v14.jsx'
F_PROP = '/workspace/dizaster/textos/cartas-asalto-dominio-propuesta.json'
F_COL = '/workspace/dizaster/cartas/frontales/colores.json'
F_FINAL = '/workspace/dizaster/textos/set-completo-textos.md'
OUT = os.path.join(ROOT, 'data')

def anchor(rid): return 'r-' + rid.replace('.', '-')

# ───────────────────────── markdown mínimo → HTML ─────────────────────────
RULE_IDS = set()

def link_refs(s, allow_int_after_ver=True, skip=()):
    """Enlaza referencias a apartados (**11.9**, (13.3), «ver 14»…) que existen en el Reglamento."""
    def bold(m):
        inner = m.group(1)
        mm = re.fullmatch(r'(\d{1,2}(?:\.\d{1,2}){1,2})', inner)
        if mm and inner in RULE_IDS and inner not in skip:
            return f'<a class="rref" href="#{anchor(inner)}">{inner}</a>'
        mi = re.fullmatch(r'(\d{1,2})', inner)
        pre = s[max(0, m.start() - 14):m.start()].lower()
        if mi and inner in RULE_IDS and allow_int_after_ver and re.search(r'(ver|apartado|en|y|de)\s*$', pre):
            return f'<a class="rref" href="#{anchor(inner)}">{inner}</a>'
        return f'<strong>{inner}</strong>'
    s = re.sub(r'\*\*(.+?)\*\*', bold, s)
    def paren(m):
        ids = re.findall(r'\d{1,2}(?:\.\d{1,2}){1,2}', m.group(1))
        out = m.group(0)
        for i in ids:
            if i in RULE_IDS and i not in skip:
                out = re.sub(r'(?<![\d.>])' + re.escape(i) + r'(?![\d.])', f'<a class="rref" href="#{anchor(i)}">{i}</a>', out, count=1)
        return out
    s = re.sub(r'\(([^()]*\d+\.\d+[^()]*)\)', paren, s)
    # «según 12.6», «ver 7.2» sin negritas ni paréntesis
    s = re.sub(r'(según |ver )(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)(?![\d.<])',
               lambda m: m.group(1) + (f'<a class="rref" href="#{anchor(m.group(2))}">{m.group(2)}</a>' if m.group(2) in RULE_IDS else m.group(2)), s)
    return s

def inline(s, **kw):
    s = html.escape(s, quote=False)
    s = re.sub(r'\[([^\]]+)\]\(#[^)]*\)', r'\1', s)
    s = link_refs(s, **kw)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)', r'<em>\1</em>', s)
    return s

def plain(s):
    s = re.sub(r'\*\*|\*|`', '', s); s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    return re.sub(r'\s+', ' ', s).strip()

def table_html(lines):
    rows = [[c.strip() for c in l.strip().strip('|').split('|')] for l in lines]
    head, body = rows[0], rows[2:]
    t = '<div class="tbl"><table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr></thead><tbody>'
    for r in body: t += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>'
    return t + '</tbody></table></div>'

def blocks_html(lines):
    """Convierte un grupo de líneas md (párrafos, tablas, listas, citas) en HTML."""
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        if not l.strip(): i += 1; continue
        if l.lstrip().startswith('|'):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith('|'): j += 1
            out.append(table_html(lines[i:j])); i = j; continue
        if re.match(r'\s*(-|\d+\.)\s', l):
            tag = 'ol' if re.match(r'\s*\d+\.', l) else 'ul'; items = []
            while i < len(lines) and re.match(r'\s*(-|\d+\.)\s', lines[i]):
                items.append(re.sub(r'^\s*(-|\d+\.)\s+', '', lines[i])); i += 1
            out.append(f'<{tag}>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + f'</{tag}>'); continue
        if l.startswith('>'):
            q = []
            while i < len(lines) and lines[i].startswith('>'):
                q.append(lines[i].lstrip('>').strip()); i += 1
            out.append('<blockquote>' + '<br>'.join(inline(x) for x in q if x) + '</blockquote>'); continue
        p = []
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(('|', '>')) and not re.match(r'\s*(-|\d+\.)\s', lines[i]):
            p.append(lines[i].strip()); i += 1
        out.append('<p>' + inline(' '.join(p)) + '</p>')
    return ''.join(out)

def lines_plain(lines):
    return plain(' '.join(re.sub(r'^\s*(>|-|\d+\.)\s*', '', l).replace('|', ' ') for l in lines if not re.match(r'^\s*\|?\s*:?-{3}', l)))

# ───────────────────────── Reglamento ─────────────────────────
def parse_rules():
    md = open(F_RULES, encoding='utf-8').read().split('\n')
    # ids primero (para poder enlazar)
    for l in md:
        m = re.match(r'#{2,3} (\d+(?:\.\d+)*) · ', l) or re.match(r'\*\*(\d+(?:\.\d+)+) · ', l)
        if m: RULE_IDS.add(m.group(1))
    # cabecera: versión + novedades
    head, k = [], 0
    while not md[k].startswith('## Índice'): head.append(md[k]); k += 1
    novedades = []
    for l in head:
        m = re.match(r'>\s*\*\*Novedad de la (\d\.\d\.\d)\s*—\s*(.*?)\*\*\s*(.*)', l)
        if m: novedades.append({'version': m.group(1), 'titulo': plain(m.group(2)).strip(' —.'), 'html': inline(m.group(3).rstrip()), 'text': plain(m.group(3))})
    intro = [l for l in head if l and not l.startswith(('#', '>', '**Reglamento v'))]
    items, cur = [], None
    chapter = sub = None; buf = []
    def flush():
        nonlocal buf
        if cur is not None and buf:
            cur['html'] += blocks_html(buf); cur['text'] = (cur['text'] + ' ' + lines_plain(buf)).strip()
        buf = []
    start = next(i for i, l in enumerate(md) if l.startswith('## 1 · '))
    for l in md[start:]:
        if l.strip() == '---': continue
        m2 = re.match(r'## (\d+) · (.+)', l); m3 = re.match(r'### (\d+(?:\.\d+)+) · (.+)', l)
        mp = re.match(r'\*\*(\d+(?:\.\d+)+) · (.+?)\*\*\s*(.*)', l)
        if m2 or m3:
            flush()
            rid, title = (m2 or m3).group(1), (m2 or m3).group(2).strip()
            lvl = 1 if m2 else 2
            if lvl == 1: chapter = rid
            cur = {'id': rid, 'anchor': anchor(rid), 'level': lvl, 'title': title, 'chapter': chapter, 'html': '', 'text': ''}
            items.append(cur); continue
        if mp:
            flush()
            rid, title, rest = mp.group(1), mp.group(2).strip(), mp.group(3)
            title = title.rstrip('.')
            cur = {'id': rid, 'anchor': anchor(rid), 'level': 3 if rid.count('.') >= 1 else 2, 'title': title, 'chapter': chapter, 'html': '', 'text': ''}
            if rid.count('.') == 1 and not any(x['id'] == rid for x in items[:-1]): cur['level'] = 2
            if rid.count('.') == 2: cur['level'] = 3
            items.append(cur)
            if rest.lstrip().startswith((',', ';')): rest = '**' + title + '**' + rest   # p. ej. 15.1: el título es el arranque de la frase
            if rest.strip(): buf.append(rest)
            continue
        buf.append(l)
    flush()
    # nivel real: 3 si su padre existe como item de nivel 2
    ids = {x['id']: x for x in items}
    for x in items:
        parts = x['id'].split('.')
        x['parent'] = '.'.join(parts[:-1]) if len(parts) > 1 else None
        if len(parts) == 2: x['level'] = 2
        if len(parts) == 3: x['level'] = 3
    chapters = [{'id': x['id'], 'title': x['title'], 'anchor': x['anchor']} for x in items if x['level'] == 1]
    return {'version': '1.5', 'titulo': 'Dizaster — Reglamento', 'fuente': os.path.basename(F_RULES),
            'intro_html': ''.join('<p>' + inline(l) + '</p>' for l in intro),
            'novedades': novedades, 'chapters': chapters, 'items': items}

# ───────────────────────── Catálogo JSX (para nombres EN, Eventos, Necrovante) ─────────────────────────
def js_str(s):
    s = s.strip()
    q = s[0]; body = s[1:-1]
    return body.replace("\\'", "'").replace('\\"', '"')

STR = r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\""
def parse_jsx():
    t = open(F_JSX, encoding='utf-8').read()
    cards = {}
    for m in re.finditer(r"C\(\s*'(\w+)',\s*'(\w+)',\s*'(\w+)',\s*'(\w+)',\s*\[([^\]]*)\],\s*(\d+),\s*(" + STR + r"),\s*(" + STR + r"),\s*(" + STR + r"),\s*(" + STR + r")\)", t, re.S):
        code, deck, clase, typ, mods, qty = m.group(1, 2, 3, 4, 5, 6)
        cards[code] = dict(code=code, deck=deck, clase=clase, type=typ, mods=re.findall(r"'(\w+)'", mods), qty=int(qty),
                           name_es=js_str(m.group(7)), name_en=js_str(m.group(8)), text_es=js_str(m.group(9)), text_en=js_str(m.group(10)))
    for m in re.finditer(r"EV\(\s*'(\w+)',\s*\[([^\]]*)\],\s*(" + STR + r"),\s*(" + STR + r"),\s*(" + STR + r"),\s*(" + STR + r")\)", t, re.S):
        code = m.group(1)
        cards[code] = dict(code=code, deck='evento', clase='evento', type='evento', mods=re.findall(r"'(\w+)'", m.group(2)), qty=1,
                           name_es=js_str(m.group(3)), name_en=js_str(m.group(4)), text_es=js_str(m.group(5)), text_en=js_str(m.group(6)))
    necro = dict(re.findall(r"^\s*([A-Z]\d\d): (" + STR + r"),", t, re.M))
    necro = {k: js_str(v) for k, v in necro.items()}
    return cards, necro

# ───────────────────────── Referencia de Cartas ─────────────────────────
TYPE_MAP = {'Precursora': 'precursora', 'Nexo': 'nexo', 'Instantáneo': 'instantaneo'}
CLASS_MAP = {'Ataque': 'ataque', 'Defensa': 'defensa', 'Efecto': 'efecto', 'Invocación': 'invocacion', 'Conjuro': 'conjuro', 'Reacción': 'reaccion', 'Aniquilación': 'aniquilacion'}

def unq(s):
    s = s.strip().rstrip()
    m = re.match(r'^«(.*)»\s*$', s.strip(), re.S)
    return (m.group(1) if m else s).strip()

def parse_ref_cards():
    t = open(F_CARDS, encoding='utf-8').read()
    out = []
    parts = re.split(r'\n### ([A-Z]\d\d) · (.+)\n', t)
    for i in range(1, len(parts), 3):
        code, name, body = parts[i], parts[i + 1].strip(), parts[i + 2].split('\n## ')[0]
        meta = re.search(r'\n\*\*(.+?)\*\*\n', '\n' + body).group(1)
        mm = re.match(r'(\w+) · (\S+) · \S+ (\w+)(?: \+ \S+ (\w+))? · (\d+) ejemplar', meta)
        deck, clase, typ, mod, qty = mm.groups()
        antes = re.search(r'\*\*Antes:\*\*\s*(.+?)\s*$', body, re.M)
        ahora = re.search(r'\*\*Ahora:\*\*\s*(.+?)\s*$', body, re.M)
        notas = [plain(x) for x in re.findall(r'^>\s*⚠\s*(.+)$', body, re.M)]
        uso = re.search(r'\*\*Uso\.\*\*\s*(.+?)(?:\n\n|$)', body, re.S)
        out.append(dict(code=code, name=name, deck=deck.lower(), clase=CLASS_MAP[clase], type=TYPE_MAP[typ],
                        mods=['furia'] if mod == 'Furia' else [], qty=int(qty),
                        antes=unq(antes.group(1)) if antes else None, ahora=unq(ahora.group(1)) if ahora else None,
                        notas=notas, uso_md=uso.group(1).strip() if uso else ''))
    # Eventos
    ev = []
    fam = None
    sec = t.split('## 5 · Cartas de Evento')[1].split('\n## 6 ·')[0]
    lines = sec.split('\n'); k = 0
    while k < len(lines):
        l = lines[k]
        if l.startswith('### 5.1'): fam = 'general'
        elif l.startswith('### 5.2'): fam = 'dado'
        elif l.startswith('### 5.3'): fam = 'especifico'
        m = re.match(r'\*\*(.+?)\*\*(?: · 𖢑 Vestigio)?\*?\*?\s*—\s*\*«(.+?)»\*\s*(.*)$', l)
        if m and fam:
            name = m.group(1).replace(' · 𖢑 Vestigio', '').strip()
            vest = 'Vestigio' in l.split('—')[0]
            original = m.group(2).strip(); rest = m.group(3).strip()
            ahora, coment = None, ''
            if rest.startswith('—'): coment = rest.lstrip('— ').strip()
            j = k + 1
            while j < len(lines) and lines[j].strip() and not lines[j].startswith('**') or (j < len(lines) and lines[j].startswith('**Ahora:**')) or (j < len(lines) and lines[j].startswith('Nota:')):
                lj = lines[j]
                ma = re.match(r'\*\*Ahora:\*\*\s*«(.+?)»\s*(?:—\s*(.*))?$', lj.strip())
                if ma: ahora = ma.group(1).strip(); coment = (ma.group(2) or '').strip()
                elif lj.startswith('Nota:'): coment = (coment + ' ' + lj.strip()).strip()
                j += 1
            warn = '⚠' in coment
            coment = coment.replace('⚠', '').strip()
            ev.append(dict(name=name, vestigio=vest, original=original, ahora=ahora, coment=coment, warn=warn, familia=fam))
            k = j; continue
        k += 1
    return out, ev

def norm(s): return re.sub(r'\W+', '', s.lower())

def parse_final():
    """Textos finales del set impreso (set-completo-textos.md): código → {name, cuerpo, reglas}."""
    t = open(F_FINAL, encoding='utf-8').read().split('\n'); out = {}
    for i, l in enumerate(t):
        m = re.match(r'^\*\*([A-Z]{1,2}\d\d) · (.+?)\*\*(?: ✎)? — (.+?)\s*$', l)
        if not m: continue
        body = t[i + 1].strip().strip('«»').strip()
        pie = t[i + 2].strip()[4:].strip() if i + 2 < len(t) and t[i + 2].startswith('Pie:') else ''
        refs = re.findall(r'\d{1,2}(?:\.\d{1,2}){0,2}', pie)
        refs += re.findall(r'(?<![\d.])(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)(?![\d])', body)
        out[m.group(1)] = {'name': m.group(2), 'cuerpo': body, 'reglas': list(dict.fromkeys(refs)), 'pie': pie}
    return out

RULE_PAREN = re.compile(r'\s*\((?:ver\s+)?(\d{1,2}(?:\.\d{1,2}){1,2}(?:\s*(?:y|,|·)\s*\d{1,2}(?:\.\d{1,2}){0,2})*)\)')
def split_refs(text):
    """Saca del cuerpo las citas a reglas «(11.9)» → pie de la carta (estilo final de impresión)."""
    refs = []
    def sub(m):
        refs.extend(re.findall(r'\d{1,2}(?:\.\d{1,2}){1,2}', m.group(1))); return ''
    body = RULE_PAREN.sub(sub, text)
    inline_refs = re.findall(r'(?<![\d.])(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)(?![\d])', body)
    refs += inline_refs
    body = re.sub(r'\s+([.,;:])', r'\1', body).strip()
    return body, list(dict.fromkeys(refs))

def strip_type_prefix(text):
    return re.sub(r'^Instantáneo(?: con Furia)?\.\s*', '', text)

def main():
    rules = parse_rules()
    jsx, necro = parse_jsx()
    ref, events = parse_ref_cards()
    prop = {c['code']: c for c in json.load(open(F_PROP, encoding='utf-8'))['cartas']}
    colores = json.load(open(F_COL, encoding='utf-8'))
    FINAL = parse_final(); assert len(FINAL) == 97, len(FINAL)
    GEM_FILES = sorted(os.listdir(os.path.join(ROOT, 'assets/gems')))
    def gem_file(n): return next(f for f in GEM_FILES if f.startswith(f'{n:02d}-'))
    cards = []
    deck_count = {'asalto': 0, 'dominio': 0, 'evento': 0}
    deck_total = {'asalto': 20, 'dominio': 34, 'evento': 43}
    for c in ref:
        j = jsx[c['code']]
        assert (j['deck'], j['clase'], j['type'], j['qty']) == (c['deck'], c['clase'], c['type'], c['qty']), c['code']
        official = c['ahora'] or c['antes']
        body, refs = split_refs(strip_type_prefix(official))
        deck_count[c['deck']] += 1
        col = colores[f"{c['clase']}/{c['deck']}"]
        uso_md = USO.get(c['code'], c['uso_md'])
        uso_html = inline(uso_md, skip=('2.1', '2.2', '2.3'))
        uso_refs = [r for r in re.findall(r'\*\*(\d{1,2}(?:\.\d{1,2}){1,2})\*\*', uso_md) if r in RULE_IDS and r not in ('2.1', '2.2', '2.3')]
        p = prop.get(c['code'])
        cards.append(dict(
            code=c['code'], deck=c['deck'], clase=c['clase'], type=c['type'], mods=c['mods'], qty=c['qty'],
            n=deck_count[c['deck']], of=deck_total[c['deck']],
            name={'es': c['name'], 'en': j['name_en']},
            gem=gem_file(col['gema']), color=col['color'] if isinstance(col['color'], str) else col['color'][0],
            texts={
                'final': {'fuente': 'Set impreso · Reglamento v1.5', 'cuerpo': FINAL[c['code']]['cuerpo'], 'reglas': FINAL[c['code']]['reglas'], 'completo': FINAL[c['code']]['cuerpo']},
                'referencia': {'fuente': 'Referencia de Cartas v1.4 · «Ahora»', 'cuerpo': body, 'reglas': refs, 'completo': official},
                'catalogo': {'fuente': 'dz-elevate-data-v14.jsx', 'cuerpo': j['text_es'], 'en': j['text_en']},
                'original': {'fuente': 'Referencia de Cartas v1.4 · «Antes»', 'cuerpo': c['antes']},
                'propuesta': None,  # borrador v1.4.2 retirado: el set final usa set-completo-textos.md
            },
            uso_html=uso_html, uso_final=c['code'] in USO, uso_refs=list(dict.fromkeys(uso_refs)), notas=c['notas'],
            necro=({'texto': necro[c['code']], 'estado': 'regla fija del autor' if c['clase'] == 'invocacion' else 'propuesta pendiente del autor'} if c['code'] in necro else None),
            familia=None, modo=['primigenio', 'superviviente', 'forjado'],
            tips=TIPS.get(c['code'], []), avisos=AVISOS.get(c['code'], []),
        ))
    evmap = {norm(v['name_es']): v for v in jsx.values() if v['deck'] == 'evento'}
    assert len(events) == 43, len(events)
    for e in events:
        j = evmap[norm(e['name'])]
        official = e['ahora'] or e['original']
        body, refs = split_refs(official)
        deck_count['evento'] += 1
        mods = ['vestigio'] if e['vestigio'] else []
        assert mods == j['mods'], (e['name'], mods, j['mods'])
        modo = {'general': ['primigenio', 'superviviente', 'forjado'], 'dado': ['primigenio'], 'especifico': ['superviviente', 'forjado']}[e['familia']]
        cards.append(dict(
            code=j['code'], deck='evento', clase='evento', type='evento', mods=mods, qty=1,
            n=deck_count['evento'], of=43, name={'es': j['name_es'], 'en': j['name_en']},
            gem='11-evento.webp', color='#E9E4D4',
            texts={
                'final': {'fuente': 'Set impreso · Reglamento v1.5', 'cuerpo': FINAL[j['code']]['cuerpo'], 'reglas': FINAL[j['code']]['reglas'], 'completo': FINAL[j['code']]['cuerpo']},
                'referencia': {'fuente': 'Referencia de Cartas v1.4 · «Ahora»' if e['ahora'] else 'Referencia de Cartas v1.4 · texto original (sin cambios)', 'cuerpo': body, 'reglas': refs, 'completo': official},
                'catalogo': {'fuente': 'dz-elevate-data-v14.jsx', 'cuerpo': j['text_es'], 'en': j['text_en']},
                'original': {'fuente': 'Referencia de Cartas v1.4 · «Antes»', 'cuerpo': e['original']},
                'propuesta': None,
            },
            uso_html=inline(e['coment'], skip=('2.1', '2.2', '2.3')) if e['coment'] else '',
            uso_refs=[r for r in re.findall(r'\d{1,2}\.\d{1,2}(?:\.\d{1,2})?', e['coment']) if r in RULE_IDS],
            notas=(['Decisión de redacción registrada en la Referencia (pendiente del veredicto del autor).'] if e['warn'] else []),
            necro=None, familia=e['familia'], modo=modo,
            tips=TIPS.get(j['code'], []), avisos=AVISOS.get(j['code'], []),
        ))
    assert len(cards) == 97
    bad = [(c['code'], r) for c in cards for r in c['texts']['final']['reglas'] + c['uso_refs'] if r not in RULE_IDS]
    assert not bad, bad
    meta = {
        'texto_activo': 'final',   # textos del set impreso (set-completo-textos.md)
        'fuentes': {'final': os.path.basename(F_FINAL), 'referencia': os.path.basename(F_CARDS), 'catalogo': os.path.basename(F_JSX)},
        'mazos': {'asalto': {'nombre': 'Asalto', 'color': colores['mazo/asalto']['color'], 'gem': gem_file(3), 'diseños': 20, 'copias': sum(c['qty'] for c in cards if c['deck'] == 'asalto')},
                  'dominio': {'nombre': 'Dominio', 'color': colores['mazo/dominio']['color'], 'gem': gem_file(8), 'diseños': 34, 'copias': sum(c['qty'] for c in cards if c['deck'] == 'dominio')},
                  'evento': {'nombre': 'Evento', 'color': '#E9E4D4', 'gem': gem_file(11), 'diseños': 43, 'copias': 43}},
        'clases': {k: {'nombre': n} for k, n in [('ataque', 'Ataque'), ('defensa', 'Defensa'), ('efecto', 'Efecto'), ('invocacion', 'Invocación'), ('conjuro', 'Conjuro'), ('reaccion', 'Reacción'), ('aniquilacion', 'Aniquilación'), ('evento', 'Evento')]},
        'tipos': {'precursora': {'nombre': 'Precursora', 'simbolo': '\U00016A30', 'regla': '10.4.1'}, 'nexo': {'nombre': 'Nexo', 'simbolo': '\U000102C4', 'regla': '10.4.2'},
                  'instantaneo': {'nombre': 'Instantánea', 'simbolo': '\u26B6', 'regla': '10.4.3'}, 'evento': {'nombre': 'Evento', 'simbolo': '', 'regla': '10.2.3'}},
        'mods': {'furia': {'nombre': 'Furia', 'simbolo': '\U00016917', 'regla': '10.5.1'}, 'vestigio': {'nombre': 'Vestigio', 'simbolo': '\U00016891', 'regla': '10.5.2'}},
        'familias': {'general': 'Eventos generales', 'dado': 'Movimiento con dado (Primigenio)', 'especifico': 'Movimiento específico (Superviviente y Forjado)'},
    }
    os.makedirs(OUT, exist_ok=True)
    json.dump(rules, open(os.path.join(OUT, 'rules.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump({'meta': meta, 'cards': cards}, open(os.path.join(OUT, 'cards.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    gl = []
    for g in GLOSARIO:
        for r in g['reglas']: assert r in RULE_IDS, (g['termino'], r)
        gl.append(g)
    gl.sort(key=lambda g: norm(g['termino'].replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')))
    json.dump({'version': '1.5', 'terms': gl}, open(os.path.join(OUT, 'glossary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('rules', len(rules['items']), 'items ·', len(rules['chapters']), 'capítulos ·', len(rules['novedades']), 'novedades')
    print('cards', len(cards), {d: sum(1 for c in cards if c['deck'] == d) for d in deck_count})
    print('glossary', len(gl), 'términos')
    print('cartas con reglas en el pie:', sum(1 for c in cards if c['texts']['final']['reglas']))

if __name__ == '__main__':
    main()
