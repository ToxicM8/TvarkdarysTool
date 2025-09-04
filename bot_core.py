# bot_core.py
import os
import asyncio
import threading
import secrets

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application

# TAVO botas iš bot.py
from bot import TvarkdaryBot


# ===== Env =====
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", secrets.token_hex(16))
SERVICE_URL = os.environ.get("SERVICE_URL", "").rstrip("/")  # pvz.: https://tvarkdarys-tool-xxxx.run.app

# ===== PTB Application =====
def build_application() -> Application:
    """Sukuria PTB Application su visais tavo handleriais."""
    bot = TvarkdaryBot()
    return bot.application


application: Application = build_application()

# ===== Flask (web serveris) =====
app = Flask(__name__)

# atskiras event loop'as botui
_loop = asyncio.new_event_loop()


def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


# paleidžiam loop'ą atskiram threade
threading.Thread(target=_run_loop, daemon=True).start()

# startinam PTB (be polling – naudosim webhook)
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)


# ---- Healthcheck / root (Cloud Run tikisi 200 iš /) ----
@app.get("/")
def index():
    return jsonify(
        ok=True,
        service="tvarkdarys",
        has_service_url=bool(SERVICE_URL),
        hint="Hit /set/<WEBHOOK_SECRET> once after deploy."
    ), 200


# ---- Set webhook (užkabinam po deploy) ----
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


# ---- Delete webhook (jei prireiks) ----
@app.get(f"/delete/{WEBHOOK_SECRET}")
def delete_webhook():
    fut = asyncio.run_coroutine_threadsafe(
        application.bot.delete_webhook(drop_pending_updates=True),
        _loop,
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


# Lokalus paleidimas (Cloud Run naudoja gunicorn)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
