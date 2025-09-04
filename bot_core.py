import os
from flask import Flask, request, jsonify

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "testsecret")

app = Flask(__name__)

# Healthcheck
@app.get("/")
def index():
    return jsonify(ok=True, service="tvarkdarys")

# Tikras webhook endpointas (tik testui – be Telegram logikos)
@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    data = request.get_json(force=True, silent=True)
    print("Gauta:", data)  # kad matytum loguose
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
