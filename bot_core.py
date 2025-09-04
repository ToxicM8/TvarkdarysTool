# bot_core.py
import os
import asyncio
import threading

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==== Env
BOT_TOKEN = os.environ["BOT_TOKEN"]
SERVICE_URL = os.environ.get("SERVICE_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

# ==== PTB application (v20+)
application: Application = (
    Application.builder()
    .token(BOT_TOKEN)
    .build()
)

# -- paprasti handleriai testui
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Botas gyvas! (/start OK)")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("ping", ping_cmd))

# ==== Flask app (šito ieško Gunicorn: bot_core:app)
app = Flask(__name__)

# Turėsim atskirą event loop'ą PTB aplikacijai
_loop = asyncio.new_event_loop()

def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

# Paleidžiam atskirą event loop giją ir startuojam PTB
threading.Thread(target=_run_loop, daemon=True).start()

# initialize + start PTB application ant to loop'o
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)

# ==== Healthcheck
@app.get("/")
def index():
    return jsonify(ok=True, service="tvarkdarys", has_service_url=bool(SERVICE_URL))

# ==== Webhook nustatyti / ištrinti (patogu Cloud Run'ui)
@app.get(f"/set/{WEBHOOK_SECRET}")
def set_webhook():
    if not SERVICE_URL:
        return jsonify({"error": "SERVICE_URL env not set"}), 400
    url = f"{SERVICE_URL}/webhook/{WEBHOOK_SECRET}"
    fut = asyncio.run_coroutine_threadsafe(
        application.bot.set_webhook(url, drop_pending_updates=True),
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
        return jsonify({"delete_webhook": ok}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==== Tikras Telegram webhook endpointas
@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    # Telegram turi siųsti JSON body
    data = request.get_json(force=True, silent=False)
    if not data:
        return "no data", 400

    # Konstruojam Update ir paduodam PTB aplikacijai
    update = Update.de_json(data, application.bot)
    asyncio.run_coroutine_threadsafe(
        application.process_update(update),
        _loop,
    )
    # Svarbu greitai atsakyti 200, Telegram to tikisi
    return "ok", 200

# Lokaliai paleidžiant (ne Cloud Run)
if __name__ == "__main__":
    # Cloud Run klausosi per $PORT, bet lokaliai galima fiksuot 8080
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
