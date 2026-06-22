from __future__ import annotations

from pathlib import Path

import yaml

from app.domain import PriceReference


class PriceService:
    DISCLAIMER = "价格仅供参考，实际费用取决于城市、上门费、材料、现场复杂度和服务商报价。"

    def __init__(self, rules_path: Path | None = None):
        self.rules_path = rules_path or Path(__file__).resolve().parents[1] / "rules" / "price_rules.yaml"
        loaded = yaml.safe_load(self.rules_path.read_text(encoding="utf-8"))
        self.version = loaded["version"]
        self.rules = loaded["rules"]

    def match(self, scene_code: str, city_tier: str | None = None) -> PriceReference:
        tier = city_tier or "other"
        for rule in self.rules:
            if rule["scene_code"] == scene_code and rule["city_tier"] == tier:
                return PriceReference(
                    range=f"{rule['min_price']}-{rule['max_price']} 元/{rule.get('price_unit', '次')}/{rule.get('note', '')}",
                    disclaimer=self.DISCLAIMER,
                    has_reliable_price=True,
                    city_tier=tier,
                    version=self.version,
                )

        return PriceReference(
            range="暂无可靠参考价格",
            disclaimer=self.DISCLAIMER,
            has_reliable_price=False,
            city_tier=tier,
            version=self.version,
        )
