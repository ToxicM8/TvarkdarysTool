"""
XP (Experience Points) system handlers for Tvarkdarys bot
"""

import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from utils.storage import BotStorage
from utils.permissions import rate_limit, group_only, group_allowed
from config import BotConfig

logger = logging.getLogger(__name__)

class XPSystem:
    def __init__(self, storage: BotStorage):
        self.storage = storage
        self.owner_id = BotConfig().owner_id
        self.allowed_chats = BotConfig().allowed_chats

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages for XP gain (tik allowed chatuose)"""
        chat = update.effective_chat
        if not chat or chat.id not in self.allowed_chats:
            return
        if not update.effective_user or update.effective_user.is_bot:
            return
        if chat.type == 'private':
            return

        user = update.effective_user

        # Elite – neskaičiuojam XP
        if user.id == self.owner_id:
            return

        user_data = self.storage.get_user(
            user_id=user.id,
            username=user.username or "",
            first_name=user.first_name or ""
        )
        # Cooldown inside storage
        xp_gained = self.storage.add_xp(user.id, 1)
        if xp_gained:
            logger.debug(f"User {user.id} gained 1 XP. Total now: {user_data.xp}")

    @rate_limit(5)
    @group_only
    @group_allowed
    async def check_xp_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        target_user = user

        # check other target
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        elif context.args and context.args[0].isdigit():
            target_user_id = int(context.args[0])
            target_user_data = self.storage.get_user(target_user_id)
            if target_user_data:
                class MinimalUser:
                    def __init__(self, user_data):
                        self.id = user_data.user_id
                        self.first_name = user_data.first_name
                        self.username = user_data.username
                target_user = MinimalUser(target_user_data)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Nu bbz, nėra tokio userio.")
                return

        user_data = self.storage.get_user(
            user_id=target_user.id,
            username=getattr(target_user, 'username', '') or "",
            first_name=getattr(target_user, 'first_name', '') or ""
        )

        all_users = sorted(self.storage.users.values(), key=lambda x: x.xp, reverse=True)
        rank = next((i + 1 for i, u in enumerate(all_users) if u.user_id == target_user.id), len(all_users))

        current_level = user_data.xp // 100
        xp_for_next_level = (current_level + 1) * 100
        xp_needed = xp_for_next_level - user_data.xp

        last_xp_time = ""
        if user_data.last_xp_time > 0:
            diff = time.time() - user_data.last_xp_time
            if diff < 60: last_xp_time = f"{int(diff)} s atgal"
            elif diff < 3600: last_xp_time = f"{int(diff/60)} min atgal"
            else: last_xp_time = f"{int(diff/3600)} h atgal"
        else:
            last_xp_time = "Niekada"

        progress = min(100, int((user_data.xp % 100) * 100 / 100))
        progress_bar = "▓" * (progress // 10) + "░" * (10 - progress // 10)

        elite_suffix = ""
        if target_user.id == self.owner_id:
            elite_suffix = " 👑 Elite ♾️"

        xp_text = (
            f"🏆 <b>XP Būsena{elite_suffix}</b>\n\n"
            f"<b>Vartotojas:</b> {user_data.first_name}"
        )
        if getattr(target_user, 'username', None):
            xp_text += f" (@{target_user.username})"
        xp_text += (
            f"\n<b>Lygis:</b> {current_level}"
            f"\n<b>XP:</b> {user_data.xp:,}"
            f"\n<b>Reitingas:</b> #{rank} iš {len(self.storage.users)}"
            f"\n<b>Kitas Lygis:</b> reikia {xp_needed} XP"
            f"\n<b>Paskutinis XP:</b> {last_xp_time}"
            f"\n<b>Progresas:</b> {progress_bar} {progress}%"
        )

        await context.bot.send_message(chat_id=update.effective_chat.id, text=xp_text, parse_mode="HTML")

    @rate_limit(10)
    @group_only
    @group_allowed
    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        top_users = self.storage.get_leaderboard(update.effective_chat.id, 10)
        if not top_users:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📊 <b>Lyderių sąrašas</b>\n\nKol kas nėra ką rodyti!\nNorint pradėti kelti XP reikia chatint! 💬",
                parse_mode="HTML"
            )
            return

        leaderboard_text = "🏆 <b>XP Lyderiai – Top 10</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]

        # išmetam owner'į iš sąrašo
        filtered = [u for u in top_users if u.user_id != self.owner_id]

        for i, user_data in enumerate(filtered):
            rank = i + 1
            level = user_data.xp // 100
            rank_display = medals[rank - 1] if rank <= 3 else f"{rank}."
            username_display = user_data.first_name
            if user_data.username:
                username_display += f" (@{user_data.username})"
            leaderboard_text += f"{rank_display} <b>{username_display}</b>\n    Level {level} • {user_data.xp:,} XP\n\n"

        # user's own position
        user_data = self.storage.get_user(update.effective_user.id)
        all_users = sorted(self.storage.users.values(), key=lambda x: x.xp, reverse=True)
        user_rank = next((i + 1 for i, u in enumerate(all_users) if u.user_id == update.effective_user.id), None)
        if user_rank and user_rank > 10:
            user_level = user_data.xp // 100
            leaderboard_text += f"---\n<b>Tavo pozicija:</b> #{user_rank}\nLevelis {user_level} • {user_data.xp:,} XP"

        leaderboard_text += "\n\n💡 <i>Kelk XP bendraudamas! +1 XP per žinutę</i>"

        await context.bot.send_message(chat_id=update.effective_chat.id, text=leaderboard_text, parse_mode='HTML')
