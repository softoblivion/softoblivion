"""SVG assets of the profile README: the hero band with the phrase and, per application, one row cut into two
images (the repository link and the download link).

Every asset is written twice, for the dark and the light theme, and the README picks one through <picture>.
The look follows the hero banners of the application repositories: a dark gradient in the app's theme colours,
blurred drifting blobs, a glass tile around the app icon, one type family embedded as a data URI so the
SVG needs no external resource. Animation is CSS inside the SVG (a soft rise and fade on load, slowly drifting
blobs); every delay is written as an explicit `animation-delay`, so a renderer can shift the clock to any
instant; it all stops under prefers-reduced-motion.

Usage:  py -3 tools/make-cards.py [--fetch] [--out assets]
  --fetch   read the latest release tag of every repository from the GitHub API and store it in apps.json
Writes the assets (file names carry a content hash) and README.md. Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
FONT_FILE = HERE / "Sora-latin.woff2"
FONT = "Sora,'Segoe UI Variable Display','Segoe UI',Inter,Roboto,'Helvetica Neue',Arial,system-ui,sans-serif"

THEMES = {
    "dark": {
        "ink": "#ffffff", "ink2_op": 0.72, "ink3_op": 0.46,
        "tile_a": 0.16, "tile_b": 0.04, "rim_a": 0.75, "rim_b": 0.12, "rim_c": 0.35,
        "blob_hue": 0.85, "blob_acc": 0.75, "shadow": 0.45,
        "frame": 0.12,
    },
    "light": {
        "ink": "#0b1020", "ink2_op": 0.70, "ink3_op": 0.48,
        "tile_a": 0.85, "tile_b": 0.55, "rim_a": 1.0, "rim_b": 0.6, "rim_c": 0.9,
        "blob_hue": 0.55, "blob_acc": 0.50, "shadow": 0.18,
        "frame": 0.9,
    },
}
BRAND_ACCENT, BRAND_HUE = "#7a8cff", "#ff7a59"
BRAND_BG = ["#03050c", "#070c1c", "#0d1430"]


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def font_face() -> str:
    b64 = base64.b64encode(FONT_FILE.read_bytes()).decode("ascii")
    return ("@font-face{font-family:'Sora';font-weight:100 800;font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def load_icon(path: pathlib.Path, prefix: str, x: float, y: float, size: float) -> str:
    data = path.read_bytes()
    if path.suffix.lower() == ".svg":
        text = data.decode("utf-8").replace("\r\n", "\n")     # the output's hash must not depend on the checkout's line endings
        text = re.sub(r"<\?xml[^>]*\?>", "", text)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        for i in sorted(set(re.findall(r'\bid="([^"]+)"', text)), key=len, reverse=True):
            text = text.replace(f'id="{i}"', f'id="{prefix}{i}"')
            text = text.replace(f"url(#{i})", f"url(#{prefix}{i})")
            text = text.replace(f'href="#{i}"', f'href="#{prefix}{i}"')
        m = re.search(r"<svg\b([^>]*)>", text)
        vb = re.search(r'viewBox="([^"]+)"', m.group(1))
        inner = text[m.end(): text.rfind("</svg>")]
        return (f'<svg x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" '
                f'viewBox="{vb.group(1) if vb else "0 0 64 64"}" preserveAspectRatio="xMidYMid meet">{inner}</svg>')
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}[path.suffix.lower()]
    b64 = base64.b64encode(data).decode("ascii")
    return (f'<image x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" '
            f'preserveAspectRatio="xMidYMid meet" href="data:{mime};base64,{b64}"/>')


def icon_of(a: dict, prefix: str, x: float, y: float, size: float) -> str:
    isz = size * a["icon_scale"]
    return load_icon(ROOT / "assets" / "icons" / a["icon"], prefix, x + (size - isz) / 2, y + (size - isz) / 2, isz)


def text_w(s: str, size: float, weight: int = 600) -> float:
    """Rough width of a Sora string; pills and chips are sized by it, typed lines force it with textLength."""
    k = 0.58 + (weight - 400) / 2400
    return len(s) * size * k


# ----------------------------------------------------------------------------------------------- building blocks

def defs_common(t: dict, uid: str, accent: str, hue: str, bg: list[str], light: bool, pale: bool = False) -> str:
    """Gradients shared by every composition. `uid` keeps ids apart when several blocks share one file."""
    top, mid, bot = bg
    if light:
        top, mid, bot = ("#f4f6fb", "#eceff7", "#e3e8f2") if pale else ("#ffffff", "#f7f8fc", "#eef1f8")
    return f'''
    <linearGradient id="{uid}bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{top}"/><stop offset="0.55" stop-color="{mid}"/><stop offset="1" stop-color="{bot}"/>
    </linearGradient>
    <radialGradient id="{uid}bh" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{hue}" stop-opacity="{t['blob_hue']}"/><stop offset="1" stop-color="{hue}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="{uid}ba" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{accent}" stop-opacity="{t['blob_acc']}"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="{uid}tile" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="{t['tile_a']}"/><stop offset="1" stop-color="#ffffff" stop-opacity="{t['tile_b']}"/>
    </linearGradient>
    <linearGradient id="{uid}rim" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="{t['rim_a']}"/><stop offset="0.45" stop-color="#ffffff" stop-opacity="{t['rim_b']}"/><stop offset="1" stop-color="#ffffff" stop-opacity="{t['rim_c']}"/>
    </linearGradient>
    <linearGradient id="{uid}pill" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{accent}"/><stop offset="1" stop-color="{accent}" stop-opacity="0.78"/>
    </linearGradient>'''


def style_common(t: dict, extra: str = "") -> str:
    return f'''<style>
    {font_face()}
    .t{{font-family:{FONT};fill:{t['ink']};}}
    .tg{{font-family:{FONT};}}
    .b1{{animation:drift1 26s ease-in-out infinite alternate;animation-delay:0s;}}
    .b2{{animation:drift2 31s ease-in-out infinite alternate;animation-delay:0s;}}
    .rise{{opacity:0;animation:rise .9s cubic-bezier(.2,.7,.2,1) forwards;animation-delay:0s;}}
    @keyframes drift1{{from{{transform:translate(0,0)}}to{{transform:translate(70px,-30px)}}}}
    @keyframes drift2{{from{{transform:translate(0,0)}}to{{transform:translate(-80px,40px)}}}}
    @keyframes rise{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:translateY(0)}}}}
    {extra}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.rise,.word{{opacity:1}}}}
  </style>'''


def tile(uid: str, x: float, y: float, size: float, radius: float, icon: str) -> str:
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" rx="{radius}" '
            f'fill="url(#{uid}tile)" stroke="url(#{uid}rim)" stroke-width="1.5" filter="url(#{uid}shadow)"/>{icon}')


def filters(uid: str, t: dict, blur: int = 60) -> str:
    return f'''
    <filter id="{uid}blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{blur}"/></filter>
    <filter id="{uid}shadow" x="-30%" y="-40%" width="160%" height="220%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000000" flood-opacity="{t['shadow']}"/></filter>'''


def wordmark(cfg: dict, t: dict, uid: str, cx: float, y: float, size: int, light: bool) -> tuple[str, str, str]:
    """The phrase of the page, centred at `cx`: Sora 650, a quiet two-tone gradient, a faint glow and a soft
    rise on load. Returns (defs, css, body)."""
    word = cfg["phrase"]
    ww = text_w(word, size, 650)
    c1, c2 = ("#b8512f", "#4f58c4") if light else ("#ffd3c4", "#c8c6ff")
    attrs = (f'x="{cx:.0f}" y="{y}" text-anchor="middle" font-size="{size}" font-weight="650" letter-spacing="-0.02em" '
             f'textLength="{ww:.0f}" lengthAdjust="spacingAndGlyphs"')
    defs = f'''
    <linearGradient id="{uid}ink" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>
    </linearGradient>
    <filter id="{uid}glow" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="{size * 0.2:.0f}"/></filter>'''
    css = f'''
    .word{{animation:wordrise 1.4s cubic-bezier(.2,.7,.2,1) forwards;animation-delay:.1s;opacity:0;}}
    @keyframes wordrise{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}'''
    body = f'''
    <g class="word">
      <g filter="url(#{uid}glow)" opacity="{0.35 if light else 0.5}"><text class="tg" fill="url(#{uid}ink)" {attrs}>{esc(word)}</text></g>
      <text class="tg" fill="url(#{uid}ink)" {attrs}>{esc(word)}</text>
    </g>'''
    return defs, css, body


def title_of(cfg: dict) -> str:
    return cfg["phrase"]


def hero_band(cfg: dict, theme: str, w: int = 1280, h: int = 96) -> str:
    """The hero: a glass band with the phrase centred in it, nothing else."""
    t = THEMES[theme]
    light = theme == "light"
    uid = "h-"
    hdefs, hcss, hbody = wordmark(cfg, t, uid, w / 2, h / 2 + 17, 48, light)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title_of(cfg))}">
  <title>{esc(title_of(cfg))}</title>
  <defs>{defs_common(t, uid, BRAND_ACCENT, BRAND_HUE, BRAND_BG, light, pale=True)}{filters(uid, t, 50)}{hdefs}
    <clipPath id="{uid}frame"><rect width="{w}" height="{h}" rx="22"/></clipPath>
  </defs>
  {style_common(t, hcss)}
  <g clip-path="url(#{uid}frame)">
    <rect width="{w}" height="{h}" fill="url(#{uid}bg)"/>
    <g filter="url(#{uid}blur)">
      <circle class="b1" cx="{w * 0.8:.0f}" cy="{h * -0.4:.0f}" r="{h * 1.6:.0f}" fill="url(#{uid}bh)"/>
      <circle class="b2" cx="{w * 0.18:.0f}" cy="{h * 1.4:.0f}" r="{h * 1.3:.0f}" fill="url(#{uid}ba)"/>
    </g>
    <rect width="{w}" height="{h}" rx="22" fill="none" stroke="#ffffff" stroke-opacity="{t['frame']}" stroke-width="1.5"/>
    {hbody}
  </g>
</svg>
'''


def mix(c1: str, c2: str, k: float) -> str:
    """`c1` moved towards `c2` by the fraction `k` (hex colours)."""
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(a, b))


def meta_line(a: dict, cx: float, cy: float, light: bool) -> str:
    """The version chip and the platform glyph of an app on one line centred at (cx, cy): same height, one gap,
    the app's accent at reduced opacity."""
    h, gap, size = 24, 8, 12
    ver = f"v{a['version']}"
    vw = text_w(ver, size, 600) + 22
    total = vw + gap + h
    x0 = cx - total / 2
    y0 = cy - h / 2
    ink = mix(a["accent"], "#0b1020", 0.45) if light else a["accent"]
    fill_op, rim_op = (0.14, 0.45) if light else (0.16, 0.42)
    g = h * 0.44
    gx, gy = x0 + vw + gap + (h - g) / 2, cy - g / 2
    q = g * 0.46
    panes = "".join(f'<rect x="{gx + dx:.1f}" y="{gy + dy:.1f}" width="{q:.1f}" height="{q:.1f}" rx="0.8"/>'
                    for dx, dy in ((0, 0), (g - q, 0), (0, g - q), (g - q, g - q)))
    pill = (f'fill="{a["accent"]}" fill-opacity="{fill_op}" stroke="{a["accent"]}" stroke-opacity="{rim_op}" '
            f'stroke-width="1"')
    return (f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{vw:.1f}" height="{h}" rx="{h / 2}" {pill}/>'
            f'<text class="t" x="{x0 + vw / 2:.1f}" y="{cy + size * 0.35:.1f}" text-anchor="middle" font-size="{size}" '
            f'font-weight="600" style="fill:{ink};fill-opacity:0.92" letter-spacing="0.04em">{esc(ver)}</text>'
            f'<g><title>Windows</title><rect x="{x0 + vw + gap:.1f}" y="{y0:.1f}" width="{h}" height="{h}" rx="{h / 2}" {pill}/>'
            f'<g fill="{ink}" fill-opacity="0.92">{panes}</g></g>')


