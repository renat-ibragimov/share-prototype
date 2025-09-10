from io import BytesIO
from typing import Optional
import os

from flask import (
    Flask,
    jsonify,
    send_from_directory,
    send_file,
    request,
    render_template_string,
    url_for,
)
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# =========================
# Config / cache-busting
# =========================
APP_ASSET_VERSION = "v5"         # меняй при каждом редизайне
DEFAULT_STYLE = "neo"            # "neo" (фон из файла), "classic", "violet"

def bust(url: str) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}v={APP_ASSET_VERSION}"

def nocache_png_response(buf: BytesIO):
    resp = send_file(buf, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

# =========================
# Data
# =========================
PAIRS = [
    {"rank": 1, "symbol": "BTC", "name": "Bitcoin",  "score": 94, "apy": 245},
    {"rank": 2, "symbol": "ETH", "name": "Ethereum", "score": 89, "apy": 189},
    {"rank": 3, "symbol": "SOL", "name": "Solana",   "score": 87, "apy": 167},
    {"rank": 4, "symbol": "XRP", "name": "Ripple",   "score": 85, "apy": 158},
    {"rank": 5, "symbol": "DOGE","name": "Dogecoin", "score": 82, "apy": 143},
]

DETAILS = {
    "BTC": {
        "symbol": "BTC", "name": "Bitcoin", "score": 94, "price": 43285.12,
        "change_pct": 2.3, "volume_24h": 28943150, "cap": 847392847,
        "volatility": 8.5, "trend_pct": 52.1, "in_channel": True, "exchange": "Binance"
    },
    "ETH": {
        "symbol": "ETH", "name": "Ethereum", "score": 89, "price": 3125.40,
        "change_pct": 1.7, "volume_24h": 14211320, "cap": 402392111,
        "volatility": 9.2, "trend_pct": 48.0, "in_channel": True, "exchange": "Binance"
    },
    "SOL": {
        "symbol": "SOL", "name": "Solana", "score": 87, "price": 112.75,
        "change_pct": 3.1, "volume_24h": 8123411, "cap": 50011222,
        "volatility": 11.0, "trend_pct": 55.4, "in_channel": True, "exchange": "Binance"
    },
    "XRP": {
        "symbol": "XRP", "name": "Ripple", "score": 85, "price": 0.68,
        "change_pct": -0.6, "volume_24h": 5123980, "cap": 35200111,
        "volatility": 7.8, "trend_pct": 41.2, "in_channel": False, "exchange": "Binance"
    },
    "DOGE": {
        "symbol": "DOGE", "name": "Dogecoin", "score": 82, "price": 0.19,
        "change_pct": 0.9, "volume_24h": 3894112, "cap": 26221111,
        "volatility": 10.2, "trend_pct": 39.7, "in_channel": True, "exchange": "Binance"
    },
}

# =========================
# Static index
# =========================
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# =========================
# API for frontend
# =========================
@app.get("/api/pairs")
def get_pairs():
    return jsonify({"items": PAIRS})

@app.get("/api/pair/<symbol>")
def get_pair(symbol: str):
    sym = symbol.upper()
    if sym in DETAILS:
        return jsonify(DETAILS[sym])
    return jsonify({"error": "Not found"}), 404

# =========================
# Pillow helpers
# =========================
def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def _text_w(draw: ImageDraw.ImageDraw, text: str, size: int) -> float:
    return draw.textlength(text, font=_font(size))

def _fit_text(draw, text, max_width, base_size, min_size=14, step=-2):
    s = base_size
    while s >= min_size:
        f = _font(s)
        if draw.textlength(text, font=f) <= max_width:
            return f
        s += step
    return _font(min_size)

def _draw_kv(draw: ImageDraw.ImageDraw, x, y, k, v,
             k_color=(160,170,185), v_color=(230,230,235),
             f1=28, f2=32, right=80, total_w=1200):
    draw.text((x, y), k, font=_font(f1), fill=k_color)
    w = draw.textlength(v, font=_font(f2))
    draw.text((total_w - right - w, y - 4), v, font=_font(f2), fill=v_color)

def _get_bg_rgba() -> Image.Image:
    """Load 1200x630 bg from static/share_bg/neo_bg.png; fall back to gradient."""
    W, H = 1200, 630
    p = os.path.join(app.root_path, "static", "share_bg", "neo_bg.png")
    if os.path.exists(p):
        bg = Image.open(p).convert("RGBA").resize((W, H), Image.LANCZOS)
    else:
        # fallback subtle gradient
        bg = Image.new("RGBA", (W, H))
        base = Image.new("RGB", (W, H), (11, 15, 25))
        top  = Image.new("RGB", (W, H), (27, 16, 51))
        m = Image.new("L", (W, H))
        md = ImageDraw.Draw(m)
        for y in range(H):
            md.line([(0, y), (W, y)], fill=int(255 * (y / (H-1))))
        base.paste(top, (0, 0), m)
        bg = base.convert("RGBA")
    return bg

def _rounded_overlay(rect, radius=28, fill=(0,0,0,180)):
    """Semi-transparent rounded rectangle overlay as separate image layer."""
    x1, y1, x2, y2 = rect
    w, h = x2 - x1, y2 - y1
    ov = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle((0, 0, w, h), radius=radius, fill=fill)
    return ov

def _draw_coin_badge(draw, cx, cy, symbol: str, r=16):
    """Simple circular badge with ticker letters."""
    # outer glow ring
    draw.ellipse((cx-r-3, cy-r-3, cx+r+3, cy+r+3), fill=(28, 38, 58, 180))
    # inner disk
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(120, 90, 220, 255))
    # highlight
    draw.ellipse((cx-r, cy-r, cx+r, cy-r+int(r*0.7)), fill=(160, 130, 255, 100))
    # ticker text
    t = (symbol or "?")[:4]
    f = _font(14)
    w = draw.textlength(t, font=f)
    draw.text((cx - w/2, cy - 8), t, font=f, fill=(245,245,250,255))

