from __future__ import annotations


class QuestionService:
    MAX_ROUNDS = 3
    MAX_QUESTIONS = 3

    QUESTIONS = {
        "water_leak": ["漏水位置在哪里？", "是持续滴水还是偶尔渗水？", "是否靠近灯具、插座或电器？"],
        "drain_blocked": ["堵塞位置在哪里？", "是否有返水或完全不下水？", "是否已经尝试过低风险疏通？"],
        "ac_not_cooling": ["空调用了几年？", "是否有风但不冷？", "滤网近期是否清洗过？"],
        "circuit_trip": ["是全屋跳闸还是局部跳闸？", "跳闸前使用了哪个电器？", "是否闻到烧焦味或看到插座发热？"],
        "lock_failure": ["人在门内还是门外？", "是机械锁还是指纹锁？", "是否尝试更换电池或备用钥匙？"],
        "wall_mold": ["发霉位置在哪里？", "面积是否持续扩大？", "是否靠近卫生间、外墙或近期漏水位置？"],
        "water_heater_failure": ["热水器是燃气还是电热水器？", "是否有故障码？", "是否闻到燃气味？"],
        "range_hood_gas_stove": ["是油烟机还是燃气灶问题？", "是否闻到燃气味？", "近期是否清洁或更换过电池？"],
        "floor_drain_smell": ["异味来自哪个位置？", "是否长期不用或水封干了？", "是否伴随返水或下水慢？"],
        "window_hardware": ["是窗户、门还是纱窗问题？", "是否关不严或明显松动？", "是否位于高层且有坠落风险？"],
    }

    def should_ask(self, text: str, secondary: str, round_count: int, high_risk: bool) -> bool:
        if high_risk:
            return False
        if round_count >= self.MAX_ROUNDS:
            return False
        return len(text.strip()) < 18 or self._has_sparse_context(text)

    def next_questions(self, secondary: str, asked: list[str] | None = None) -> list[str]:
        asked_set = set(asked or [])
        candidates = [q for q in self.QUESTIONS.get(secondary, []) if q not in asked_set]
        return candidates[: self.MAX_QUESTIONS]

    def _has_sparse_context(self, text: str) -> bool:
        signals = ("多久", "位置", "靠近", "故障码", "持续", "味", "电", "返水", "楼上", "外机")
        return not any(signal in text for signal in signals)

