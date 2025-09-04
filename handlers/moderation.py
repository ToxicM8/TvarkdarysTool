"""
Moderation command handlers for Tvarkdarys bot
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden

from utils.permissions import admin_required, group_only, can_restrict_user, group_allowed
from utils.storage import BotStorage

logger = logging.getLogger(__name__)

class ModerationHandlers:
    def __init__(self, storage: BotStorage):
        self.storage = storage

    def _extract_user_from_message(self, update: Update) -> Tuple[Optional[object], str]:
        target_user = None
        reason = "No reason provided"
        msg = update.message
        if not msg:
            return None, reason

        if msg.reply_to_message:
            target_user = msg.reply_to_message.from_user
            parts = msg.text.split(maxsplit=1)
            if len(parts) > 1:
                reason = parts[1].strip()
            return target_user, reason

        parts = msg.text.split()
        args = parts[1:] if len(parts) > 1 else []
        if not args:
            return None, reason

        user_identifier = args[0]
        if len(args) > 1:
            reason = " ".join(args[1:]).strip() or reason

        if user_identifier.isdigit():
            user_id = int(user_identifier)
            class MinimalUser:
                def __init__(self, uid: int):
                    self.id = uid
                    self.username = None
                    self.first_name = f"User{uid}"
            return MinimalUser(user_id), reason

        return None, "Negaliu rasti pagal @username. Atsakyk į žinutę arba naudok skaitinį user_id."

    async def _send(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, html: bool = True):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="HTML" if html else None,
            disable_web_page_preview=True,
        )

    @group_only
    @group_allowed
    @admin_required
    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_user, reason = self._extract_user_from_message(update)
        if not target_user:
            await self._send(update, context, "❌ Nurodyk naudotoją.\n<b>Naudojimas:</b> <code>/ban &lt;user_id&gt; [priežastis]</code> arba reply su <code>/ban [priežastis]</code>")
            return
        if target_user.id == update.effective_user.id:
            await self._send(update, context, "❌ Nu ką tu čia išsipisinėji?")
            return
        chat_id = update.effective_chat.id
        if not await can_restrict_user(update, context, target_user.id):
            await self._send(update, context, "❌ Negaliu. Taikinys yra admin/creator arba neturiu teisių.")
            return
        try:
            await context.bot.ban_chat_member(chat_id, target_user.id)
            self.storage.ban_user(chat_id, target_user.id)
            text = f"🔨 <b>User Banned</b>\n\n<b>User:</b> {target_user.first_name}"
            if getattr(target_user, 'username', None):
                text += f" (@{target_user.username})"
            text += f"\n<b>ID:</b> <code>{target_user.id}</code>\n<b>Reason:</b> {reason}\n<b>Banned by:</b> {update.effective_user.mention_html()}"
            await self._send(update, context, text)
        except BadRequest as e:
            await self._send(update, context, f"❌ Nepavyko užbaninti: {e}", html=False)
        except Forbidden:
            await self._send(update, context, "❌ Neturiu leidimų ban'inti.")

    @group_only
    @group_allowed
    @admin_required
    async def kick_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_user, reason = self._extract_user_from_message(update)
        if not target_user:
            await self._send(update, context, "❌ Nurodyk naudotoją.\n<b>Naudojimas:</b> <code>/kick &lt;user_id&gt; [priežastis]</code> arba reply su <code>/kick [priežastis]</code>")
            return
        if target_user.id == update.effective_user.id:
            await self._send(update, context, "❌ Nu ką tu čia išsipisinėji?")
            return
        chat_id = update.effective_chat.id
        if not await can_restrict_user(update, context, target_user.id):
            await self._send(update, context, "❌ Negaliu. Taikinys yra admin/creator arba neturiu teisių.")
            return
        try:
            await context.bot.ban_chat_member(chat_id, target_user.id)
            await context.bot.unban_chat_member(chat_id, target_user.id)
            text = f"👢 <b>User Kicked</b>\n\n<b>User:</b> {target_user.first_name}"
            if getattr(target_user, 'username', None):
                text += f" (@{target_user.username})"
            text += f"\n<b>ID:</b> <code>{target_user.id}</code>\n<b>Reason:</b> {reason}\n<b>Kicked by:</b> {update.effective_user.mention_html()}"
            await self._send(update, context, text)
        except BadRequest as e:
            await self._send(update, context, f"❌ Nepavyko išmesti: {e}", html=False)
        except Forbidden:
            await self._send(update, context, "❌ Neturiu leidimų kick'inti.")

    @group_only
    @group_allowed
    @admin_required
    async def unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args or not context.args[0].isdigit():
            await self._send(update, context, "❌ Paduok skaitinį user_id.\n<b>Naudojimas:</b> <code>/unban &lt;user_id&gt;</code>")
            return
        user_id = int(context.args[0])
        chat_id = update.effective_chat.id
        try:
            await context.bot.unban_chat_member(chat_id, user_id)
            self.storage.unban_user(chat_id, user_id)
            await self._send(update, context, f"✅ <b>User Unbanned</b>\n\n<b>User ID:</b> <code>{user_id}</code>\n<b>Unbanned by:</b> {update.effective_user.mention_html()}")
        except BadRequest as e:
            await self._send(update, context, f"❌ Nepavyko atbaninti: {e}", html=False)
        except Forbidden:
            await self._send(update, context, "❌ Neturiu leidimų unban'inti.")

    @group_only
    @group_allowed
    @admin_required
    async def mute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_user, reason = self._extract_user_from_message(update)
        if not target_user:
            await self._send(update, context, "❌ Nurodyk naudotoją.\n<b>Naudojimas:</b> <code>/mute &lt;user_id&gt; [minutes] [priežastis]</code> arba reply su <code>/mute [minutes] [priežastis]</code>")
            return
        duration = 60
        if context.args:
            for a in context.args:
                if a.isdigit():
                    duration = int(a); break
        if target_user.id == update.effective_user.id:
            await self._send(update, context, "❌ NOPE")
            return
        chat_id = update.effective_chat.id
        if not await can_restrict_user(update, context, target_user.id):
            await self._send(update, context, "❌ Negaliu. Taikinys yra admin/creator arba neturiu teisių.")
            return
        try:
            until = datetime.utcnow() + timedelta(minutes=duration)
            perms = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(chat_id=chat_id, user_id=target_user.id, permissions=perms, until_date=until)
            self.storage.mute_user(chat_id, target_user.id, duration)
            text = f"🔇 <b>User Muted</b>\n\n<b>User:</b> {target_user.first_name}"
            if getattr(target_user, 'username', None):
                text += f" (@{target_user.username})"
            text += f"\n<b>ID:</b> <code>{target_user.id}</code>\n<b>Duration:</b> {duration} min\n<b>Reason:</b> {reason}\n<b>Muted by:</b> {update.effective_user.mention_html()}"
            await self._send(update, context, text)
        except BadRequest as e:
            await self._send(update, context, f"❌ Nepavyko užtildyti: {e}", html=False)
        except Forbidden:
            await self._send(update, context, "❌ Neturiu leidimų restrict'inti.")

    @group_only
    @group_allowed
    @admin_required
    async def unmute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_user, _ = self._extract_user_from_message(update)
        if not target_user:
            await self._send(update, context, "❌ Nurodyk naudotoją.\n<b>Naudojimas:</b> <code>/unmute &lt;user_id&gt;</code> arba reply su <code>/unmute</code>")
            return
        chat_id = update.effective_chat.id
        try:
            restore = ChatPermissions(can_send_messages=True)
            await context.bot.restrict_chat_member(chat_id=chat_id, user_id=target_user.id, permissions=restore, until_date=0)
            self.storage.unmute_user(chat_id, target_user.id)
            await self._send(update, context, f"🔊 <b>User Unmuted</b>\n\n<b>User:</b> {target_user.first_name}\n<b>Unmuted by:</b> {update.effective_user.mention_html()}")
        except BadRequest as e:
            await self._send(update, context, f"❌ Nepavyko nuimti mute: {e}", html=False)
        except Forbidden:
            await self._send(update, context, "❌ Neturiu leidimų restrict'inti.")

    @group_only
    @group_allowed
    @admin_required
    async def warn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_user, reason = self._extract_user_from_message(update)
        if not target_user:
            await self._send(update, context, "❌ Nurodyk naudotoją.\n<b>Naudojimas:</b> <code>/warn &lt;user_id&gt; [priežastis]</code> arba reply su <code>/warn [priežastis]</code>")
            return
        if target_user.id == update.effective_user.id:
            await self._send(update, context, "❌ NOPE!")
            return
        chat_id = update.effective_chat.id
        total = self.storage.add_warning(chat_id, target_user.id)
        text = f"⚠️ <b>User Warned</b>\n\n<b>User:</b> {target_user.first_name}"
        if getattr(target_user, 'username', None):
            text += f" (@{target_user.username})"
        text += f"\n<b>ID:</b> <code>{target_user.id}</code>\n<b>Reason:</b> {reason}\n<b>Warnings:</b> {total}/3\n<b>Warned by:</b> {update.effective_user.mention_html()}"
        if total >= 3:
            text += "\n\n🔨 <b>Auto-ban:</b> 3 įspėjimai."
            try:
                await context.bot.ban_chat_member(chat_id, target_user.id)
                self.storage.ban_user(chat_id, target_user.id)
            except Exception as e:
                text += f"\n❌ Nepavyko auto-ban: {e}"
        await self._send(update, context, text)

    @group_only
    @group_allowed
    async def check_warnings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        target_user, _ = self._extract_user_from_message(update)
        if not target_user:
            target_user = update.effective_user
        count = self.storage.get_warnings(target_user.id)
        text = f"⚠️ <b>Warning Status</b>\n\n<b>User:</b> {target_user.first_name}"
        if getattr(target_user, 'username', None):
            text += f" (@{target_user.username})"
        text += f"\n<b>Warnings:</b> {count}/3"
        if count >= 3: text += "\n🔴 <b>Maksimumas viršytas!</b>"
        elif count == 2: text += "\n🟡 <b>Dar vienas – ir ban.</b>"
        elif count == 1: text += "\n🟠 <b>Atsargiau.</b>"
        else: text += "\n🟢 <b>Švaru.</b>"
        await self._send(update, context, text)
