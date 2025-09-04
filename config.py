"""
Configuration settings for Tvarkdarys bot
"""

import os

class BotConfig:
    """Bot configuration class"""

    def __init__(self):
        # Bot token iš environment
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

        # 👑 Owner/Elite ID
        self.owner_id = 1173493108

        # ✅ LEIDŽIAMI CHAT’AI (įrašyk savo grupės chat_id)
        # Pvz. supergrupės ID: -100xxxxxxxxxx
        self.allowed_chats = [
            -1002737420624  # <-- pakeisk į SAVO grupės chat_id
        ]

        # XP System settings
        self.xp_per_message = 1
        self.xp_cooldown = 60  # seconds tarp XP gavimų
        self.max_xp_per_hour = 50

        # Rate limiting
        self.command_cooldown = 3  # seconds tarp komandų
        self.max_warnings = 3      # warnings iki auto-ban

        # Default messages in Lithuanian
        self.default_rules = [
            "1. Gerbkite visus narius",
            "2. Draudžiamas šlamštas ir per didelis savireklama",
            "3. Laikykitės temos diskusijose",
            "4. Draudžiamos neapykantos kalbos ir diskriminacija",
            "5. Laikykitės Telegram naudojimo taisyklių"
        ]

        self.default_welcome = (
            "Sveiki atvykę į mūsų bendruomenę, {user}! 🎉\n\n"
            "Prašome perskaityti taisykles naudojant /taisykles"
        )
