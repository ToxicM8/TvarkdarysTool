# bot_core.py
import os, asyncio, threading, secrets
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application
from bot import TvarkdaryBot  # <-- Tavo bot.py failo klasė

# ENV
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", secrets.token_hex(16))
SERVICE_URL = os.environ.get("SERVICE_URL", "").rstrip("/")

# Sukuriam PTB Application (be jokių run_polling – čia nenaudojam)
def build_application() -> Application:
    return TvarkdaryBot().application

application: Application = build_application()

# Flask app – būtent šitas objektas turi vadintis "app"
app = Flask(__name__)

# Atidarom event loop atskiram threade
_loop = asyncio.new_event_loop()
def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

threading.Thread(target=_run_loop, daemon=True).start()
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)

# Healthcheck + info
@app.get("/")
def index():
    return jsonify(ok=True, service="tvarkdarys", has_service_url=bool(SERVICE_URL)), 200

# Webhook set/delete (naudinga Cloud Run’ui)
@app.get(f"/set/{WEBHOOK_SECRET}")
def set_webhook():
    if not SERVICE_URL:
        return jsonify({"error": "SERVICE_URL env not set"}), 500
    url = f"{SERVICE_URL}/webhook/{WEBHOOK_SECRET}"
    fut = asyncio.run_coroutine_threadsafe(application.bot.set_webhook(url), _loop)
    try:
        ok = fut.result(timeout=15)
        return jsonify({"set_webhook": ok, "url": url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get(f"/delete/{WEBHOOK_SECRET}")
def delete_webhook():
    fut = asyncio.run_coroutine_threadsafe(
        application.bot.delete_webhook(drop_pending_updates=True), _loop
    )
    try:
        ok = fut.result(timeout=15)
        return jsonify({"delete_webhook": ok}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Tikras Telegram webhook endpointas
@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    data = request.get_json(force=True, silent=False)
    update = Update.de_json(data, application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), _loop)
    return "ok", 200

# Vietinis paleidimas (nereikia Cloud Run’ui, bet netrukdo)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
