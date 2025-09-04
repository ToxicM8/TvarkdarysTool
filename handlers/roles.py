"""
Role selection handlers: /mergina, /vaikinas, /kas
"""

from telegram import Update
from telegram.ext import ContextTypes
from utils.storage import BotStorage
from utils.permissions import group_only, group_allowed

MERGINA = "mergina"
VAIKINAS = "vaikinas"

class RoleHandlers:
    def __init__(self, storage: BotStorage):
        self.storage = storage

    async def _announce_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, role: str):
        chat_id = update.effective_chat.id
        member = await context.bot.get_chat_member(chat_id, user_id)
        mention = member.user.mention_html()
        role_nice = "👩 Mergina" if role == MERGINA else "🧑 Vaikinas"
        await context.bot.send_message(chat_id=chat_id, text=f"{mention} pasirinko rolę: <b>{role_nice}</b>.", parse_mode="HTML")

    async def _show_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        chat_id = update.effective_chat.id
        udata = self.storage.get_user(user_id)
        role = (udata.role or "").lower()
        if role == MERGINA:
            txt = f"<b>{udata.first_name}</b> rolė: 👩 <b>Mergina</b>"
        elif role == VAIKINAS:
            txt = f"<b>{udata.first_name}</b> rolė: 🧑 <b>Vaikinas</b>"
        else:
            txt = f"<b>{udata.first_name}</b> dar nepasirinko rolės."
        await context.bot.send_message(chat_id=chat_id, text=txt, parse_mode="HTML")

    @group_only
    @group_allowed
    async def mergina_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user: return
        self.storage.set_user_role(user.id, MERGINA)
        await self._announce_role(update, context, user.id, MERGINA)

    @group_only
    @group_allowed
    async def vaikinas_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user: return
        self.storage.set_user_role(user.id, VAIKINAS)
        await self._announce_role(update, context, user.id, VAIKINAS)

    @group_only
    @group_allowed
    async def kas_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user: return
        target_id = user.id
        if update.message and update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
        elif context.args and context.args[0].isdigit():
            target_id = int(context.args[0])
        await self._show_role(update, context, target_id)
