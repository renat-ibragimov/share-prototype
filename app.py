from flask import Flask, jsonify, send_from_directory, send_file, request, render_template_string, url_for
from flask_cors import CORS
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# ---------------------------
# Hardcoded demo data
# ---------------------------
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

# ---------------------------
# Static index
# ---------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# ---------------------------
# API for frontend
# ---------------------------
@app.get("/api/pairs")
def get_pairs():
    return jsonify({"items": PAIRS})

@app.get("/api/pair/<symbol>")
def get_pair(symbol: str):
    sym = symbol.upper()
    if sym in DETAILS:
        return jsonify(DETAILS[sym])
    return jsonify({"error": "Not found"}), 404

# ---------------------------
# Image generation helpers
# ---------------------------
def _font(size: int):
    """Try DejaVuSans if present, else default bitmap font."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def _draw_kv(draw: ImageDraw.ImageDraw, x, y, k, v,
             k_color=(160,170,185), v_color=(230,230,235),
             f1=28, f2=32, right=80, total_w=1200):
    draw.text((x, y), k, font=_font(f1), fill=k_color)
    w = draw.textlength(v, font=_font(f2))
    draw.text((total_w - right - w, y - 4), v, font=_font(f2), fill=v_color)

# ---------------------------
# Share: OG images
# ---------------------------
@app.get("/share/image/top.png")
def share_image_top():
    items = PAIRS
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), (17, 26, 33))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((40, 40, W-40, H-40), radius=24, fill=(31, 36, 48))
    draw.text((80, 70), "Best Performing Overall", font=_font(44), fill=(230,230,235))

    y = 140
    for it in items:
        y2 = y + 80
        draw.rounded_rectangle((80, y, W-80, y2), radius=14, fill=(39, 48, 64))
        draw.text((100, y+22), str(it["rank"]), font=_font(28), fill=(150,160,173))
        draw.text((160, y+14), it["symbol"], font=_font(30), fill=(235,235,240))
        draw.text((160, y+44), it["name"],   font=_font(22), fill=(150,160,173))
        score = f'{it["score"]}% Score'
        apy   = f'{it["apy"]}% APY'
        w1 = draw.textlength(score, font=_font(24))
        w2 = draw.textlength(apy,   font=_font(24))
        draw.text((W-80- w1 - w2 - 28, y+26), score, font=_font(24), fill=(110, 220, 170))
        draw.text((W-80- w2,            y+26), apy,   font=_font(24), fill=(110, 220, 170))
        y = y2 + 12
        if y > 520:
            break

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.get("/share/image/pair/<symbol>.png")
def share_image_pair(symbol):
    d = DETAILS.get(symbol.upper())
    if not d:
        return jsonify({"error": "Not found"}), 404

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), (17, 26, 33))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((40, 40, W-40, H-40), radius=24, fill=(31, 36, 48))
    head = f'{d["name"]} ({d["symbol"]})'
    draw.text((80, 70), head, font=_font(44), fill=(235,235,240))
    draw.text((80, 120), f'Trading Score {d["score"]}%', font=_font(26), fill=(110,220,170))

    price_line = f'${d["price"]:,.2f}'
    draw.text((80, 180), price_line, font=_font(56), fill=(235,235,240))
    # change pct right after price
    px_w = draw.textlength(price_line, font=_font(56))
    ch = "▲" if d["change_pct"] >= 0 else "▼"
    color = (110,220,170) if d["change_pct"] >= 0 else (240,120,120)
    draw.text((80 + px_w + 20, 190), f"{ch} {d['change_pct']}%", font=_font(28), fill=color)

    base_y = 270
    _draw_kv(draw, 80, base_y + 0,   "Binance Volume (24h)", f'${d["volume_24h"]:,.0f}')
    _draw_kv(draw, 80, base_y + 50,  "Cap", f'${d["cap"]:,.0f}')
    _draw_kv(draw, 80, base_y + 100, "Volatility", f'{d["volatility"]}%')
    _draw_kv(draw, 80, base_y + 150, "Trend", f'{d["trend_pct"]}%')
    _draw_kv(draw, 80, base_y + 200, "In Channel", "Yes" if d["in_channel"] else "No")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# ---------------------------
# Share: pages with OG/Twitter tags
# ---------------------------
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
    image = base + url_for("share_image_top")
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
    image = base + url_for("share_image_pair", symbol=symbol.upper())
    app_url = base + f"/#/{symbol.upper()}"
    html = render_template_string(
        SHARE_PAGE_TPL,
        title=f'{d["name"]} ({d["symbol"]}) — Trading Analysis',
        desc=f'Price ${d["price"]:.2f} · Score {d["score"]}% · Volatility {d["volatility"]}%',
        image=image,
        app_url=app_url,
    )
    return html

# ---------------------------
# Share: API for frontend buttons
# ---------------------------
def _share_payload(kind: str, symbol: str | None = None):
    base = request.url_root.rstrip("/")
    if kind == "top":
        page = f"{base}/share/top"
        image = f"{base}/share/image/top.png"
        title = "Best Performing Overall — Crypto Prototype"
    else:
        page = f"{base}/share/pair/{symbol}"
        image = f"{base}/share/image/pair/{symbol}.png"
        title = f'{DETAILS[symbol]["name"]} ({symbol}) — Trading Analysis'

    tg_url = f"https://t.me/share/url?url={page}&text={title}"
    x_url  = f"https://twitter.com/intent/tweet?text={title}&url={page}"

    return {
        "page_url": page,
        "image_url": image,
        "telegram_url": tg_url,
        "x_url": x_url,
        "title": title,
    }

@app.get("/api/share/top")
def api_share_top():
    return jsonify(_share_payload("top"))

@app.get("/api/share/pair/<symbol>")
def api_share_pair(symbol):
    sym = symbol.upper()
    if sym not in DETAILS:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_share_payload("pair", sym))

# ---------------------------
# Dev server
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
