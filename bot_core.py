import os
import asyncio
import threading
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application

# Aplinkos kintamieji
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")

# Sukuriam Application
application: Application = Application.builder().token(BOT_TOKEN).build()

# Flask app
app = Flask(__name__)
_loop = asyncio.new_event_loop()

def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

threading.Thread(target=_run_loop, daemon=True).start()
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)

# Healthcheck
@app.get("/")
def index():
    return jsonify(ok=True, service="tvarkdarys")

# Tikras webhook endpointas
@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return "no data", 400

    update = Update.de_json(data, application.bot)
    asyncio.run_coroutine_threadsafe(
        application.process_update(update),
        _loop
    )
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
