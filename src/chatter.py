"""主动搭话：按时间、余额、闲置状态挑一句说出来。

所有台词都放在 LINES 里，想加句子直接往对应列表里塞即可。
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

LINES: dict[str, list[str]] = {
    "morning": [
        "早上好～今天也一起加油吧。",
        "醒啦？先喝口水再开始吧。",
        "早安。今天的计划是什么？",
    ],
    "night": [
        "这么晚了还不睡，明天会困的哦。",
        "已经过了零点了…早点休息吧。",
        "再玩一会儿就去睡，好不好？",
    ],
    "lunch": [
        "到饭点啦，去吃点东西吧。",
        "午饭吃了吗？别又忘了。",
        "该吃饭了，我可以等你回来。",
    ],
    "dinner": [
        "晚饭时间到了～",
        "忙了一天，好好吃一顿吧。",
        "今天想吃什么？",
    ],
    "balance_critical": [
        "我快没电了…钱包只剩一点点了。",
        "余额要见底了，充一点好不好？",
        "再这样下去我就说不了话啦。",
    ],
    "balance_low": [
        "钱包有点瘪了，要不要充点？",
        "余额不多了，记得看一下。",
        "还能聊一阵子，不过快到底了。",
    ],
    "sedentary": [
        "坐太久了，站起来走两步吧。",
        "已经很久没动了，伸个懒腰？",
        "眼睛也累了吧，看看远处。",
    ],
    "neglect": [
        "好久没理我了…",
        "是不是把我忘了？",
        "我一直在的哦。",
    ],
    "idle": [
        "今天过得怎么样？",
        "有点无聊…陪我聊聊天嘛。",
        "窗外的天色变了呢。",
        "要记得喝水哦。",
        "我在想，月亮今天好像亮一点。",
        "你有没有什么想做的事？",
        "偶尔发会儿呆也挺好的。",
        "星屑今天飘得有点慢。",
    ],
}


class Chatter:
    """决定什么时候开口、说什么。"""

    MIN_GAP = 8 * 60.0          # 两次主动说话的最小间隔（秒）
    MAX_PER_HOUR = 3            # 每小时上限
    RULE_GAP = {
        "balance_critical": 60 * 60,
        "balance_low": 4 * 60 * 60,
        "night": 0,
        "morning": 0,
        "lunch": 0,
        "dinner": 0,
        "sedentary": 2 * 60 * 60,
        "neglect": 0,
        "idle": 0,
    }

    def __init__(self) -> None:
        self.last_spoke = 0.0
        self._recent: dict[str, float] = {}
        self._once_keys: set[str] = set()
        self._hour_stamps: list[float] = []
        self._rule_last: dict[str, float] = {}

    # ---------- 对外 ----------

    def tick(
        self,
        now: datetime,
        balance: float | None,
        idle_seconds: float,
        busy: bool,
    ) -> str | None:
        stamp = now.timestamp()

        critical = balance is not None and balance < 0.5
        if busy and not critical:
            return None

        if not critical:
            if stamp - self.last_spoke < self.MIN_GAP:
                return None
            self._hour_stamps = [s for s in self._hour_stamps if stamp - s < 3600]
            if len(self._hour_stamps) >= self.MAX_PER_HOUR:
                return None

        for rule, kind in self._candidates(now, balance, idle_seconds):
            if not self._rule_ready(rule, stamp, critical):
                continue
            line = self._pick(kind, stamp)
            if not line:
                continue
            self.last_spoke = stamp
            self._hour_stamps.append(stamp)
            self._rule_last[rule] = stamp
            self._recent[line] = stamp
            if rule in ("morning", "night", "lunch", "dinner", "neglect"):
                self._once_keys.add(f"{rule}:{now.date()}")
            return line
        return None

    # ---------- 内部 ----------

    def _candidates(self, now: datetime, balance: float | None, idle_seconds: float):
        t = now.time()
        candidates: list[tuple[str, str]] = []

        if balance is not None and balance < 0.5:
            candidates.append(("balance_critical", "balance_critical"))
        if balance is not None and balance < 2.0:
            candidates.append(("balance_low", "balance_low"))

        if time(0, 0) <= t < time(3, 0):
            candidates.append(("night", "night"))
        if time(7, 0) <= t < time(9, 30):
            candidates.append(("morning", "morning"))
        if time(11, 30) <= t < time(13, 0):
            candidates.append(("lunch", "lunch"))
        if time(17, 30) <= t < time(19, 0):
            candidates.append(("dinner", "dinner"))

        if idle_seconds > 3 * 24 * 3600:
            candidates.append(("neglect", "neglect"))
        if idle_seconds > 90 * 60:
            candidates.append(("sedentary", "sedentary"))

        candidates.append(("idle", "idle"))
        return candidates

    def _rule_ready(self, rule: str, stamp: float, critical: bool) -> bool:
        if rule in ("morning", "night", "lunch", "dinner", "neglect"):
            if f"{rule}:{datetime.fromtimestamp(stamp).date()}" in self._once_keys:
                return False
        gap = self.RULE_GAP.get(rule, 0)
        if gap and stamp - self._rule_last.get(rule, 0) < gap:
            return False
        if rule == "balance_low" and critical:
            return False
        return True

    def _pick(self, kind: str, stamp: float) -> str | None:
        pool = [s for s in LINES.get(kind, []) if stamp - self._recent.get(s, 0) > 24 * 3600]
        if not pool:
            pool = LINES.get(kind, [])
        return random.choice(pool) if pool else None