# =========================
# RENDERERS
# =========================
def render_top_classic(items):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), (17, 26, 33)).convert("RGBA")
    ov  = _rounded_overlay((40,40,1160,590), radius=24, fill=(31,36,48,255))
    img.alpha_composite(ov, (40,40))
    d = ImageDraw.Draw(img)
    d.text((80, 70), "Best Performing Overall", font=_font(44), fill=(230,230,235,255))
    y = 140
    for it in items[:5]:
        y2 = y + 80
        rr = _rounded_overlay((0,0,1040,80), radius=14, fill=(39,48,64,255))
        img.alpha_composite(rr, (80, y))
        d.text((100, y+22), str(it["rank"]), font=_font(28), fill=(150,160,173,255))
        d.text((160, y+14), it["symbol"], font=_font(30), fill=(235,235,240,255))
        d.text((160, y+44), it["name"],   font=_font(22), fill=(150,160,173,255))
        score = f'{it["score"]}% Score'; apy = f'{it["apy"]}% APY'
        w1 = _text_w(d, score, 24); w2 = _text_w(d, apy, 24)
        d.text((1120- w1 - w2 - 28, y+26), score, font=_font(24), fill=(110,220,170,255))
        d.text((1120- w2,            y+26), apy,   font=_font(24), fill=(110,220,170,255))
        y = y2 + 12
        if y > 520: break
    buf = BytesIO(); img.save(buf, "PNG"); buf.seek(0); return buf

def render_pair_classic(dct: dict):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), (17, 26, 33)).convert("RGBA")
    ov  = _rounded_overlay((40,40,1160,590), radius=24, fill=(31,36,48,255))
    img.alpha_composite(ov, (40,40))
    d = ImageDraw.Draw(img)
    head = f'{dct["name"]} ({dct["symbol"]})'
    d.text((80, 70), head, font=_font(44), fill=(235,235,240,255))
    d.text((80, 120), f'Trading Score {dct["score"]}%', font=_font(26), fill=(110,220,170,255))
    price_line = f'${dct["price"]:,.2f}'
    d.text((80, 180), price_line, font=_font(56), fill=(235,235,240,255))
    px_w = _text_w(d, price_line, 56)
    ch = "▲" if dct["change_pct"] >= 0 else "▼"
    color = (110,220,170,255) if dct["change_pct"] >= 0 else (240,120,120,255)
    d.text((80 + px_w + 20, 190), f"{ch} {dct['change_pct']}%", font=_font(28), fill=color)
    base_y = 270
    _draw_kv(d, 80, base_y +   0, "Binance Volume (24h)", f'${dct["volume_24h"]:,.0f}')
    _draw_kv(d, 80, base_y +  50, "Cap",                   f'${dct["cap"]:,.0f}')
    _draw_kv(d, 80, base_y + 100, "Volatility",            f'{dct["volatility"]}%')
    _draw_kv(d, 80, base_y + 150, "Trend",                 f'{dct["trend_pct"]}%')
    _draw_kv(d, 80, base_y + 200, "In Channel",            "Yes" if dct["in_channel"] else "No")
    buf = BytesIO(); img.save(buf, "PNG"); buf.seek(0); return buf

