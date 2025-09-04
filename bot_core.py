# bot_core.py
import os
import asyncio
import threading
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler

# ==== Env
BOT_TOKEN = os.environ["BOT_TOKEN"]
SERVICE_URL = os.environ.get("SERVICE_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

# ==== PTB application
application: Application = Application.builder().token(BOT_TOKEN).build()

# --- paprasti handleriai testui
async def start_cmd(update, context):
    await update.message.reply_text("✅ Botas gyvas! (/start)")

async def ping_cmd(update, context):
    await update.message.reply_text("pong")

application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("ping", ping_cmd))

# ==== Flask app
app = Flask(__name__)
_loop = asyncio.new_event_loop()

def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

# Paleidžiam atskirą event loop giją ir startuojam PTB
threading.Thread(target=_run_loop, daemon=True).start()
# initialize + start PTB application ant to loop'o
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)

# ---- Healthcheck
@app.get("/")
def index():
    return jsonify(ok=True, service="tvarkdarys", has_url=bool(SERVICE_URL))

# ---- Webhook nustatyti / ištrinti (patogu Cloud Run'e)
@app.get(f"/set/{WEBHOOK_SECRET}")
def set_webhook():
    if not SERVICE_URL:
        return jsonify({"error": "SERVICE_URL env not set"}), 500
    url = f"{SERVICE_URL}/webhook/{WEBHOOK_SECRET}"
    fut = asyncio.run_coroutine_threadsafe(
        application.bot.set_webhook(url),
        _loop,
    )
    try:
        ok = fut.result(timeout=15)
        return jsonify({"set_webhook": ok, "url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get(f"/delete/{WEBHOOK_SECRET}")
def delete_webhook():
    fut = asyncio.run_coroutine_threadsafe(
        application.bot.delete_webhook(drop_pending_updates=True),
        _loop,
    )
    try:
        ok = fut.result(timeout=15)
        return jsonify({"delete_webhook": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---- Tikras Telegram webhook endpointas
@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return "no data", 400

    # PTB v20: reikia paduoti bot'ą
    update = Update.de_json(data, application.bot)

    asyncio.run_coroutine_threadsafe(
        application.process_update(update),
        _loop,
    )
    return "ok", 200

# ⚠️ JOKIO app.run() – gunicorn jį paleidžia.
# Dockerfile CMD turi būti:
# CMD ["gunicorn", "-b", "0.0.0.0:8080", "bot_core:app"]
