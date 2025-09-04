# handlers/invite_tracker.py
"""
Invite tracking / member join handler for Tvarkdarys bot
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils.storage import BotStorage
from utils.permissions import rate_limit, group_only, group_allowed
from config import BotConfig

logger = logging.getLogger(__name__)


class InviteTracker:
    def __init__(self, storage: BotStorage):
        self.storage = storage
        cfg = BotConfig()
        self.allowed_chats = set(cfg.allowed_chats)

    async def handle_member_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Called by ChatMemberHandler when someone joins / status changes.
        Registruojam naują userį, atnaujinam vardą, etc.
        """
        chat = update.effective_chat
        cmu = update.chat_member
        if not chat or chat.id not in self.allowed_chats:
            return
        if not cmu or not cmu.new_chat_member:
            return

        try:
            if cmu.new_chat_member.status != "member":
                return

            new_user = cmu.new_chat_member.user
            # užregistruojam / atnaujinam user info storage'e
            self.storage.get_user(
                user_id=new_user.id,
                username=new_user.username or "",
                first_name=new_user.first_name or ""
            )

            logger.info(f"[JOIN] {new_user.id} ({new_user.first_name}) įėjo į chat {chat.id}")
        except Exception as e:
            logger.error(f"InviteTracker.handle_member_join error: {e}")

    # --- OPTIONAL: paprasta komanda pasitikrinti kvietimų statistiką (mock) ---
    # jei nenori — gali neregistruot bot.py
    @rate_limit(5)  # <- SVARBU: naudok funkcijos parametrą be self; storage viduje per lambda dekoratoriuje NENAUDOTAS
    @group_only
    @group_allowed
    async def check_invites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /kvietimai  (demo)
        Dabar netrakinam realių INVITE linkų – tik placeholderis su user->invites_count iš storage.
        Jei nori realaus tracking per unikalų linką – darysim vėliau.
        """
        user = update.effective_user
        if not user:
            return

        u = self.storage.get_user(user.id)
        count = getattr(u, "invites_count", 0)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔗 {u.first_name} turi {count} kvietimų."
        )
