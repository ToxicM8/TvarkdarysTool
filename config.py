"""
Configuration settings for Tvarkdarys bot
"""

import os

class BotConfig:
    """Bot configuration class"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        # XP System settings
        self.xp_per_message = 1
        self.xp_cooldown = 60  # seconds between XP gains for same user
        self.max_xp_per_hour = 50
        
        # Rate limiting
        self.command_cooldown = 3  # seconds between commands
        self.max_warnings = 3  # warnings before auto-ban
        
        # Default messages
        self.default_rules = [
            "1. Be respectful to all members",
            "2. No spam or excessive self-promotion", 
            "3. Keep discussions relevant to the topic",
            "4. No hate speech or discrimination",
            "5. Follow Telegram's Terms of Service"
        ]
        
        self.default_welcome = "Welcome to our community, {user}! 🎉\n\nPlease read our rules with /rules"
