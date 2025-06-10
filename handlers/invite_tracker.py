"""
Invite tracking system handlers for Tvarkdarys bot
"""

import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from utils.storage import BotStorage
from utils.permissions import admin_required, group_only, rate_limit

logger = logging.getLogger(__name__)

class InviteTracker:
    """Handler class for invite tracking"""
    
    def __init__(self, storage: BotStorage):
        self.storage = storage
    
    async def handle_member_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when a member joins the chat"""
        if not update.chat_member or not update.chat_member.new_chat_member:
            return
        
        # Check if it's a new member joining
        if update.chat_member.new_chat_member.status != "member":
            return
        
        new_user = update.chat_member.new_chat_member.user
        chat_id = update.effective_chat.id
        
        # Skip if bot joins
        if new_user.is_bot:
            return
        
        logger.info(f"New member {new_user.id} joined chat {chat_id}")
        
        # Try to determine who invited them (simplified approach)
        # In a real implementation, you'd need to track invite links
        # For now, we'll just log the join
        user_data = self.storage.get_user(
            user_id=new_user.id,
            username=new_user.username or "",
            first_name=new_user.first_name or ""
        )
        
        # Could implement invite link tracking here
        # For MVP, we'll just track joins
        
    @rate_limit(lambda self: self.storage, 5)
    async def check_invites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /invites command"""
        user = update.effective_user
        target_user = user
        
        # Check if checking someone else's invites
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
        
        # Calculate invite rank
        all_users = sorted(self.storage.users.values(), key=lambda x: x.invites_count, reverse=True)
        invite_rank = next((i + 1 for i, u in enumerate(all_users) if u.user_id == target_user.id), len(all_users))
        
        invites_text = f"👥 **Invite Statistics**\n\n"
        invites_text += f"**User:** {target_user.first_name}"
        if hasattr(target_user, 'username') and target_user.username:
            invites_text += f" (@{target_user.username})"
        invites_text += f"\n**Invites:** {user_data.invites_count}"
        invites_text += f"\n**Rank:** #{invite_rank} of {len(self.storage.users)}"
        
        # Calculate join date
        if user_data.join_date:
            join_time = time.time() - user_data.join_date
            if join_time < 86400:  # Less than 1 day
                join_display = f"{int(join_time / 3600)} hours ago"
            else:
                join_display = f"{int(join_time / 86400)} days ago"
            invites_text += f"\n**Joined:** {join_display}"
        
        if target_user.id != user.id:
            invites_text += f"\n\n*Requested by {user.mention_html()}*"
        
        await update.message.reply_text(invites_text, parse_mode='HTML')
    
    @group_only
    @admin_required
    @rate_limit(lambda self: self.storage, 10)
    async def invite_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /invitestats command - Admin only"""
        chat_id = update.effective_chat.id
        invite_data = self.storage.get_invite_stats(chat_id)
        
        if not invite_data:
            await update.message.reply_text(
                "📊 **Invite Statistics**\n\n"
                "No invite links are being tracked yet.\n"
                "Invite tracking will start automatically when members join!"
            )
            return
        
        stats_text = "📊 **Invite Link Statistics**\n\n"
        
        # Sort by usage
        sorted_invites = sorted(invite_data.items(), key=lambda x: x[1]['uses'], reverse=True)
        
        for i, (link, data) in enumerate(sorted_invites[:10], 1):
            creator_id = data['creator_id']
            uses = data['uses']
            created_time = data['created_time']
            
            # Get creator info
            creator_data = self.storage.get_user(creator_id)
            creator_name = creator_data.first_name if creator_data else f"User {creator_id}"
            
            # Format creation time
            time_diff = time.time() - created_time
            if time_diff < 86400:
                time_display = f"{int(time_diff / 3600)}h ago"
            else:
                time_display = f"{int(time_diff / 86400)}d ago"
            
            stats_text += f"**{i}.** {creator_name}\n"
            stats_text += f"    Uses: {uses} • Created: {time_display}\n"
            stats_text += f"    Link: `{link[:20]}...`\n\n"
        
        # Summary
        total_links = len(invite_data)
        total_uses = sum(data['uses'] for data in invite_data.values())
        
        stats_text += f"**Summary:**\n"
        stats_text += f"• Total Links: {total_links}\n"
        stats_text += f"• Total Uses: {total_uses}\n"
        
        # Top inviter
        if invite_data:
            top_creator_id = max(invite_data.values(), key=lambda x: x['uses'])['creator_id']
            top_creator = self.storage.get_user(top_creator_id)
            top_creator_name = top_creator.first_name if top_creator else f"User {top_creator_id}"
            stats_text += f"• Top Inviter: {top_creator_name}"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    def track_invite_usage(self, chat_id: int, invite_link: str, inviter_id: int):
        """Track usage of an invite link"""
        # Store the invite link tracking
        self.storage.track_invite_link(chat_id, invite_link, inviter_id)
        
        # Award the inviter
        self.storage.add_invite_use(inviter_id)
        
        logger.info(f"Invite link used in chat {chat_id} by inviter {inviter_id}")
