import os
import asyncio
import threading
from flask import Flask, jsonify, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==== Env
BOT_TOKEN = os.environ["BOT_TOKEN"]
SERVICE_URL = os.environ.get("SERVICE_URL", "")
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

# ==== PTB application (v20+)
application: Application = (
    Application.builder()
    .token(BOT_TOKEN)
    .build()
)

# -- paprasti handleriai testui
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Botas gyvas!")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("ping", ping_cmd))

# ==== Flask app (čia ieško Gunicorn, bet mes tiesiogiai paleidžiam su python)
app = Flask(__name__)
_loop = asyncio.new_event_loop()

def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

# Paleidžiam atskirą event loop giją ir startuojam PTB
threading.Thread(target=_run_loop, daemon=True).start()
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)

# ==== Healthcheck
@app.get("/")
def index():
    return jsonify(ok=True, service="tvarkdarys", has_token=bool(BOT_TOKEN))

# ==== Webhook nustatyti
@app.get(f"/set/{WEBHOOK_SECRET}")
def set_webhook():
    if not SERVICE_URL:
        return jsonify(ok=False, error="SERVICE_URL missing")
    url = f"{SERVICE_URL}/webhook/{WEBHOOK_SECRET}"
    asyncio.run_coroutine_threadsafe(
        application.bot.set_webhook(url), _loop
    )
    return jsonify(ok=True, webhook_url=url)

# ==== Webhook endpointas
@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify(ok=False)
    asyncio.run_coroutine_threadsafe(
        application.update_queue.put(Update.de_json(data, application.bot)), _loop
    )
    return jsonify(ok=True)

# ==== Main
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
