"""
Antiflood handler: gaudo daug trumpų žinučių per trumpą laiką ir automatiškai mutina.
"""

import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, Deque

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes


@dataclass
class FloodRule:
    messages: int
    window_sec: int
    action: str  # "warn" | "mute"
    mute_minutes: int = 0


DEFAULT_RULES = [
    FloodRule(messages=5,  window_sec=10, action="warn"),
    FloodRule(messages=8,  window_sec=15, action="mute", mute_minutes=5),
    FloodRule(messages=12, window_sec=20, action="mute", mute_minutes=30),
]


class AntiFlood:
    def __init__(self, owner_id: int, rules=DEFAULT_RULES):
        self.owner_id = owner_id
        self.rules = rules
        self._bucket: Dict[int, Dict[int, Deque[float]]] = {}

    def _now(self) -> float:
        return time.time()

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        user = update.effective_user
        msg = update.effective_message
        if not chat or not user or not msg or user.is_bot:
            return

        if user.id == self.owner_id:
            return

        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            if member.status in ("administrator", "creator"):
                return
        except Exception:
            pass

        chat_map = self._bucket.setdefault(chat.id, {})
        q = chat_map.setdefault(user.id, deque(maxlen=50))

        now = self._now()
        q.append(now)

        triggered = None
        for rule in sorted(self.rules, key=lambda r: (r.mute_minutes, r.messages), reverse=True):
            while q and (now - q[0]) > rule.window_sec:
                q.popleft()
            if len(q) >= rule.messages:
                triggered = rule
                break

        if not triggered:
            return

        try:
            await msg.delete()
        except Exception:
            pass

        if triggered.action == "warn":
            await context.bot.send_message(
                chat_id=chat.id,
                text=f"⚠️ {user.mention_html()}, ne floodink. Susirink žodžius į vieną žinutę.",
                parse_mode="HTML"
            )
            return

        if triggered.action == "mute":
            duration_min = triggered.mute_minutes
            until_date = int(now + duration_min * 60)
            perms = ChatPermissions(can_send_messages=False)
            try:
                await context.bot.restrict_chat_member(chat_id=chat.id, user_id=user.id, permissions=perms, until_date=until_date)
                await context.bot.send_message(chat_id=chat.id, text=f"🔇 {user.mention_html()} užfloodino. Mute {duration_min} min.", parse_mode="HTML")
                chat_map[user.id] = deque(maxlen=50)
            except Exception as e:
                await context.bot.send_message(chat_id=chat.id, text=f"⚠️ Nepavyko pritaikyti mute: {e}")
