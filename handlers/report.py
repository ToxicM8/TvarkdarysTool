"""
Report command handler for Tvarkdarys bot
"""

import html
import logging
from typing import Optional, Tuple

from telegram import Update
from telegram.ext import ContextTypes
from config import BotConfig
from utils.storage import BotStorage
from utils.permissions import group_only, group_allowed

logger = logging.getLogger(__name__)

class ReportHandlers:
    def __init__(self, storage: BotStorage):
        self.storage = storage
        self.owner_id = BotConfig().owner_id

    def _extract_target(self, update: Update) -> Tuple[Optional[int], str]:
        msg = update.message
        if not msg:
            return None, "Nenurodyta priežastis"
        if msg.reply_to_message:
            target_id = msg.reply_to_message.from_user.id
            parts = msg.text.split(maxsplit=1)
            reason = parts[1].strip() if len(parts) > 1 else "Nenurodyta priežastis"
            return target_id, reason
        parts = msg.text.split()
        args = parts[1:] if len(parts) > 1 else []
        if not args:
            return None, "Nenurodyta priežastis"
        if args[0].isdigit():
            target_id = int(args[0])
            reason = " ".join(args[1:]).strip() or "Nenurodyta priežastis"
            return target_id, reason
        return None, " ".join(args).strip() or "Nenurodyta priežastis"

    def _message_link(self, update: Update) -> Optional[str]:
        chat = update.effective_chat
        msg = update.effective_message
        if not chat or not msg:
            return None
        if chat.username:
            mid = msg.reply_to_message.message_id if msg.reply_to_message else msg.message_id
            return f"https://t.me/{chat.username}/{mid}"
        if str(chat.id).startswith("-100"):
            internal = str(chat.id)[4:]
            target_mid = msg.reply_to_message.message_id if msg.reply_to_message else msg.message_id
            return f"https://t.me/c/{internal}/{target_mid}"
        return None

    async def _dm_owner(self, context: ContextTypes.DEFAULT_TYPE, *, reporter_id: int, reporter_name: str,
                        chat_title: str, chat_id: int, target_id: Optional[int], target_name: Optional[str],
                        reason: str, link: Optional[str], reported_text: Optional[str]):
        try:
            lines = []
            lines.append("🚩 <b>NAUJAS REPORT</b>")
            lines.append(f"<b>Grupė:</b> {html.escape(chat_title)} (<code>{chat_id}</code>)")
            lines.append(f"<b>Reporteris:</b> <code>{html.escape(reporter_name)}</code> (<code>{reporter_id}</code>)")
            if target_id:
                lines.append(f"<b>Taikinys:</b> <code>{html.escape(target_name or 'User')}</code> (<code>{target_id}</code>)")
            else:
                lines.append("<b>Taikinys:</b> <i>nenustatytas</i>")
            lines.append(f"<b>Priežastis:</b> {html.escape(reason)}")
            if link:
                lines.append(f"<b>Žinutės nuoroda:</b> {html.escape(link)}")

            await context.bot.send_message(chat_id=self.owner_id, text="\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)

            if reported_text:
                safe = reported_text if len(reported_text) < 4000 else reported_text[:4000] + "…"
                await context.bot.send_message(chat_id=self.owner_id, text=f"<b>Raportuota žinutė:</b>\n\n{html.escape(safe)}", parse_mode="HTML")

        except Exception as e:
            logger.warning(f"DM owner failed: {e}")
            try:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Report priimtas, bet nepavyko pranešti šeimininkui per PM.")
            except Exception:
                pass

    @group_only
    @group_allowed
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        user = update.effective_user
        msg = update.effective_message
        if not chat or not user or not msg:
            return

        target_id, reason = self._extract_target(update)

        target_name = None
        reported_text = None
        if msg.reply_to_message:
            target_name = msg.reply_to_message.from_user.full_name
            reported_text = msg.reply_to_message.text or msg.reply_to_message.caption or ""
        link = self._message_link(update)

        await context.bot.send_message(chat_id=chat.id, text="✅ Report priimtas. Adminai informuoti.")

        await self._dm_owner(
            context,
            reporter_id=user.id,
            reporter_name=user.full_name,
            chat_title=chat.title or str(chat.id),
            chat_id=chat.id,
            target_id=target_id,
            target_name=target_name,
            reason=reason,
            link=link,
            reported_text=reported_text,
        )
