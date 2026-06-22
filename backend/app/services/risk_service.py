from __future__ import annotations

from app.domain import RiskAssessment


class RiskService:
    """Rule-first high-risk recall with conservative negation handling."""

    NEGATION_WORDS = ("没有", "无", "没闻到", "不存在", "不是", "未发现", "不在")
    UNCERTAIN_WORDS = ("担心", "是不是", "好像", "疑似", "可能", "不确定")

    RULES = [
        {
            "risk_type": "gas",
            "keywords": ["燃气味", "煤气味", "燃气泄漏", "刺鼻气味", "煤气泄漏"],
            "urgency_level": "S",
            "action": "先关闭燃气阀门，开窗通风，不开关电器，尽快联系燃气公司；紧急时拨打 119。",
        },
        {
            "risk_type": "gas",
            "context_keywords": ["燃气灶", "煤气灶", "燃气管", "燃气", "煤气", "灶"],
            "keywords": ["气味", "味道", "有味", "刺鼻", "闻到"],
            "urgency_level": "S",
            "action": "先关闭燃气阀门，开窗通风，不开关电器，尽快联系燃气公司；紧急时拨打 119。",
        },
        {
            "risk_type": "electric_smoke",
            "keywords": ["冒烟", "火花", "插座烧黑", "烧焦", "漏电", "焦味", "噼啪响"],
            "urgency_level": "S",
            "action": "停止使用相关电器，关闭空气开关，远离现场并联系专业电工；起火时拨打 119。",
        },
        {
            "risk_type": "electric_smoke",
            "context_keywords": ["插座", "插排", "插头", "开关", "配电箱"],
            "keywords": ["发黑", "发烫", "黑印"],
            "urgency_level": "S",
            "action": "停止使用相关电器，关闭空气开关，远离现场并联系专业电工；起火时拨打 119。",
        },
        {
            "risk_type": "electric",
            "context_keywords": ["跳闸", "漏保"],
            "keywords": ["重新开又跳", "反复跳", "一开就跳", "一启动就跳"],
            "urgency_level": "S",
            "action": "不要反复合闸或继续试用，停止使用相关电器并联系专业电工检查。",
        },
        {
            "risk_type": "water_near_electric",
            "keywords": ["漏水靠近电", "水碰到插座", "灯具漏水", "电源附近漏水"],
            "urgency_level": "S",
            "action": "先远离电源并关闭相关电路，不要自行拆修，联系物业或水电师傅现场处理。",
        },
        {
            "risk_type": "water_near_electric",
            "context_keywords": ["漏水", "渗水", "滴水", "返水", "进水", "泡了", "打湿", "水漫", "水溅湿", "发潮", "返潮", "有水"],
            "keywords": ["插座", "插排", "灯", "灯具", "灯罩", "开关", "电源", "电器", "配电箱", "电热水器", "油烟机", "冰箱"],
            "urgency_level": "S",
            "action": "先远离电源并关闭相关电路，不要自行拆修，联系物业或水电师傅现场处理。",
        },
        {
            "risk_type": "locked_in",
            "keywords": ["被困", "门打不开出不去", "老人被锁", "孩子被锁", "小孩被锁"],
            "urgency_level": "S",
            "action": "优先确认人身安全，联系物业、正规开锁服务或紧急救助。",
        },
        {
            "risk_type": "locked_in",
            "context_keywords": ["老人", "孩子", "小孩", "有人", "在屋里", "在家", "里面", "卫生间里"],
            "keywords": ["出不来", "打不开", "被锁", "反锁", "困", "头晕"],
            "urgency_level": "S",
            "action": "优先确认人身安全，联系物业、正规开锁服务或紧急救助。",
        },
        {
            "risk_type": "falling_object",
            "context_keywords": ["窗户", "玻璃", "窗扇", "外开窗", "合页", "高层"],
            "keywords": ["高层", "掉下来", "坠落", "裂了", "裂纹"],
            "urgency_level": "S",
            "action": "远离窗边和玻璃，不要探身或强行操作，联系物业或门窗师傅现场处理。",
        },
    ]

    def assess(self, text: str) -> RiskAssessment:
        normalized = text.strip()
        for rule in self.RULES:
            matches = self._match_rule(rule, normalized)
            if not matches:
                continue

            if self._is_explicitly_negated(normalized, matches):
                return RiskAssessment(
                    triggered=False,
                    risk_type=rule["risk_type"],
                    matched_keywords=matches,
                    explicitly_negated=True,
                )

            return RiskAssessment(
                triggered=True,
                risk_type=rule["risk_type"],
                level=rule["urgency_level"],
                action=rule["action"],
                matched_keywords=matches,
                requires_confirmation=self._is_uncertain(normalized),
            )

        return RiskAssessment(triggered=False)

    def _match_rule(self, rule: dict, text: str) -> list[str]:
        keyword_matches = [kw for kw in rule["keywords"] if kw in text]
        if not keyword_matches:
            return []
        context_keywords = rule.get("context_keywords") or []
        if not context_keywords:
            return keyword_matches
        context_matches = [kw for kw in context_keywords if kw in text]
        if not context_matches:
            return []
        return context_matches + keyword_matches

    def _is_explicitly_negated(self, text: str, matches: list[str]) -> bool:
        for keyword in matches:
            idx = text.find(keyword)
            prefix = text[max(0, idx - 8) : idx]
            if "是不是" in prefix or "是否" in prefix:
                continue
            if any(word in prefix for word in self.NEGATION_WORDS):
                return True
        return False

    def _is_uncertain(self, text: str) -> bool:
        return any(word in text for word in self.UNCERTAIN_WORDS)
