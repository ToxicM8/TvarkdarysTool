"""
Basic command handlers for Tvarkdarys bot
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils.permissions import admin_required, group_only, rate_limit, group_allowed
from utils.storage import BotStorage
from config import BotConfig

logger = logging.getLogger(__name__)

class CommandHandlers:
    def __init__(self, storage: BotStorage):
        self.storage = storage
        self.owner_id = BotConfig().owner_id

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "Kas driso mane pažadinti? 😈 \n"
            "🔥 Pragaras tavęs laukia."
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode='Markdown')

    @rate_limit(3)
    @group_only
    @group_allowed
    async def pagalba_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "<b>🧠 TVARKDARYS PAGALBA</b>\n\n"

            "<b>🎮 XP sistema:</b>\n"
            "• <code>/xp</code> – Patikrink savo XP ir Level\n"
            "• <code>/xpinfo</code> – Kaip veikia XP sistema\n"
            "• <code>/lyderiai</code> – TOP veikėjai\n\n"

            "<b>👮 Moderacija:</b>\n"
            "• <code>/ban</code>, <code>/kick</code>, <code>/unban</code>\n"
            "• <code>/mute</code>, <code>/unmute</code>, <code>/warn</code>\n"
            "• <code>/ispejimai</code> – Vartotojo įspėjimai\n\n"

            "<b>🎭 Rolės:</b>\n"
            "• <code>/mergina</code> – Pasirinkti 👩 Mergina\n"
            "• <code>/vaikinas</code> – Pasirinkti 🧑 Vaikinas\n"
            "• <code>/kas</code> [reply | user_id] – Parodo pasirinktą rolę\n\n"

            "<b>🚩 Report:</b>\n"
            "• <code>/report</code> [reply | <i>user_id</i>] [priežastis] – Pranešti adminams\n\n"

            "<b>📜 Kiti dalykai:</b>\n"
            "• <code>/taisykles</code> – Pragaro įsakymai\n"
            "• <code>/pagalba</code> – Na va, radai ją 😈\n"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML")

    @group_only
    @group_allowed
    async def rules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "<b>📜 Grupės Taisyklės:</b>\n\n"
            "1. ⛔ Jokios nelegalios veiklos. Narkotikų reklama = banas. Nediskutuojama.\n"
            "2. 📵 Telegram grupių reklama – tabu. Kelk YouTube/IG/memus, bet ne t.me linkus. Banas automatas įkrautas.\n"
            "3. 💬 Gerbk kitus, bet nepersistenk. Sarkazmas – gerai. Įžeidinėjimai – pro duris.\n"
            "4. 🔞 Daliniesi? Būk sąmoningas. Nuogumas – taip. Nepilnamečiai ar iškrypimai – ne.\n"
            "5. 📣 Flood’ini be turinio? XP negausi, geriausiu atveju ignoras, blogiausiu – mute.\n"
            "6. 🕵️‍♀️ Report’ink su /report – staff’ai viską mato, nepiktnaudžiauk.\n"
            "7. 🎭 Rolė: /mergina, /vaikinas, /kas.\n"
            "8. 👑 Demonas – paskutinis žodis."
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode='HTML')

    @rate_limit(3)
    @group_only
    @group_allowed
    async def set_welcome_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tik owner'is gali naudoti /setwelcome"""
        chat_id = update.effective_chat.id
        user = update.effective_user

        if not user or user.id != self.owner_id:
            await context.bot.send_message(chat_id=chat_id, text="❌ Čia tik šeimininkui, bičiuk.")
            return

        if not context.args:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ Įrašyk pasisveikinimo žinutę.\n\n"
                    "<b>Naudojimas:</b> <code>/setwelcome Sveiki atvykę, {user}</code>\n"
                    "<i>{user}</i> bus pakeistas į naujo nario paminėjimą."
                ),
                parse_mode='HTML'
            )
            return

        welcome_msg = " ".join(context.args)
        self.storage.set_welcome_message(chat_id, welcome_msg)

        preview = welcome_msg.replace("{user}", user.mention_html())
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Nustatyta pasisveikinimo žinutė:\n\n{preview}",
            parse_mode='HTML'
        )

    @group_only
    @group_allowed
    async def xpinfo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "<b>📈 XP sistema:</b>\n\n"
            "• Kiekviena žinutė duoda <b>3 XP</b>\n"
            "• <b>1 Level = 1000 XP</b>\n"
            "• Maks. Level – 25 (2,500,000 XP)\n"
            "• XP skirstomi tolygiai tarp lygių\n"
            "• TOP – <code>/lyderiai</code>"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode='HTML')
