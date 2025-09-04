import os
import asyncio
import threading
import secrets
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application
from bot_core import build_application  # PTB app su tavo handleriais

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", secrets.token_hex(16))
SERVICE_URL = os.environ.get("SERVICE_URL", "").rstrip("/")

application: Application = build_application()

app = Flask(__name__)
_loop = asyncio.new_event_loop()

def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

threading.Thread(target=_run_loop, daemon=True).start()

# startinam PTB be pollingo
asyncio.run_coroutine_threadsafe(application.initialize(), _loop)
asyncio.run_coroutine_threadsafe(application.start(), _loop)

@app.get("/")
def root():
    return {"ok": True, "service": "tvarkdarys", "secret": WEBHOOK_SECRET[:6] + "..."}

@app.get(f"/set/{WEBHOOK_SECRET}")
def set_webhook():
    if not SERVICE_URL:
        return jsonify({"error": "SERVICE_URL env not set"}), 500
    url = f"{SERVICE_URL}/webhook/{WEBHOOK_SECRET}"
    fut = asyncio.run_coroutine_threadsafe(application.bot.set_webhook(url), _loop)
    try:
        ok = fut.result(timeout=15)
        return jsonify({"set_webhook": ok, "url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get(f"/delete/{WEBHOOK_SECRET}")
def delete_webhook():
    fut = asyncio.run_coroutine_threadsafe(
        application.bot.delete_webhook(drop_pending_updates=True), _loop
    )
    try:
        ok = fut.result(timeout=15)
        return jsonify({"delete_webhook": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    data = request.get_json(force=True, silent=False)
    update = Update.de_json(data, application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), _loop)
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    if SERVICE_URL:
        try:
            asyncio.get_event_loop().run_until_complete(
                application.bot.set_webhook(f"{SERVICE_URL}/webhook/{WEBHOOK_SECRET}")
            )
        except Exception:
            pass
    app.run(host="0.0.0.0", port=port)
