#!/usr/bin/env python3
"""Dizaster web · genera los assets estáticos optimizados:
 - webfonts woff2 (subconjuntos) desde /workspace/dizaster/tipografias/
 - gemas recortadas (webp con alfa, 240 px) desde /workspace/dizaster/gemstones/
Requiere: pillow, numpy, scipy, fonttools, brotli.  Uso: python3 tools/build_assets.py
"""
import os, numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as nd
from fontTools import subset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_FONTS = '/workspace/dizaster/tipografias/'
SRC_GEMS = '/workspace/dizaster/gemstones/'
OUT_F = os.path.join(ROOT, 'assets/fonts'); OUT_G = os.path.join(ROOT, 'assets/gems')

LATIN = 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2190-2199,U+2212,U+2215,U+25A0-25FF,U+2600-26FF'
FONTS = [  # (archivo, salida, unicodes)
    ('GermaniaOne-Regular.ttf', 'germania-one.woff2', LATIN),
    ('BarlowSemiCondensed-Regular.ttf', 'barlow-sc-400.woff2', LATIN),
    ('BarlowSemiCondensed-Italic.ttf', 'barlow-sc-400i.woff2', LATIN),
    ('BarlowSemiCondensed-Medium.ttf', 'barlow-sc-500.woff2', LATIN),
    ('BarlowSemiCondensed-SemiBold.ttf', 'barlow-sc-600.woff2', LATIN),
    ('BarlowSemiCondensed-Bold.ttf', 'barlow-sc-700.woff2', LATIN),
    ('Michroma-Regular.ttf', 'michroma.woff2', LATIN),
    # glifos del sistema de cartas (10.4 / 10.5)
    ('NotoSansBamum[wght].ttf', 'dz-bamum.woff2', 'U+16A30,U+16917,U+16891'),   # 𖨰 Precursora · 𖤗 Furia · 𖢑 Vestigio
    ('NotoSansCarian-Regular.ttf', 'dz-carian.woff2', 'U+102C4'),               # 𐋄 Nexo
    ('NotoSansSymbols[wght].ttf', 'dz-symbols.woff2', 'U+26B6'),                # ⚶ Instantáneo
]

def parse_unicodes(s):
    out = []
    for part in s.split(','):
        part = part.strip().replace('U+', '')
        if '-' in part:
            a, b = part.split('-'); out += range(int(a, 16), int(b, 16) + 1)
        else:
            out.append(int(part, 16))
    return out

def build_fonts():
    os.makedirs(OUT_F, exist_ok=True)
    for src, dst, uni in FONTS:
        opts = subset.Options(); opts.flavor = 'woff2'; opts.layout_features = ['*']; opts.name_IDs = ['*']
        opts.notdef_outline = True
        f = subset.load_font(os.path.join(SRC_FONTS, src), opts)
        s = subset.Subsetter(opts); s.populate(unicodes=parse_unicodes(uni)); s.subset(f)
        subset.save_font(f, os.path.join(OUT_F, dst), opts)
        print('font', dst, os.path.getsize(os.path.join(OUT_F, dst)), 'B')
    for lic in ('OFL-germaniaone.txt', 'OFL-barlowsemicondensed.txt', 'OFL-michroma.txt', 'OFL-notosansbamum.txt', 'OFL-notosanscarian.txt', 'OFL-notosanssymbols.txt'):
        with open(os.path.join(SRC_FONTS, lic), 'rb') as a, open(os.path.join(OUT_F, lic), 'wb') as b: b.write(a.read())

def ramp(x, a, b): return np.clip((x - a) / (b - a), 0, 1)

def cutout(path, size=240):
    """Recorta la gema de su fondo negro (silueta sólida + alfa por luminancia) y la centra."""
    im = Image.open(path).convert('RGB'); im.thumbnail((700, 700), Image.LANCZOS)
    a = np.asarray(im).astype(np.float64) / 255; L = a.max(2)
    solid = nd.binary_fill_holes(nd.binary_closing(L > 0.06, iterations=3))
    lb, nl = nd.label(solid); sizes = nd.sum(solid, lb, range(1, nl + 1)); solid = nd.binary_fill_holes(lb == (np.argmax(sizes) + 1))
    a_s = np.asarray(Image.fromarray((solid * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))).astype(np.float64) / 255
    alpha = np.maximum(a_s, ramp(L, 0.02, 0.35))
    ys, xs = np.nonzero(solid); cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    gy, gx = np.mgrid[0:L.shape[0], 0:L.shape[1]]; d = np.hypot(gx - cx, gy - cy); r = d[solid].max()
    alpha *= 1 - ramp(d, r * 1.02, r * 1.10)
    rgb = np.where(alpha[..., None] > 1e-3, np.clip(a / np.maximum(alpha[..., None], 1e-3), 0, 1), 0)
    rgba = np.dstack([rgb, alpha]); img = Image.fromarray((rgba * 255).astype(np.uint8), 'RGBA')
    R = int(r * 1.08); box = (int(cx - R), int(cy - R), int(cx + R), int(cy + R))
    img = img.crop(box).resize((size, size), Image.LANCZOS)
    return img

def build_gems():
    os.makedirs(OUT_G, exist_ok=True)
    for f in sorted(os.listdir(SRC_GEMS)):
        if f.startswith('gemstone-') or not f.endswith('.jpg'): continue
        img = cutout(os.path.join(SRC_GEMS, f))
        out = os.path.join(OUT_G, f.replace('.jpg', '.webp')); img.save(out, 'WEBP', quality=86, method=6)
        print('gem', os.path.basename(out), os.path.getsize(out), 'B')

if __name__ == '__main__':
    build_fonts(); build_gems()
