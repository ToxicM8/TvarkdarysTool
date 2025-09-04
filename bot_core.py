import os
import asyncio
import threading
from flask import Flask, jsonify, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==== ENV ====
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
SERVICE_URL = os.environ.get("SERVICE_URL", "").rstrip("/")  # pvz. https://tvarkdarys-tool-xxxx.run.app

# ==== PTB app ====
application: Application = Application.builder().token(BOT_TOKEN).build()

# — testiniai handleriai (pasitikrinimui) —
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Botas gyvas! (/start OK)")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("ping", ping_cmd))

# ==== Flask ====
app = Flask(__name__)

# atskiras event loop PTB aplikacijai
_loop = asyncio.new_event_loop()
def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()
threading.Thread(target=_run_loop, daemon=True).start()

# startinam PTB ant _loop
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)

# ---- Healthcheck (Cloud Run tikrina /) ----
@app.get("/")
def index():
    return jsonify(ok=True, service="tvarkdarys", has_service_url=bool(SERVICE_URL))

# ---- Set webhook (patogu po deploy) ----
@app.get(f"/set/{WEBHOOK_SECRET}")
def set_webhook():
    if not SERVICE_URL:
        return jsonify(ok=False, error="SERVICE_URL env not set"), 400
    url = f"{SERVICE_URL}/webhook/{WEBHOOK_SECRET}"
    fut = asyncio.run_coroutine_threadsafe(application.bot.set_webhook(url), _loop)
    try:
        fut.result(timeout=15)
        return jsonify(ok=True, url=url)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# ---- Tikras Telegram webhook endpointas ----
@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return "no data", 400
    update = Update.de_json(data, application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), _loop)
    return "ok", 200

# ---- Lokalinis paleidimas (Cloud Run irgi gerbia PORT) ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