def download_block(uid: str, a: dict, x_right: float, cy: float, t: dict, delay: float, light: bool) -> str:
    """The download part of a row, centred on `cy` as one group: an accent block with the download mark,
    "Download" and the exe name, and under it the version chip and the platform glyph."""
    bw, bh = 236, 62
    line_gap, line_h = 10, 24
    top = cy - (bh + line_gap + line_h) / 2
    x, y = x_right - bw, top
    bcy = y + bh / 2
    mx = x + 24
    tx = x + 58
    return f'''<g class="rise" style="animation-delay:{delay:.2f}s">
      <rect x="{x:.0f}" y="{y:.0f}" width="{bw}" height="{bh}" rx="18" fill="url(#{uid}pill)" filter="url(#{uid}shadow)"/>
      <path d="M{mx + 8:.0f} {bcy - 10:.0f} v12 m-6 -5 l6 6 l6 -6 M{mx:.0f} {bcy + 9:.0f} h16" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
      <text class="t" x="{tx:.0f}" y="{bcy - 3:.0f}" font-size="18" font-weight="650" style="fill:#ffffff">Download</text>
      <text class="t" x="{tx:.0f}" y="{bcy + 17:.0f}" font-size="13" font-weight="600" style="fill:#ffffff;fill-opacity:0.85" letter-spacing="0.03em">{esc(a['exe'])}</text>
    </g>
    <g class="rise" style="animation-delay:{delay + 0.12:.2f}s">{meta_line(a, x + bw / 2, y + bh + line_gap + line_h / 2, light)}</g>'''


