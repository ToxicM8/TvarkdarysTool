import os
from telegram.ext import Application

# ====== Handlerių importai ======
from handlers.commands import register_commands
from handlers.moderation import register_moderation
from handlers.invite_tracker import register_invite_tracker
from handlers.antiflood import register_antiflood
from handlers.report import register_report
from handlers.roles import register_roles
from handlers.xp_system import register_xp_system


# ====== Config ======
TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["BASE_URL"]  # Pvz.: https://tvarkdarys-xxxx.a.run.app
PORT = int(os.environ.get("PORT", "8080"))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "slaptas_zodis")


def build_app() -> Application:
    """Sukuriam ir surišam visus handlerius į vieną appą."""
    application = Application.builder().token(TOKEN).build()

    # registruojam tavo handlerių funkcijas
    register_commands(application)
    register_moderation(application)
    register_invite_tracker(application)
    register_antiflood(application)
    register_report(application)
    register_roles(application)
    register_xp_system(application)

    return application


def main():
    app = build_app()

    # PTB startuoja savo aiohttp serverį webhook'ui
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=f"{BASE_URL}/webhook",
        secret_token=WEBHOOK_SECRET,
    )


if __name__ == "__main__":
    main()
