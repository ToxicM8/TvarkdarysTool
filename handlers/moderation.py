"""
Moderation command handlers for Tvarkdarys bot
"""

import logging
import re
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden
from utils.permissions import admin_required, group_only, can_restrict_user
from utils.storage import BotStorage

logger = logging.getLogger(__name__)

class ModerationHandlers:
    """Handler class for moderation commands"""
    
    def __init__(self, storage: BotStorage):
        self.storage = storage
    
    def _extract_user_from_message(self, update: Update) -> tuple:
        """Extract user ID and reason from command arguments or reply"""
        target_user = None
        reason = "No reason provided"
        
        # Check if replying to a message
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
            if update.message.text and len(update.message.text.split()) > 1:
                reason = " ".join(update.message.text.split()[1:])
        else:
            # Parse from command arguments
            args = update.message.text.split()[1:] if update.message.text else []
            if args:
                # Try to extract user ID or username
                user_identifier = args[0]
                if len(args) > 1:
                    reason = " ".join(args[1:])
                
                # Check if it's a user ID
                if user_identifier.isdigit():
                    user_id = int(user_identifier)
                    # Create a minimal user object
                    class MinimalUser:
                        def __init__(self, user_id):
                            self.id = user_id
                            self.username = None
                            self.first_name = f"User{user_id}"
                            
                    target_user = MinimalUser(user_id)
                elif user_identifier.startswith('@'):
                    # Username mention - we'll handle this as best we can
                    username = user_identifier[1:]
                    # In a real implementation, you'd need to resolve username to user_id
                    # For now, we'll return None and show an error
                    return None, "Cannot resolve username. Please reply to user's message or use user ID."
        
        return target_user, reason
    
    @group_only
    @admin_required
    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ban command"""
        target_user, reason = self._extract_user_from_message(update)
        
        if not target_user:
            await update.message.reply_text(
                "❌ Please reply to a user's message or provide a user ID.\n"
                "**Usage:** `/ban [user_id] [reason]` or reply to message with `/ban [reason]`",
                parse_mode='Markdown'
            )
            return
        
        if target_user.id == update.effective_user.id:
            await update.message.reply_text("❌ You cannot ban yourself!")
            return
        
        chat_id = update.effective_chat.id
        
        # Check permissions
        if not await can_restrict_user(update, context, target_user.id):
            await update.message.reply_text(
                "❌ Cannot ban this user. They might be an admin or I don't have sufficient permissions."
            )
            return
        
        try:
            # Ban user from chat
            await context.bot.ban_chat_member(chat_id, target_user.id)
            
            # Store in our database
            self.storage.ban_user(chat_id, target_user.id)
            
            ban_text = f"🔨 **User Banned**\n\n"
            ban_text += f"**User:** {target_user.first_name}"
            if target_user.username:
                ban_text += f" (@{target_user.username})"
            ban_text += f"\n**ID:** `{target_user.id}`"
            ban_text += f"\n**Reason:** {reason}"
            ban_text += f"\n**Banned by:** {update.effective_user.mention_html()}"
            
            await update.message.reply_text(ban_text, parse_mode='HTML')
            
            logger.info(f"User {target_user.id} banned from chat {chat_id} by {update.effective_user.id}. Reason: {reason}")
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to ban user: {e}")
            logger.error(f"Failed to ban user {target_user.id}: {e}")
        except Forbidden:
            await update.message.reply_text("❌ I don't have permission to ban users. Please make me an admin with ban permissions.")
    
    @group_only
    @admin_required
    async def kick_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /kick command"""
        target_user, reason = self._extract_user_from_message(update)
        
        if not target_user:
            await update.message.reply_text(
                "❌ Please reply to a user's message or provide a user ID.\n"
                "**Usage:** `/kick [user_id] [reason]` or reply to message with `/kick [reason]`",
                parse_mode='Markdown'
            )
            return
        
        if target_user.id == update.effective_user.id:
            await update.message.reply_text("❌ You cannot kick yourself!")
            return
        
        chat_id = update.effective_chat.id
        
        # Check permissions
        if not await can_restrict_user(update, context, target_user.id):
            await update.message.reply_text(
                "❌ Cannot kick this user. They might be an admin or I don't have sufficient permissions."
            )
            return
        
        try:
            # Kick user (ban then unban)
            await context.bot.ban_chat_member(chat_id, target_user.id)
            await context.bot.unban_chat_member(chat_id, target_user.id)
            
            kick_text = f"👢 **User Kicked**\n\n"
            kick_text += f"**User:** {target_user.first_name}"
            if target_user.username:
                kick_text += f" (@{target_user.username})"
            kick_text += f"\n**ID:** `{target_user.id}`"
            kick_text += f"\n**Reason:** {reason}"
            kick_text += f"\n**Kicked by:** {update.effective_user.mention_html()}"
            
            await update.message.reply_text(kick_text, parse_mode='HTML')
            
            logger.info(f"User {target_user.id} kicked from chat {chat_id} by {update.effective_user.id}. Reason: {reason}")
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to kick user: {e}")
            logger.error(f"Failed to kick user {target_user.id}: {e}")
        except Forbidden:
            await update.message.reply_text("❌ I don't have permission to kick users. Please make me an admin with ban permissions.")
    
    @group_only
    @admin_required
    async def unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unban command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a user ID to unban.\n"
                "**Usage:** `/unban <user_id>`",
                parse_mode='Markdown'
            )
            return
        
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid user ID.")
            return
        
        chat_id = update.effective_chat.id
        
        try:
            # Unban user
            await context.bot.unban_chat_member(chat_id, user_id)
            
            # Remove from our banned list
            self.storage.unban_user(chat_id, user_id)
            
            await update.message.reply_text(
                f"✅ **User Unbanned**\n\n"
                f"**User ID:** `{user_id}`\n"
                f"**Unbanned by:** {update.effective_user.mention_html()}",
                parse_mode='HTML'
            )
            
            logger.info(f"User {user_id} unbanned from chat {chat_id} by {update.effective_user.id}")
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to unban user: {e}")
            logger.error(f"Failed to unban user {user_id}: {e}")
        except Forbidden:
            await update.message.reply_text("❌ I don't have permission to unban users.")
    
    @group_only
    @admin_required
    async def mute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mute command"""
        target_user, reason = self._extract_user_from_message(update)
        
        if not target_user:
            await update.message.reply_text(
                "❌ Please reply to a user's message or provide a user ID.\n"
                "**Usage:** `/mute [user_id] [minutes]` or reply to message with `/mute [minutes]`",
                parse_mode='Markdown'
            )
            return
        
        # Parse duration
        duration = 60  # default 60 minutes
        if context.args:
            # Find duration in args
            for arg in context.args:
                if arg.isdigit():
                    duration = int(arg)
                    break
        
        if target_user.id == update.effective_user.id:
            await update.message.reply_text("❌ You cannot mute yourself!")
            return
        
        chat_id = update.effective_chat.id
        
        # Check permissions
        if not await can_restrict_user(update, context, target_user.id):
            await update.message.reply_text(
                "❌ Cannot mute this user. They might be an admin or I don't have sufficient permissions."
            )
            return
        
        try:
            # Mute user (restrict messages)
            await context.bot.restrict_chat_member(
                chat_id, 
                target_user.id,
                permissions=context.bot.get_chat_member(chat_id, target_user.id).permissions._replace(can_send_messages=False)
            )
            
            # Store mute in our system
            self.storage.mute_user(chat_id, target_user.id, duration)
            
            mute_text = f"🔇 **User Muted**\n\n"
            mute_text += f"**User:** {target_user.first_name}"
            if target_user.username:
                mute_text += f" (@{target_user.username})"
            mute_text += f"\n**ID:** `{target_user.id}`"
            mute_text += f"\n**Duration:** {duration} minutes"
            mute_text += f"\n**Muted by:** {update.effective_user.mention_html()}"
            
            await update.message.reply_text(mute_text, parse_mode='HTML')
            
            logger.info(f"User {target_user.id} muted in chat {chat_id} for {duration} minutes by {update.effective_user.id}")
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to mute user: {e}")
            logger.error(f"Failed to mute user {target_user.id}: {e}")
        except Forbidden:
            await update.message.reply_text("❌ I don't have permission to restrict users.")
    
    @group_only
    @admin_required
    async def unmute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unmute command"""
        target_user, _ = self._extract_user_from_message(update)
        
        if not target_user:
            await update.message.reply_text(
                "❌ Please reply to a user's message or provide a user ID.\n"
                "**Usage:** `/unmute [user_id]` or reply to message with `/unmute`",
                parse_mode='Markdown'
            )
            return
        
        chat_id = update.effective_chat.id
        
        try:
            # Get current chat permissions and restore them
            chat = await context.bot.get_chat(chat_id)
            await context.bot.restrict_chat_member(
                chat_id,
                target_user.id,
                permissions=chat.permissions
            )
            
            # Remove mute from our system
            self.storage.unmute_user(chat_id, target_user.id)
            
            await update.message.reply_text(
                f"🔊 **User Unmuted**\n\n"
                f"**User:** {target_user.first_name}\n"
                f"**Unmuted by:** {update.effective_user.mention_html()}",
                parse_mode='HTML'
            )
            
            logger.info(f"User {target_user.id} unmuted in chat {chat_id} by {update.effective_user.id}")
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to unmute user: {e}")
            logger.error(f"Failed to unmute user {target_user.id}: {e}")
        except Forbidden:
            await update.message.reply_text("❌ I don't have permission to restrict users.")
    
    @group_only
    @admin_required
    async def warn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /warn command"""
        target_user, reason = self._extract_user_from_message(update)
        
        if not target_user:
            await update.message.reply_text(
                "❌ Please reply to a user's message or provide a user ID.\n"
                "**Usage:** `/warn [user_id] [reason]` or reply to message with `/warn [reason]`",
                parse_mode='Markdown'
            )
            return
        
        if target_user.id == update.effective_user.id:
            await update.message.reply_text("❌ You cannot warn yourself!")
            return
        
        chat_id = update.effective_chat.id
        
        # Add warning
        total_warnings = self.storage.add_warning(chat_id, target_user.id)
        
        warn_text = f"⚠️ **User Warned**\n\n"
        warn_text += f"**User:** {target_user.first_name}"
        if target_user.username:
            warn_text += f" (@{target_user.username})"
        warn_text += f"\n**ID:** `{target_user.id}`"
        warn_text += f"\n**Reason:** {reason}"
        warn_text += f"\n**Warnings:** {total_warnings}/3"
        warn_text += f"\n**Warned by:** {update.effective_user.mention_html()}"
        
        if total_warnings >= 3:
            warn_text += "\n\n🔨 **Auto-ban triggered due to 3 warnings!**"
            try:
                await context.bot.ban_chat_member(chat_id, target_user.id)
                self.storage.ban_user(chat_id, target_user.id)
                logger.info(f"User {target_user.id} auto-banned for 3 warnings in chat {chat_id}")
            except Exception as e:
                warn_text += f"\n❌ Failed to auto-ban: {e}"
                logger.error(f"Failed to auto-ban user {target_user.id}: {e}")
        
        await update.message.reply_text(warn_text, parse_mode='HTML')
        
        logger.info(f"User {target_user.id} warned in chat {chat_id} by {update.effective_user.id}. Total warnings: {total_warnings}")
    
    async def check_warnings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /warnings command"""
        target_user, _ = self._extract_user_from_message(update)
        
        if not target_user:
            # Check own warnings
            target_user = update.effective_user
        
        warnings = self.storage.get_warnings(target_user.id)
        
        warnings_text = f"⚠️ **Warning Status**\n\n"
        warnings_text += f"**User:** {target_user.first_name}"
        if target_user.username:
            warnings_text += f" (@{target_user.username})"
        warnings_text += f"\n**Warnings:** {warnings}/3"
        
        if warnings >= 3:
            warnings_text += "\n🔴 **Maximum warnings reached!**"
        elif warnings >= 2:
            warnings_text += "\n🟡 **One warning away from ban!**"
        elif warnings >= 1:
            warnings_text += "\n🟠 **Be careful with your behavior!**"
        else:
            warnings_text += "\n🟢 **No warnings - good behavior!**"
        
        await update.message.reply_text(warnings_text, parse_mode='HTML')