SPLIT = 1000                        # x where a row is cut: the left part links to the repository, the right part to the asset


def row(a: dict, cfg: dict, theme: str, index: int, part: str, w: int = 1280, h: int = 150) -> str:
    """One application row drawn once and cut into two images: `part` "repo" (icon, name, one line; the link
    to the repository) and `part` "get" (the download block with the version chip and the platform glyph under
    it; the link to the latest release asset). Both draw the same background (gradient, blobs, glass) in the
    row's coordinates and show their slice through the viewBox, so the seam is invisible; each part contains
    only its own foreground elements."""
    t = THEMES[theme]
    light = theme == "light"
    uid = "r-"
    tsize = 96
    pad = 28
    ty = (h - tsize) / 2
    tx = pad + tsize + 30
    ny = h / 2 - 4
    d = 0.2 + index * 0.12
    if part == "repo":
        vx, vw_ = 0, SPLIT
        label = f"{a['name']}: {a['line']}"
        front = f'''<g class="rise" style="animation-delay:{d:.2f}s">{tile(uid, pad, ty, tsize, 24, icon_of(a, "ic-", pad, ty, tsize))}</g>
    <g class="rise" style="animation-delay:{d + 0.12:.2f}s">
      <text class="t" x="{tx}" y="{ny:.0f}" font-size="34" font-weight="700" letter-spacing="-0.02em">{esc(a['name'])}</text>
      <text class="t" x="{tx}" y="{ny + 36:.0f}" font-size="19" font-weight="450" fill-opacity="{t['ink2_op']}">{esc(a['line'])}</text>
    </g>'''
    else:
        vx, vw_ = SPLIT, w - SPLIT
        label = f"Download {a['exe']} (v{a['version']}, Windows)"
        front = download_block(uid, a, w - pad, h / 2, t, d + 0.24, light)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{vw_}" height="{h}" viewBox="{vx} 0 {vw_} {h}" role="img" aria-label="{esc(label)}">
  <title>{esc(label)}</title>
  <defs>{defs_common(t, uid, a['accent'], a['hue'], a['bg'], light)}{filters(uid, t, 48)}
    <clipPath id="{uid}frame"><rect width="{w}" height="{h}" rx="26"/></clipPath>
  </defs>
  {style_common(t)}
  <g clip-path="url(#{uid}frame)">
    <rect width="{w}" height="{h}" fill="url(#{uid}bg)"/>
    <g filter="url(#{uid}blur)">
      <circle class="b1" cx="{w * 0.62:.0f}" cy="{h * -0.3:.0f}" r="200" fill="url(#{uid}bh)"/>
      <circle class="b2" cx="{w * 0.3:.0f}" cy="{h * 1.4:.0f}" r="170" fill="url(#{uid}ba)"/>
    </g>
    <rect width="{w}" height="{h}" rx="26" fill="none" stroke="#ffffff" stroke-opacity="{t['frame']}" stroke-width="1.5"/>
    {front}
  </g>
