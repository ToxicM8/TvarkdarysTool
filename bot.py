#!/usr/bin/env python3
"""Tvarkdarys - Telegram Moderation Bot"""

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatMemberHandler
from telegram import Update
from telegram.ext import ContextTypes

from handlers.commands import CommandHandlers
from handlers.moderation import ModerationHandlers
from handlers.xp_system import XPSystem
from handlers.invite_tracker import InviteTracker
from handlers.roles import RoleHandlers
from handlers.report import ReportHandlers
from handlers.antiflood import AntiFlood
from utils.storage import BotStorage
from config import BotConfig

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler('tvarkdarys.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class TvarkdaryBot:
    def __init__(self):
        self.config = BotConfig()
        self.storage = BotStorage()

        self.command_handlers = CommandHandlers(self.storage)
        self.moderation_handlers = ModerationHandlers(self.storage)
        self.xp_system = XPSystem(self.storage)
        self.invite_tracker = InviteTracker(self.storage)
        self.role_handlers = RoleHandlers(self.storage)
        self.report_handlers = ReportHandlers(self.storage)
        self.antiflood = AntiFlood(owner_id=self.config.owner_id)

        self.application = Application.builder().token(self.config.bot_token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        app = self.application

        # Commands
        app.add_handler(CommandHandler("start", self.command_handlers.start_command, block=True))
        app.add_handler(CommandHandler("pagalba", self.command_handlers.pagalba_command, block=True))
        app.add_handler(CommandHandler("taisykles", self.command_handlers.rules_command, block=True))
        app.add_handler(CommandHandler("xpinfo", self.command_handlers.xpinfo_command, block=True))
        app.add_handler(CommandHandler("xp", self.xp_system.check_xp_command, block=True))
        app.add_handler(CommandHandler("lyderiai", self.xp_system.leaderboard_command, block=True))

        # Roles
        app.add_handler(CommandHandler("mergina", self.role_handlers.mergina_command, block=True))
        app.add_handler(CommandHandler("vaikinas", self.role_handlers.vaikinas_command, block=True))
        app.add_handler(CommandHandler("kas", self.role_handlers.kas_command, block=True))

        # Report
        app.add_handler(CommandHandler("report", self.report_handlers.report_command, block=True))

        # Moderation
        app.add_handler(CommandHandler("ban", self.moderation_handlers.ban_command, block=True))
        app.add_handler(CommandHandler("kick", self.moderation_handlers.kick_command, block=True))
        app.add_handler(CommandHandler("unban", self.moderation_handlers.unban_command, block=True))
        app.add_handler(CommandHandler("mute", self.moderation_handlers.mute_command, block=True))
        app.add_handler(CommandHandler("unmute", self.moderation_handlers.unmute_command, block=True))
        app.add_handler(CommandHandler("warn", self.moderation_handlers.warn_command, block=True))
        app.add_handler(CommandHandler("ispejimai", self.moderation_handlers.check_warnings_command, block=True))

        # Owner-only
        app.add_handler(CommandHandler("setwelcome", self.command_handlers.set_welcome_command, block=True))

        # Message handlers — eilė svarbu!
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"(?:^|\s)(?:https?://)?t\.me/"), self._autoban_links))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._antiflood_entry))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._xp_entry))

        # Chat member updates
        app.add_handler(ChatMemberHandler(self._invite_entry, ChatMemberHandler.CHAT_MEMBER))
        app.add_handler(ChatMemberHandler(self._handle_welcome, ChatMemberHandler.CHAT_MEMBER))

        # Unknown
        app.add_handler(MessageHandler(filters.COMMAND, self._unknown_command))

        logger.info("Handlers registered (with whitelist).")
        app.add_error_handler(self._error_handler)

    # ---- whitelist wrappers for message handlers ----
    async def _antiflood_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if not chat or chat.id not in self.config.allowed_chats:
            return
        await self.antiflood.handle_text(update, context)

    async def _xp_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if not chat or chat.id not in self.config.allowed_chats:
            return
        await self.xp_system.handle_message(update, context)

    async def _invite_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if not chat or chat.id not in self.config.allowed_chats:
            return
        await self.invite_tracker.handle_member_join(update, context)

    # --- t.me autoban ---
    async def _autoban_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if not chat or chat.id not in self.config.allowed_chats:
            return

        msg = update.effective_message
        user = update.effective_user
        if not msg or not msg.text or not user or user.is_bot:
            return
        if user.id == self.config.owner_id:
            return
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            if member.status in ("administrator", "creator"):
                return
        except Exception:
            pass
        try:
            await msg.delete()
        except Exception:
            pass
        try:
            await context.bot.ban_chat_member(chat.id, user.id)
            self.storage.ban_user(chat.id, user.id)
            await context.bot.send_message(
                chat_id=chat.id,
                text=f"🚫 {user.mention_html()} išmestas už t.me nuorodą. Tokie linkai draudžiami.",
                parse_mode="HTML"
            )
        except Exception as e:
            await context.bot.send_message(chat_id=chat.id, text=f"⚠️ Nepavyko užbaninti: {e}")

    # --- welcome / unknown / error ---
    async def _handle_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if not chat or chat.id not in self.config.allowed_chats:
            return
        if update.chat_member.new_chat_member and update.chat_member.new_chat_member.status == "member":
            chat_id = chat.id
            user = update.chat_member.new_chat_member.user
            welcome_msg = self.storage.get_welcome_message(chat_id) or "Sveiki atvykę į pragarą, kekšės!!! 😈"
            welcome_msg = welcome_msg.replace("{user}", user.mention_html())
            try:
                await context.bot.send_message(chat_id=chat_id, text=welcome_msg, parse_mode='HTML')
            except Exception:
                pass

    async def _unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if chat and chat.id not in self.config.allowed_chats and chat.type != 'private':
            await context.bot.send_message(chat_id=chat.id, text="❌ Čia aš nedirbu.")
            return
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ NU KĄ TU BLET DARAI? 🤷\n❗ Naudok <code>/pagalba</code> 👇",
            parse_mode='HTML'
        )

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        try:
            if isinstance(update, Update) and update.effective_message:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ Įvyko klaida. Bandyk dar kart.",
                )
        except Exception:
            pass

def build_application() -> Application:
    """
    Sukuria ir grąžina PTB Application su visais tavo handleriais.
    NEPaleidžia pollingo — tam turėsim Flask webhook startą.
    """
    bot = TvarkdaryBot()
    return bot.application