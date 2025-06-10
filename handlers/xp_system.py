"""
XP (Experience Points) system handlers for Tvarkdarys bot
"""

import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from utils.storage import BotStorage
from utils.permissions import rate_limit

logger = logging.getLogger(__name__)

class XPSystem:
    """Handler class for XP system"""
    
    def __init__(self, storage: BotStorage):
        self.storage = storage
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages for XP gain"""
        if not update.effective_user or update.effective_user.is_bot:
            return
        
        # Only process group messages
        if update.effective_chat.type == 'private':
            return
        
        user = update.effective_user
        
        # Get or create user data
        user_data = self.storage.get_user(
            user_id=user.id,
            username=user.username or "",
            first_name=user.first_name or ""
        )
        
        # Try to add XP (respects cooldown)
        xp_gained = self.storage.add_xp(user.id, 1)
        
        if xp_gained:
            logger.debug(f"User {user.id} gained 1 XP. Total: {user_data.xp + 1}")
    
    @rate_limit(lambda self: self.storage, 5)
    async def check_xp_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /xp command"""
        user = update.effective_user
        target_user = user
        
        # Check if checking someone else's XP
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        elif context.args and context.args[0].isdigit():
            target_user_id = int(context.args[0])
            target_user_data = self.storage.get_user(target_user_id)
            if target_user_data:
                # Create a minimal user object for display
                class MinimalUser:
                    def __init__(self, user_data):
                        self.id = user_data.user_id
                        self.first_name = user_data.first_name
                        self.username = user_data.username
                
                target_user = MinimalUser(target_user_data)
            else:
                await update.message.reply_text("❌ User not found in the system.")
                return
        
        # Get user data
        user_data = self.storage.get_user(
            user_id=target_user.id,
            username=getattr(target_user, 'username', '') or "",
            first_name=getattr(target_user, 'first_name', '') or ""
        )
        
        # Calculate rank
        all_users = sorted(self.storage.users.values(), key=lambda x: x.xp, reverse=True)
        rank = next((i + 1 for i, u in enumerate(all_users) if u.user_id == target_user.id), len(all_users))
        
        # Calculate next level (every 100 XP = 1 level)
        current_level = user_data.xp // 100
        xp_for_next_level = (current_level + 1) * 100
        xp_needed = xp_for_next_level - user_data.xp
        
        # Time since last XP
        last_xp_time = ""
        if user_data.last_xp_time > 0:
            time_diff = time.time() - user_data.last_xp_time
            if time_diff < 60:
                last_xp_time = f"{int(time_diff)} seconds ago"
            elif time_diff < 3600:
                last_xp_time = f"{int(time_diff / 60)} minutes ago"
            else:
                last_xp_time = f"{int(time_diff / 3600)} hours ago"
        else:
            last_xp_time = "Never"
        
        xp_text = f"🏆 **XP Status**\n\n"
        xp_text += f"**User:** {target_user.first_name}"
        if hasattr(target_user, 'username') and target_user.username:
            xp_text += f" (@{target_user.username})"
        xp_text += f"\n**Level:** {current_level}"
        xp_text += f"\n**XP:** {user_data.xp:,}"
        xp_text += f"\n**Rank:** #{rank} of {len(self.storage.users)}"
        xp_text += f"\n**Next Level:** {xp_needed} XP needed"
        xp_text += f"\n**Last XP:** {last_xp_time}"
        
        # Progress bar
        progress = min(100, int((user_data.xp % 100) * 100 / 100))
        progress_bar = "▓" * (progress // 10) + "░" * (10 - progress // 10)
        xp_text += f"\n**Progress:** {progress_bar} {progress}%"
        
        if target_user.id != user.id:
            xp_text += f"\n\n*Requested by {user.mention_html()}*"
        
        await update.message.reply_text(xp_text, parse_mode='HTML')
    
    @rate_limit(lambda self: self.storage, 10)
    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /leaderboard command"""
        # Get top 10 users
        top_users = self.storage.get_leaderboard(update.effective_chat.id, 10)
        
        if not top_users:
            await update.message.reply_text(
                "📊 **XP Leaderboard**\n\n"
                "No users have gained XP yet!\n"
                "Start chatting to earn your first XP points! 💬"
            )
            return
        
        leaderboard_text = "🏆 **XP Leaderboard - Top 10**\n\n"
        
        # Medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users):
            rank = i + 1
            level = user_data.xp // 100
            
            # Get medal or rank number
            if rank <= 3:
                rank_display = medals[rank - 1]
            else:
                rank_display = f"{rank}."
            
            # Format username
            username_display = user_data.first_name
            if user_data.username:
                username_display += f" (@{user_data.username})"
            
            leaderboard_text += f"{rank_display} **{username_display}**\n"
            leaderboard_text += f"    Level {level} • {user_data.xp:,} XP\n\n"
        
        # Add user's position if not in top 10
        user_data = self.storage.get_user(update.effective_user.id)
        all_users = sorted(self.storage.users.values(), key=lambda x: x.xp, reverse=True)
        user_rank = next((i + 1 for i, u in enumerate(all_users) if u.user_id == update.effective_user.id), None)
        
        if user_rank and user_rank > 10:
            user_level = user_data.xp // 100
            leaderboard_text += f"---\n"
            leaderboard_text += f"**Your Position:** #{user_rank}\n"
            leaderboard_text += f"Level {user_level} • {user_data.xp:,} XP"
        
        leaderboard_text += f"\n\n💡 *Earn XP by chatting! +1 XP per message (1 min cooldown)*"
        
        await update.message.reply_text(leaderboard_text, parse_mode='Markdown')