</svg>
'''


# ----------------------------------------------------------------------------------------------- main

def fetch_versions(cfg: dict) -> None:
    for a in cfg["apps"]:
        url = f"https://api.github.com/repos/{cfg['owner']}/{a['repo']}/releases/latest"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-cards"})
        with urllib.request.urlopen(req, timeout=30) as r:
            tag = json.load(r)["tag_name"]
        a["version"] = tag.lstrip("v")
        print(f"{a['repo']}: {tag}")


def readme(cfg: dict, names: dict) -> str:
    """The README: the hero, then per app the repository image and the download image on one line."""
    def pic(key: str, alt: str, width: str) -> str:
        return (f'<picture><source media="(prefers-color-scheme: light)" srcset="assets/{names[key + "-light"]}">'
                f'<img src="assets/{names[key + "-dark"]}" alt="{esc(alt)}" width="{width}"></picture>')
    o = cfg["owner"]
    lines = ['<div align="center">', "", pic("hero", cfg["phrase"], "100%")]
    for a in cfg["apps"]:
        lines.append(f'<a href="https://github.com/{o}/{a["repo"]}">{pic("app-" + a["slug"], a["name"] + ": " + a["line"], "78.125%")}</a>'
                     f'<a href="https://github.com/{o}/{a["repo"]}/releases/latest/download/{a["exe"]}">{pic("get-" + a["slug"], "Download " + a["exe"], "21.875%")}</a>')
    lines += ["", "</div>", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "assets"))
    args = ap.parse_args()
    cfg_path = HERE / "apps.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if args.fetch:
        fetch_versions(cfg)
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # Every file name carries a hash of its content: GitHub's image proxy keeps serving an SVG at an unchanged
    # URL, so a changed asset must change its name. Stale files are removed first.
    for old in out.glob("*.svg"):
        old.unlink()
    names: dict = {}

    def write(key: str, text: str) -> None:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        name = f"{key}.{digest}.svg"
        path = out / name
        path.write_text(text, encoding="utf-8", newline="\n")
        names[key] = name
        print(f"wrote {name} ({path.stat().st_size // 1024} KB)")

    for theme in ("dark", "light"):
        write(f"hero-{theme}", hero_band(cfg, theme))
        for i, a in enumerate(cfg["apps"]):
            write(f"app-{a['slug']}-{theme}", row(a, cfg, theme, i, "repo"))
            write(f"get-{a['slug']}-{theme}", row(a, cfg, theme, i, "get"))
    (ROOT / "README.md").write_text(readme(cfg, names), encoding="utf-8", newline="\n")
    print("wrote README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
