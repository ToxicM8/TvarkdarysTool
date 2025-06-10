#!/usr/bin/env python3
"""
Tvarkdarys - Telegram Moderation Bot
Main bot file that initializes and runs the bot with all handlers
"""

import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatMemberHandler
from telegram import Update
from telegram.ext import ContextTypes

from handlers.commands import CommandHandlers
from handlers.moderation import ModerationHandlers
from handlers.xp_system import XPSystem
from handlers.invite_tracker import InviteTracker
from utils.storage import BotStorage
from config import BotConfig

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('tvarkdarys.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TvarkdaryBot:
    def __init__(self):
        """Initialize the Tvarkdarys bot with all components"""
        self.config = BotConfig()
        self.storage = BotStorage()
        
        # Initialize handlers
        self.command_handlers = CommandHandlers(self.storage)
        self.moderation_handlers = ModerationHandlers(self.storage)
        self.xp_system = XPSystem(self.storage)
        self.invite_tracker = InviteTracker(self.storage)
        
        # Create application
        self.application = Application.builder().token(self.config.bot_token).build()
        
        # Setup handlers
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup all command and message handlers"""
        app = self.application
        
        # Command handlers - English and Lithuanian
        app.add_handler(CommandHandler("start", self.command_handlers.start_command))
        app.add_handler(CommandHandler("pradeti", self.command_handlers.start_command))
        app.add_handler(CommandHandler("help", self.command_handlers.help_command))
        app.add_handler(CommandHandler("pagalba", self.command_handlers.help_command))
        app.add_handler(CommandHandler("rules", self.command_handlers.rules_command))
        app.add_handler(CommandHandler("taisykles", self.command_handlers.rules_command))
        app.add_handler(CommandHandler("setrules", self.command_handlers.set_rules_command))
        app.add_handler(CommandHandler("nustatyti_taisykles", self.command_handlers.set_rules_command))
        app.add_handler(CommandHandler("xp", self.xp_system.check_xp_command))
        app.add_handler(CommandHandler("leaderboard", self.xp_system.leaderboard_command))
        app.add_handler(CommandHandler("lyderiai", self.xp_system.leaderboard_command))
        app.add_handler(CommandHandler("invites", self.invite_tracker.check_invites_command))
        app.add_handler(CommandHandler("kvietimai", self.invite_tracker.check_invites_command))
        app.add_handler(CommandHandler("invitestats", self.invite_tracker.invite_stats_command))
        app.add_handler(CommandHandler("kvietu_statistika", self.invite_tracker.invite_stats_command))
        
        # Moderation commands - English and Lithuanian
        app.add_handler(CommandHandler("ban", self.moderation_handlers.ban_command))
        app.add_handler(CommandHandler("uzblokuoti", self.moderation_handlers.ban_command))
        app.add_handler(CommandHandler("kick", self.moderation_handlers.kick_command))
        app.add_handler(CommandHandler("ismesti", self.moderation_handlers.kick_command))
        app.add_handler(CommandHandler("unban", self.moderation_handlers.unban_command))
        app.add_handler(CommandHandler("atblokuoti", self.moderation_handlers.unban_command))
        app.add_handler(CommandHandler("mute", self.moderation_handlers.mute_command))
        app.add_handler(CommandHandler("nutildyti", self.moderation_handlers.mute_command))
        app.add_handler(CommandHandler("unmute", self.moderation_handlers.unmute_command))
        app.add_handler(CommandHandler("atkurti_balsa", self.moderation_handlers.unmute_command))
        app.add_handler(CommandHandler("warn", self.moderation_handlers.warn_command))
        app.add_handler(CommandHandler("ispeti", self.moderation_handlers.warn_command))
        app.add_handler(CommandHandler("warnings", self.moderation_handlers.check_warnings_command))
        app.add_handler(CommandHandler("ispejimai", self.moderation_handlers.check_warnings_command))
        
        # Admin commands - English and Lithuanian
        app.add_handler(CommandHandler("setwelcome", self.command_handlers.set_welcome_command))
        app.add_handler(CommandHandler("nustatyti_pasisveikinima", self.command_handlers.set_welcome_command))
        app.add_handler(CommandHandler("settings", self.command_handlers.settings_command))
        app.add_handler(CommandHandler("nustatymai", self.command_handlers.settings_command))
        
        # Message handlers
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.xp_system.handle_message))
        app.add_handler(ChatMemberHandler(self.invite_tracker.handle_member_join, ChatMemberHandler.CHAT_MEMBER))
        app.add_handler(ChatMemberHandler(self._handle_welcome, ChatMemberHandler.CHAT_MEMBER))
        
        # Error handler
        app.add_error_handler(self._error_handler)
        
    async def _handle_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle welcome messages for new members"""
        if update.chat_member.new_chat_member and update.chat_member.new_chat_member.status == "member":
            chat_id = update.effective_chat.id
            user = update.chat_member.new_chat_member.user
            
            # Get custom welcome message or use default
            welcome_msg = self.storage.get_welcome_message(chat_id)
            if not welcome_msg:
                welcome_msg = f"Sveiki atvykę į pokalbį, {user.mention_html()}! 🎉\n\nPrašome perskaityti taisykles naudojant /taisykles komandą."
            else:
                welcome_msg = welcome_msg.replace("{user}", user.mention_html())
            
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=welcome_msg,
                    parse_mode='HTML'
                )
                logger.info(f"Welcome message sent to {user.username} in chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send welcome message: {e}")
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log errors caused by updates"""
        logger.error(f'Update {update} caused error {context.error}')
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred while processing your request. Please try again later."
                )
            except Exception:
                pass  # Ignore errors when sending error messages
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Tvarkdarys bot...")
        print("🤖 Tvarkdarys bot is starting...")
        
        try:
            # Start the bot
            self.application.run_polling(
                allowed_updates=["message", "chat_member", "callback_query"]
            )
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            print("👋 Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            print(f"❌ Bot crashed: {e}")

def main():
    """Main function to run the bot"""
    bot = TvarkdaryBot()
    bot.run()

if __name__ == '__main__':
    main()
