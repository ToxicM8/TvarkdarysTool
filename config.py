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
        
        # Default messages in Lithuanian
        self.default_rules = [
            "1. Gerbkite visus narių",
            "2. Draudžiamas šlamštas ir per didelis savireklama", 
            "3. Laikykitės temos diskusijose",
            "4. Draudžiamos neapykantos kalbos ir diskriminacija",
            "5. Laikykitės Telegram naudojimo taisyklių"
        ]
        
        self.default_welcome = "Sveiki atvykę į mūsų bendruomenę, {user}! 🎉\n\nPrašome perskaityti taisykles naudojant /taisykles"
