"""Rule-based proactive chat scheduling with configurable local frequency."""
from __future__ import annotations

import random
from datetime import datetime, time

LINES: dict[str, list[str]] = {
    "morning": ["早上好～今天也一起加油吧。", "醒啦？先喝口水再开始吧。", "早安。今天的计划是什么？"],
    "night": ["这么晚了还不睡，明天会困的哦。", "已经过了零点了…早点休息吧。", "今天辛苦了，记得给自己留些休息时间。"],
    "lunch": ["到饭点啦，去吃点东西吧。", "午饭吃了吗？别忘了照顾好自己。", "该吃饭了，休息一下也不错。"],
    "dinner": ["晚饭时间到了～", "忙了一天，好好吃一顿吧。", "今天想吃什么？"],
    "balance_critical": ["API 余额快用完了，可以去设置里看看。", "当前服务余额不多啦，记得确认一下。"],
    "balance_low": ["API 余额不多了，方便时可以检查一下。", "还可以继续聊一阵，记得留意服务余额。"],
    "sedentary": ["坐了好一会儿啦，想不想起来活动一下？", "可以稍微伸个懒腰、看看远处。", "休息一下眼睛也不错。"],
    "idle": ["今天过得怎么样？", "有空的话，愿意和我聊聊今天吗？", "希望你今天也有一点属于自己的轻松时刻。", "我在这儿，需要聊天时叫我就好。", "偶尔发会儿呆也挺好的。", "你有没有什么想做的事？", "星屑今天飘得有点慢。"],
}


class Chatter:
    """Honor configured target frequency, temporarily backing off after no response."""
    MIN_FREQUENCY = 0.01
    MAX_FREQUENCY = 10.0
    MIN_GAP = 6.0
    MAX_GAP = 3 * 60 * 60.0
    MAX_PER_HOUR = 2  # retained for compatibility; configured frequency supersedes caps
    MAX_PER_DAY = 8
    STEP = 5 * 60.0
    RULE_GAP = {"balance_critical": 60 * 60, "balance_low": 4 * 60 * 60,
                "night": 0, "morning": 0, "lunch": 0, "dinner": 0,
                "sedentary": 2 * 60 * 60, "idle": 0}

    def __init__(self) -> None:
        self.last_spoke = 0.0
        self.current_gap = 60 * 60.0  # legacy adaptation metric; not a scheduler limit
        self._hour_stamps: list[float] = []
        self._day_stamps: list[float] = []
        self._recent: dict[str, float] = {}
        self._once_keys: set[str] = set()
        self._rule_last: dict[str, float] = {}
        self._unanswered = 0
        self._unanswered_backoff = 0.0
        self._last_response = 0.0

    def on_user_response(self, now: datetime) -> None:
        stamp = now.timestamp()
        if self._last_response and 0 <= stamp - self._last_response < 30 * 60:
            self.current_gap = max(self.MIN_GAP, self.current_gap - self.STEP)
        if self._last_response and 0 <= stamp - self._last_response < 30 * 60:
            self._unanswered_backoff = max(0.0, self._unanswered_backoff - self.STEP)
        self._last_response = stamp
        self._unanswered = 0
        self._unanswered_backoff = 0.0

    def on_user_chat(self) -> None:
        self.current_gap = max(self.MIN_GAP, self.current_gap - self.STEP)
        self._unanswered = 0
        self._unanswered_backoff = 0.0

    def on_unanswered(self) -> None:
        """Increase a temporary interval after an unanswered/hidden bubble."""
        self._unanswered += 1
        self.current_gap = min(self.MAX_GAP, self.current_gap + self.STEP * min(self._unanswered, 3))
        self._unanswered_backoff = min(
            self.MAX_GAP, self._unanswered_backoff + self.STEP * min(self._unanswered, 3)
        )

    def reset_adaptation(self) -> None:
        self.current_gap = 60 * 60.0
        self._unanswered = 0
        self._unanswered_backoff = 0.0
        self._last_response = 0.0

    def tick(self, now: datetime, balance: float | None, idle_seconds: float, busy: bool,
             quiet_enabled: bool = False, quiet_start: str = "23:00", quiet_end: str = "08:00",
             frequency_per_minute: float = 0.02, enabled: bool = True) -> str | None:
        if not enabled or busy:
            return None
        try:
            frequency = float(frequency_per_minute)
        except (TypeError, ValueError):
            frequency = 0.02
        if frequency != frequency or frequency <= 0:
            frequency = 0.02
        frequency = min(self.MAX_FREQUENCY, max(self.MIN_FREQUENCY, frequency))
        if quiet_enabled and self._in_quiet_hours(now.time().replace(tzinfo=None), quiet_start, quiet_end):
            return None

        stamp = now.timestamp()
        if stamp < self.last_spoke:
            self.last_spoke = 0.0
            self._hour_stamps.clear()
            self._day_stamps.clear()
            self._rule_last.clear()
            self._recent.clear()
            self._once_keys.clear()
        target_gap = max(self.MIN_GAP, 60.0 / frequency)
        if stamp - self.last_spoke < max(target_gap, self._unanswered_backoff):
            return None

        for rule, kind in self._candidates(now, balance, idle_seconds):
            if not self._rule_ready(rule, stamp):
                continue
            line = self._pick(kind, stamp)
            if not line:
                continue
            self.last_spoke = stamp
            self._hour_stamps.append(stamp)
            self._day_stamps.append(stamp)
            self._rule_last[rule] = stamp
            self._recent[line] = stamp
            if rule in ("morning", "night", "lunch", "dinner"):
                self._once_keys.add(f"{rule}:{now.date()}")
            return line
        return None

    @staticmethod
    def _in_quiet_hours(current: time, start_text: str, end_text: str) -> bool:
        try:
            start, end = time.fromisoformat(start_text), time.fromisoformat(end_text)
        except (TypeError, ValueError):
            return False
        if start == end:
            return True
        if start < end:
            return start <= current < end
        return current >= start or current < end

    def _candidates(self, now: datetime, balance: float | None, idle_seconds: float):
        t = now.time().replace(tzinfo=None)
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
        if idle_seconds > 90 * 60:
            candidates.append(("sedentary", "sedentary"))
        candidates.append(("idle", "idle"))
        return candidates

    def _rule_ready(self, rule: str, stamp: float) -> bool:
        if rule in ("morning", "night", "lunch", "dinner"):
            if f"{rule}:{datetime.fromtimestamp(stamp).date()}" in self._once_keys:
                return False
        gap = self.RULE_GAP.get(rule, 0)
        return not gap or stamp - self._rule_last.get(rule, 0) >= gap

    def _pick(self, kind: str, stamp: float) -> str | None:
        pool = [line for line in LINES.get(kind, []) if stamp - self._recent.get(line, 0) > 24 * 3600]
        if not pool:
            pool = LINES.get(kind, [])
        return random.choice(pool) if pool else None
