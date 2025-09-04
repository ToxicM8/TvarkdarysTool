# bot_core.py
import os
import asyncio
import threading
import secrets

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application

# Svarbu: čia importuojam TAVO botą iš bot.py
from bot import TvarkdaryBot


# ==== ENV ====
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", secrets.token_hex(16))
SERVICE_URL = os.environ.get("SERVICE_URL", "").rstrip("/")  # pvz. https://tvarkdarys-tool-xxxx.run.app

# ==== PTB Application ====
def build_application() -> Application:
    """Sukuria PTB app su visais tavo handleriais."""
    bot = TvarkdaryBot()
    return bot.application


application: Application = build_application()

# ==== Flask app (webhook serveris) ====
app = Flask(__name__)

# atskiras event loop'as Telegram botui
_loop = asyncio.new_event_loop()


def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


# paleidžiam loop'ą atskiram threade
threading.Thread(target=_run_loop, daemon=True).start()

# startinam PTB (be long-polling, nes naudosim webhook)
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)


# ---- Health/Root (Cloud Run healthcheck) ----
@app.get("/")
def root():
    return jsonify(
        ok=True,
        service="tvarkdarys",
        webhook_secret=WEBHOOK_SECRET[:6] + "...",
        has_service_url=bool(SERVICE_URL),
    ), 200


# ---- Set webhook (patogu pasileist po deploy) ----
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


# ---- Delete webhook (jei prireiktų) ----
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


# ---- Telegram POST webhook ----
@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    data = request.get_json(force=True, silent=False)
    update = Update.de_json(data, application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), _loop)
    return "ok", 200


# Lokaliam paleidimui (Cloud Run vistiek naudoja gunicorn)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
