"""
Basic command handlers for Tvarkdarys bot
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils.permissions import admin_required, group_only, rate_limit
from utils.storage import BotStorage

logger = logging.getLogger(__name__)

class CommandHandlers:
    """Handler class for basic bot commands"""
    
    def __init__(self, storage: BotStorage):
        self.storage = storage
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        welcome_text = f"""
🤖 **Tvarkdarys Bot** - Telegram Moderation Assistant

Hello {user.first_name}! I'm here to help manage your Telegram groups.

**Available Commands:**
• `/help` - Show all commands
• `/rules` - Display group rules
• `/xp` - Check your experience points
• `/leaderboard` - Show XP leaderboard
• `/invites` - Check your invite statistics

**Admin Commands:**
• `/ban` - Ban a user
• `/kick` - Kick a user  
• `/mute` - Mute a user
• `/warn` - Warn a user
• `/setrules` - Set group rules
• `/setwelcome` - Set welcome message

Add me to your group and make me an admin to get started! 🚀
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    @rate_limit(lambda self: self.storage, 5)
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🔧 **Tvarkdarys Bot Commands**

**General Commands:**
• `/rules` - View group rules
• `/xp` - Check your XP points
• `/leaderboard` - Top 10 XP users
• `/invites` - Your invite statistics

**Moderation (Admin Only):**
• `/ban <user>` - Ban user from group
• `/kick <user>` - Kick user from group
• `/unban <user>` - Unban user
• `/mute <user> [minutes]` - Mute user (default: 60 min)
• `/unmute <user>` - Unmute user
• `/warn <user> [reason]` - Warn user
• `/warnings <user>` - Check user warnings

**Settings (Admin Only):**
• `/setrules <rules>` - Set group rules
• `/setwelcome <message>` - Set welcome message
• `/settings` - View group settings

**XP System:**
Earn 1 XP per message (1 minute cooldown)
Track engagement and compete on leaderboards!

**Invite Tracking:**
Monitor who invites new members and track statistics.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    @group_only
    @rate_limit(lambda self: self.storage, 3)
    async def rules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rules command"""
        chat_id = update.effective_chat.id
        rules = self.storage.get_rules(chat_id)
        
        if not rules:
            rules_text = """
📋 **Group Rules**

No specific rules have been set yet.
Contact an administrator to set up group rules.
            """
        else:
            rules_text = "📋 **Group Rules**\n\n"
            for i, rule in enumerate(rules, 1):
                rules_text += f"{i}. {rule}\n"
        
        await update.message.reply_text(rules_text, parse_mode='Markdown')
    
    @group_only
    @admin_required
    async def set_rules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setrules command - Admin only"""
        chat_id = update.effective_chat.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide rules to set.\n\n"
                "**Usage:** `/setrules Rule 1 | Rule 2 | Rule 3`\n"
                "Separate multiple rules with ' | '",
                parse_mode='Markdown'
            )
            return
        
        # Join all arguments and split by |
        rules_text = " ".join(context.args)
        rules = [rule.strip() for rule in rules_text.split('|') if rule.strip()]
        
        if not rules:
            await update.message.reply_text("❌ No valid rules provided.")
            return
        
        self.storage.set_rules(chat_id, rules)
        
        rules_display = "✅ **Rules updated successfully!**\n\n"
        for i, rule in enumerate(rules, 1):
            rules_display += f"{i}. {rule}\n"
        
        await update.message.reply_text(rules_display, parse_mode='Markdown')
        logger.info(f"Rules updated for chat {chat_id} by user {update.effective_user.id}")
    
    @group_only
    @admin_required
    async def set_welcome_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setwelcome command - Admin only"""
        chat_id = update.effective_chat.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a welcome message.\n\n"
                "**Usage:** `/setwelcome Welcome to our group, {user}!`\n"
                "Use `{user}` to mention the new member.",
                parse_mode='Markdown'
            )
            return
        
        welcome_message = " ".join(context.args)
        self.storage.set_welcome_message(chat_id, welcome_message)
        
        await update.message.reply_text(
            f"✅ **Welcome message updated!**\n\n"
            f"Preview: {welcome_message.replace('{user}', update.effective_user.mention_html())}",
            parse_mode='HTML'
        )
        logger.info(f"Welcome message updated for chat {chat_id} by user {update.effective_user.id}")
    
    @group_only
    @admin_required
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command - Admin only"""
        chat_id = update.effective_chat.id
        group_settings = self.storage.get_group_settings(chat_id)
        
        # Count statistics
        total_users = len(self.storage.users)
        banned_count = len(self.storage.banned_users.get(chat_id, []))
        muted_count = len(self.storage.muted_users.get(chat_id, {}))
        
        settings_text = f"""
⚙️ **Group Settings**

**Rules:** {len(group_settings.rules)} rules set
**Welcome Message:** {'✅ Set' if group_settings.welcome_message else '❌ Not set'}
**Invite Links:** {len(group_settings.invite_links)} tracked

**Statistics:**
• Total Users: {total_users}
• Banned Users: {banned_count}
• Muted Users: {muted_count}

**Commands Available:**
• `/setrules` - Update group rules
• `/setwelcome` - Set welcome message
• Moderation commands: `/ban`, `/kick`, `/mute`, `/warn`
        """
        
        await update.message.reply_text(settings_text, parse_mode='Markdown')