def render_top_neo(items):
    """Top-5 over photographic/illustrative background."""
    W, H = 1200, 630
    bg = _get_bg_rgba()
    img = bg.copy()
    # translucent content card
    ov = _rounded_overlay((40,40,1160,590), radius=28, fill=(18,22,30,200))
    img.alpha_composite(ov, (40,40))
    d = ImageDraw.Draw(img)
    # header
    title = "TOP 5 CRYPTO"
    d.text((80, 70), title, font=_fit_text(d, title, 740, 64), fill=(236,240,244,255))
    d.text((80, 128), "Best Performing Overall", font=_font(26), fill=(168,176,190,255))
    # list container
    list_ov = _rounded_overlay((70,180,1130,500), radius=20, fill=(26,32,44,180))
    img.alpha_composite(list_ov, (70,180))
    y = 195
    for it in items[:5]:
        row = _rounded_overlay((0,0,1040,52), radius=12, fill=(36,44,58,210))
        img.alpha_composite(row, (90, y))
        # coin badge + rank
        d.text((106, y+16), f"{it['rank']}", font=_font(18), fill=(160,170,185,255))
        _draw_coin_badge(d, 145, y+26, it["symbol"], r=15)
        # symbol/name
        d.text((170, y+8),  it["symbol"], font=_font(24), fill=(236,240,244,255))
        d.text((170, y+28), it["name"],   font=_font(16), fill=(160,170,185,255))
        # right side badges
        score = f"{it['score']}% Score"; apy = f"{it['apy']}% APY"
        w2 = _text_w(d, apy, 20); w1 = _text_w(d, score, 20); px = 1110
        d.text((px - w2,           y+16), apy,   font=_font(20), fill=(120,230,180,255))
        d.text((px - w2 - 18 - w1, y+16), score, font=_font(20), fill=(120,230,180,255))
        y += 60
    # footer
    tagline = "See details in GT-App and trade smarter"
    tf = _fit_text(d, tagline, W-200, 26); tw = d.textlength(tagline, font=tf)
    d.text(((W-tw)//2, 510), tagline, font=tf, fill=(210,220,235,230))
    buf = BytesIO(); img.convert("RGB").save(buf, "PNG"); buf.seek(0); return buf

def render_pair_neo(dct: dict):
    W, H = 1200, 630
    bg = _get_bg_rgba()
    img = bg.copy()
    ov = _rounded_overlay((40,40,1160,590), radius=28, fill=(18,22,30,200))
    img.alpha_composite(ov, (40,40))
    d = ImageDraw.Draw(img)
    # header + badge
    head = f'{dct["name"]} ({dct["symbol"]})'
    d.text((80, 70), head, font=_fit_text(d, head, 760, 56), fill=(236,240,244,255))
    d.text((80, 124), f'Trading Score {dct["score"]}%', font=_font(26), fill=(120,230,180,255))
    _draw_coin_badge(d, 40+1060, 70, dct["symbol"], r=18)  # маленький бейдж справа-верх
    # price + change
    price_line = f'${dct["price"]:,.2f}'
    d.text((80, 180), price_line, font=_font(60), fill=(236,240,244,255))
    px_w = _text_w(d, price_line, 60)
    ch = "▲" if dct["change_pct"] >= 0 else "▼"
    color = (120,230,180,255) if dct["change_pct"] >= 0 else (240,120,120,255)
    d.text((80 + px_w + 20, 192), f"{ch} {dct['change_pct']}%", font=_font(30), fill=color)
    # divider
    d.rounded_rectangle((80, 232, 1120, 246), radius=8, fill=(60,66,80,200))
    # k/v grid
    base_y = 270
    _draw_kv(d, 80, base_y +   0, "Binance Volume (24h)", f'${dct["volume_24h"]:,.0f}', k_color=(175,180,195), v_color=(236,240,244))
    _draw_kv(d, 80, base_y +  50, "Cap",                   f'${dct["cap"]:,.0f}',        k_color=(175,180,195), v_color=(236,240,244))
    _draw_kv(d, 80, base_y + 100, "Volatility",            f'{dct["volatility"]}%',      k_color=(175,180,195), v_color=(236,240,244))
    _draw_kv(d, 80, base_y + 150, "Trend",                 f'{dct["trend_pct"]}%',       k_color=(175,180,195), v_color=(236,240,244))
    _draw_kv(d, 80, base_y + 200, "In Channel",            "Yes" if dct["in_channel"] else "No", k_color=(175,180,195), v_color=(236,240,244))
    buf = BytesIO(); img.convert("RGB").save(buf, "PNG"); buf.seek(0); return buf

# ====== old violet (optional) ======
def _linear_gradient(width, height, start_color, end_color):
    base = Image.new("RGB", (width, height), start_color)
    top = Image.new("RGB", (width, height), end_color)
    mask = Image.new("L", (width, height))
    m = ImageDraw.Draw(mask)
    for y in range(height):
        alpha = int(255 * (y / max(1, height-1)))
        m.line([(0, y), (width, y)], fill=alpha)
    base.paste(top, (0, 0), mask)
    return base

def render_top_violet(items):
    W, H = 1200, 630
    img = _linear_gradient(W, H, (12,10,20), (30,15,60)).convert("RGBA")
    ov = _rounded_overlay((40,40,1160,590), radius=28, fill=(26,20,46,255))
    img.alpha_composite(ov, (40,40))
    d = ImageDraw.Draw(img)
    d.text((80, 70), "TOP 5 CRYPTO!", font=_fit_text(d, "TOP 5 CRYPTO!", 700, 72), fill=(245,240,255,255))
    d.text((80, 130), "Best Performing Overall", font=_font(28), fill=(180,165,230,255))
    list_ov = _rounded_overlay((70,180,1130,500), radius=22, fill=(36,28,64,255))
    img.alpha_composite(list_ov, (70,180))
    y = 195
    for it in items[:5]:
        row = _rounded_overlay((0,0,1040,52), radius=12, fill=(46,38,78,255))
        img.alpha_composite(row, (90, y))
        d.text((106, y+14), f"#{it['rank']}", font=_font(22), fill=(160,150,210,255))
        d.text((170, y+8),  it["symbol"], font=_font(26), fill=(245,242,255,255))
        d.text((170, y+30), it["name"],   font=_font(18), fill=(170,160,210,255))
        score = f"{it['score']}% Score"; apy = f"{it['apy']}% APY"
        w2 = _text_w(d, apy, 22); w1 = _text_w(d, score, 22); px = 1110
        d.text((px - w2,           y+14), apy,   font=_font(22), fill=(120,230,180,255))
        d.text((px - w2 - 20 - w1, y+14), score, font=_font(22), fill=(120,230,180,255))
        y += 56
    buf = BytesIO(); img.convert("RGB").save(buf, "PNG"); buf.seek(0); return buf

def render_pair_violet(dct):
    W,H=1200,630
    img = _linear_gradient(W,H,(12,10,20),(30,15,60)).convert("RGBA")
    ov = _rounded_overlay((40,40,1160,590), radius=28, fill=(26,20,46,255))
    img.alpha_composite(ov, (40,40))
    d = ImageDraw.Draw(img)
    head = f'{dct["name"]} ({dct["symbol"]})'
    d.text((80,70), head, font=_fit_text(d, head, 700, 56), fill=(245,242,255,255))
    d.text((80,120), f'Trading Score {dct["score"]}%', font=_font(28), fill=(120,230,180,255))
    price_line = f'${dct["price"]:,.2f}'
    d.text((80,180), price_line, font=_font(60), fill=(245,245,248,255))
    px_w = _text_w(d, price_line, 60)
    ch = "▲" if dct["change_pct"]>=0 else "▼"
    color = (120,230,180,255) if dct["change_pct"]>=0 else (240,120,120,255)
    d.text((80+px_w+20,192), f"{ch} {dct['change_pct']}%", font=_font(30), fill=color)
    base_y=270
    _draw_kv(d, 80, base_y+0,   "Binance Volume (24h)", f'${dct["volume_24h"]:,.0f}', k_color=(175,170,210), v_color=(236,240,244))
    _draw_kv(d, 80, base_y+50,  "Cap",                   f'${dct["cap"]:,.0f}',        k_color=(175,170,210), v_color=(236,240,244))
    _draw_kv(d, 80, base_y+100, "Volatility",            f'{dct["volatility"]}%',      k_color=(175,170,210), v_color=(236,240,244))
    _draw_kv(d, 80, base_y+150, "Trend",                 f'{dct["trend_pct"]}%',       k_color=(175,170,210), v_color=(236,240,244))
    _draw_kv(d, 80, base_y+200, "In Channel",            "Yes" if dct["in_channel"] else "No", k_color=(175,170,210), v_color=(236,240,244))
    buf = BytesIO(); img.convert("RGB").save(buf, "PNG"); buf.seek(0); return buf

# =========================
# Share: OG images
# =========================
@app.get("/share/image/top.png")
def share_image_top():
    style = request.args.get("style", DEFAULT_STYLE).lower()
    if style == "classic":
        buf = render_top_classic(PAIRS)
    elif style == "violet":
        buf = render_top_violet(PAIRS)
    else:
        buf = render_top_neo(PAIRS)
    return nocache_png_response(buf)

@app.get("/share/image/pair/<symbol>.png")
def share_image_pair(symbol):
    d = DETAILS.get(symbol.upper())
    if not d:
        return jsonify({"error": "Not found"}), 404
    style = request.args.get("style", DEFAULT_STYLE).lower()
    if style == "classic":
        buf = render_pair_classic(d)
    elif style == "violet":
        buf = render_pair_violet(d)
    else:
        buf = render_pair_neo(d)
    return nocache_png_response(buf)

# =========================
# Share: OG pages
# =========================
SHARE_PAGE_TPL = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{title}}</title>
  <meta property="og:type" content="website">
  <meta property="og:title" content="{{title}}">
  <meta property="og:description" content="{{desc}}">
  <meta property="og:image" content="{{image}}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{{title}}">
  <meta name="twitter:description" content="{{desc}}">
  <meta name="twitter:image" content="{{image}}">
</head>
<body style="margin:0;background:#0f1115;color:#e6e6e6;font-family:sans-serif">
  <div style="padding:24px">
    <p>Sharing preview. Open the app → <a href="{{app_url}}" style="color:#22c55e">{{app_url}}</a></p>
    <script>location.href="{{app_url}}";</script>
  </div>
</body>
</html>
"""

@app.get("/share/top")
def share_top_page():
    base = request.url_root.rstrip("/")
    image = bust(base + url_for("share_image_top") + f"?style={DEFAULT_STYLE}")
    app_url = base + "/"
    html = render_template_string(
        SHARE_PAGE_TPL,
        title="Best Performing Overall — Crypto Prototype",
        desc="Top 5 coins by trading score and APY.",
        image=image,
        app_url=app_url,
    )
    return html

@app.get("/share/pair/<symbol>")
def share_pair_page(symbol):
    d = DETAILS.get(symbol.upper())
    if not d:
        return "Not Found", 404
    base = request.url_root.rstrip("/")
    image = bust(base + url_for("share_image_pair", symbol=symbol.upper()) + f"?style={DEFAULT_STYLE}")
    app_url = base + f"/#/{symbol.upper()}"
    html = render_template_string(
        SHARE_PAGE_TPL,
        title=f'{d["name"]} ({d["symbol"]}) — Trading Analysis',
        desc=f'Price ${d["price"]:.2f} · Score {d["score"]}% · Volatility {d["volatility"]}%',
        image=image,
        app_url=app_url,
    )
    return html

# =========================
# Share: API for frontend menus
# =========================
def _share_payload(kind: str, symbol: Optional[str] = None):
    base = request.url_root.rstrip("/")
    style_q = f"?style={DEFAULT_STYLE}"
    if kind == "top":
        page  = bust(f"{base}/share/top")
        image = bust(f"{base}/share/image/top.png{style_q}")
        title = "Best Performing Overall — Crypto Prototype"
    else:
        assert symbol is not None
        page  = bust(f"{base}/share/pair/{symbol}")
        image = bust(f"{base}/share/image/pair/{symbol}.png{style_q}")
        title = f'{DETAILS[symbol]["name"]} ({symbol}) — Trading Analysis'
    tg_url = f"https://t.me/share/url?url={page}&text={title}"
    x_url  = f"https://twitter.com/intent/tweet?text={title}&url={page}"
    return {"page_url": page, "image_url": image, "telegram_url": tg_url, "x_url": x_url, "title": title}

@app.get("/api/share/top")
def api_share_top():
    return jsonify(_share_payload("top"))

@app.get("/api/share/pair/<symbol>")
def api_share_pair(symbol):
    sym = symbol.upper()
    if sym not in DETAILS:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_share_payload("pair", sym))

# =========================
# Dev server
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
