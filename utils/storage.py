"""
In-memory storage system for Tvarkdarys bot
Handles data persistence for users, groups, and bot settings
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

@dataclass
class UserData:
    """User data structure"""
    user_id: int
    username: str
    first_name: str
    xp: int = 0
    last_xp_time: float = 0
    warnings: int = 0
    invites_count: int = 0
    join_date: float = None
    
    def __post_init__(self):
        if self.join_date is None:
            self.join_date = time.time()

@dataclass 
class GroupSettings:
    """Group settings structure"""
    chat_id: int
    rules: List[str] = None
    welcome_message: str = ""
    admins: List[int] = None
    invite_links: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.rules is None:
            self.rules = []
        if self.admins is None:
            self.admins = []
        if self.invite_links is None:
            self.invite_links = {}

class BotStorage:
    """In-memory storage for bot data"""
    
    def __init__(self):
        self.users: Dict[int, UserData] = {}
        self.groups: Dict[int, GroupSettings] = {}
        self.user_last_command: Dict[int, float] = {}
        self.banned_users: Dict[int, List[int]] = {}  # chat_id -> [user_ids]
        self.muted_users: Dict[int, Dict[int, float]] = {}  # chat_id -> {user_id: unmute_time}
        
    def get_user(self, user_id: int, username: str = "", first_name: str = "") -> UserData:
        """Get or create user data"""
        if user_id not in self.users:
            self.users[user_id] = UserData(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
        else:
            # Update username and first_name if provided
            if username:
                self.users[user_id].username = username
            if first_name:
                self.users[user_id].first_name = first_name
                
        return self.users[user_id]
    
    def get_group_settings(self, chat_id: int) -> GroupSettings:
        """Get or create group settings"""
        if chat_id not in self.groups:
            self.groups[chat_id] = GroupSettings(chat_id=chat_id)
        return self.groups[chat_id]
    
    def add_xp(self, user_id: int, amount: int = 1) -> bool:
        """Add XP to user if cooldown has passed"""
        user = self.get_user(user_id)
        current_time = time.time()
        
        # Check cooldown (60 seconds)
        if current_time - user.last_xp_time < 60:
            return False
            
        user.xp += amount
        user.last_xp_time = current_time
        return True
    
    def get_leaderboard(self, chat_id: int, limit: int = 10) -> List[UserData]:
        """Get top users by XP"""
        # Filter users who have been active in this chat (simplified)
        all_users = list(self.users.values())
        all_users.sort(key=lambda x: x.xp, reverse=True)
        return all_users[:limit]
    
    def set_rules(self, chat_id: int, rules: List[str]):
        """Set rules for a group"""
        group_settings = self.get_group_settings(chat_id)
        group_settings.rules = rules
    
    def get_rules(self, chat_id: int) -> List[str]:
        """Get rules for a group"""
        group_settings = self.get_group_settings(chat_id)
        return group_settings.rules
    
    def set_welcome_message(self, chat_id: int, message: str):
        """Set welcome message for a group"""
        group_settings = self.get_group_settings(chat_id)
        group_settings.welcome_message = message
    
    def get_welcome_message(self, chat_id: int) -> str:
        """Get welcome message for a group"""
        group_settings = self.get_group_settings(chat_id)
        return group_settings.welcome_message
    
    def add_warning(self, chat_id: int, user_id: int) -> int:
        """Add warning to user and return total warnings"""
        user = self.get_user(user_id)
        user.warnings += 1
        return user.warnings
    
    def get_warnings(self, user_id: int) -> int:
        """Get warning count for user"""
        user = self.get_user(user_id)
        return user.warnings
    
    def clear_warnings(self, user_id: int):
        """Clear warnings for user"""
        user = self.get_user(user_id)
        user.warnings = 0
    
    def ban_user(self, chat_id: int, user_id: int):
        """Add user to banned list"""
        if chat_id not in self.banned_users:
            self.banned_users[chat_id] = []
        if user_id not in self.banned_users[chat_id]:
            self.banned_users[chat_id].append(user_id)
    
    def unban_user(self, chat_id: int, user_id: int):
        """Remove user from banned list"""
        if chat_id in self.banned_users and user_id in self.banned_users[chat_id]:
            self.banned_users[chat_id].remove(user_id)
    
    def is_banned(self, chat_id: int, user_id: int) -> bool:
        """Check if user is banned"""
        return chat_id in self.banned_users and user_id in self.banned_users[chat_id]
    
    def mute_user(self, chat_id: int, user_id: int, duration_minutes: int = 60):
        """Mute user for specified duration"""
        if chat_id not in self.muted_users:
            self.muted_users[chat_id] = {}
        
        unmute_time = time.time() + (duration_minutes * 60)
        self.muted_users[chat_id][user_id] = unmute_time
    
    def unmute_user(self, chat_id: int, user_id: int):
        """Unmute user"""
        if chat_id in self.muted_users and user_id in self.muted_users[chat_id]:
            del self.muted_users[chat_id][user_id]
    
    def is_muted(self, chat_id: int, user_id: int) -> bool:
        """Check if user is muted"""
        if chat_id not in self.muted_users or user_id not in self.muted_users[chat_id]:
            return False
        
        unmute_time = self.muted_users[chat_id][user_id]
        if time.time() >= unmute_time:
            # Mute expired, remove it
            del self.muted_users[chat_id][user_id]
            return False
        
        return True
    
    def add_invite_use(self, user_id: int):
        """Add invite use to user"""
        user = self.get_user(user_id)
        user.invites_count += 1
    
    def check_command_cooldown(self, user_id: int, cooldown_seconds: int = 3) -> bool:
        """Check if user can use command (rate limiting)"""
        current_time = time.time()
        last_command_time = self.user_last_command.get(user_id, 0)
        
        if current_time - last_command_time < cooldown_seconds:
            return False
        
        self.user_last_command[user_id] = current_time
        return True
    
    def add_admin(self, chat_id: int, user_id: int):
        """Add admin to group"""
        group_settings = self.get_group_settings(chat_id)
        if user_id not in group_settings.admins:
            group_settings.admins.append(user_id)
    
    def is_admin(self, chat_id: int, user_id: int) -> bool:
        """Check if user is admin"""
        group_settings = self.get_group_settings(chat_id)
        return user_id in group_settings.admins
    
    def track_invite_link(self, chat_id: int, invite_link: str, creator_id: int):
        """Track invite link usage"""
        group_settings = self.get_group_settings(chat_id)
        group_settings.invite_links[invite_link] = {
            'creator_id': creator_id,
            'uses': 0,
            'created_time': time.time()
        }
    
    def use_invite_link(self, chat_id: int, invite_link: str) -> Optional[int]:
        """Record invite link use and return creator ID"""
        group_settings = self.get_group_settings(chat_id)
        if invite_link in group_settings.invite_links:
            group_settings.invite_links[invite_link]['uses'] += 1
            return group_settings.invite_links[invite_link]['creator_id']
        return None
    
    def get_invite_stats(self, chat_id: int) -> Dict[str, Any]:
        """Get invite link statistics"""
        group_settings = self.get_group_settings(chat_id)
        return group_settings.invite_links
