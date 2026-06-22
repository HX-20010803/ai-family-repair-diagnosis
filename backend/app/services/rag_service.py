from __future__ import annotations

from pathlib import Path
import hashlib

import yaml


class RagService:
    KNOWLEDGE_VERSION = "knowledge:2026.06:template"

    DEFAULT = {
        "possible_causes": ["现场信息不足，可能存在多种原因"],
        "safe_self_checks": ["补充位置、持续时间、是否有异味或异常声音"],
        "risk_warnings": ["不要进行带电、燃气、高空或拆装类高风险操作"],
        "professional_required": True,
    }

    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or Path(__file__).resolve().parents[1] / "knowledge"
        self.knowledge = self._load_knowledge()
        self.KNOWLEDGE_VERSION = self._build_version()

    def retrieve(self, secondary: str, symptoms: str) -> dict:
        entries = self.knowledge.get(secondary)
        if not entries:
            fallback = dict(self.DEFAULT)
            fallback["secondary_category"] = secondary
            fallback["version"] = "fallback"
            return fallback
        best = entries[0]
        return {
            "secondary_category": best["secondary_category"],
            "possible_causes": best.get("possible_causes", []),
            "safe_self_checks": best.get("safe_self_checks", []),
            "risk_warnings": best.get("risk_warnings", []),
            "professional_required": bool(best.get("professional_required", True)),
            "price_scene_code": best.get("price_scene_code", secondary),
            "version": best.get("version", "unknown"),
        }

    def _load_knowledge(self) -> dict[str, list[dict]]:
        loaded: dict[str, list[dict]] = {}
        for path in sorted(self.knowledge_dir.glob("*.yaml")):
            items = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            for item in items:
                loaded.setdefault(item["secondary_category"], []).append(item)
        return loaded

    def _build_version(self) -> str:
        digest = hashlib.sha256()
        for path in sorted(self.knowledge_dir.glob("*.yaml")):
            digest.update(path.read_bytes())
        return f"knowledge:2026.06:{digest.hexdigest()[:8]}"
