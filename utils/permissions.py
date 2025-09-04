"""
Permission checking utilities for Tvarkdarys bot
"""

import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config import BotConfig

logger = logging.getLogger(__name__)


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None) -> bool:
    """Check if user is admin in the chat"""
    if not update.effective_chat:
        return False
    if user_id is None:
        user_id = update.effective_user.id
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return chat_member.status in ['creator', 'administrator']
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


async def is_creator(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None) -> bool:
    """Check if user is creator of the chat"""
    if not update.effective_chat:
        return False
    if user_id is None:
        user_id = update.effective_user.id
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return chat_member.status == 'creator'
    except Exception as e:
        logger.error(f"Error checking creator status: {e}")
        return False


def admin_required(func):
    """Decorator to require admin permissions"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await is_admin(update, context):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Jūs turite būti administratorius, kad galėtumėte naudoti šią komandą."
            )
            return
        return await func(self, update, context)
    return wrapper


def group_only(func):
    """Decorator to restrict command to groups only"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == 'private':
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Ši komanda gali būti naudojama tik grupėse."
            )
            return
        return await func(self, update, context)
    return wrapper


def group_allowed(func):
    """Decorator: leisti dirbti tik whitelist'intuose chatuose (config.allowed_chats)."""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cfg = BotConfig()
        chat = update.effective_chat
        if not chat or chat.id not in cfg.allowed_chats:
            await context.bot.send_message(chat_id=chat.id, text="❌ Čia aš nedirbu.")
            return
        return await func(self, update, context)
    return wrapper


def rate_limit(cooldown_seconds: int = 3):
    """Decorator for rate limiting commands (naudoja self.storage.check_command_cooldown)."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            storage = getattr(self, "storage", None)
            if storage:
                user_id = update.effective_user.id
                if not storage.check_command_cooldown(user_id, cooldown_seconds):
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"⏳ Palauk {cooldown_seconds} s prieš naudodamas šitą komandą dar kartą."
                    )
                    return
            return await func(self, update, context)
        return wrapper
    return decorator


async def can_restrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int) -> bool:
    """Check if bot and admin can restrict target user"""
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    try:
        # Admin permissions
        admin_member = await context.bot.get_chat_member(chat_id, admin_id)
        if not (admin_member.status == 'creator' or
                (admin_member.status == 'administrator' and getattr(admin_member, 'can_restrict_members', True))):
            return False

        # Target must NOT be admin/creator
        target_member = await context.bot.get_chat_member(chat_id, target_user_id)
        if target_member.status in ['creator', 'administrator']:
            return False

        # Bot must have restrict
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not (bot_member.status == 'administrator'):
            return False

        return True
    except Exception as e:
        logger.error(f"Error checking restriction permissions: {e}")
        return False
