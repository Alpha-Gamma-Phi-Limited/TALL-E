from __future__ import annotations

from typing import Any


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize(value: float, lower: float, upper: float) -> float:
    if upper <= lower:
        return 0.0
    return max(0.0, min(1.0, (value - lower) / (upper - lower)))


def _safe_tier(value: str | None, mapping: dict[str, float]) -> float:
    if not value:
        return 0.0
    return mapping.get(str(value).strip().lower(), 0.0)


def compute_value_score(category: str, attributes: dict[str, Any], effective_price: float | None) -> float | None:
    category_key = (category or "").strip().lower()
    if effective_price is None or effective_price <= 0:
        return None

    if category_key == "laptops":
        cpu_score = _to_float(attributes.get("cpu_score"))
        ram_gb = _to_float(attributes.get("ram_gb"))
        storage_gb = _to_float(attributes.get("storage_gb"))
        if cpu_score is None or ram_gb is None or storage_gb is None:
            return None
        perf = (
            0.45 * _normalize(cpu_score, 1000, 10000)
            + 0.30 * _normalize(ram_gb, 4, 64)
            + 0.25 * _normalize(storage_gb, 128, 4000)
        )
        price_penalty = _normalize(effective_price, 700, 4500)
        return max(0.0, min(1.0, perf * 0.85 + (1 - price_penalty) * 0.15))

    if category_key == "monitors":
        refresh = _to_float(attributes.get("refresh_rate_hz"))
        panel = _safe_tier(attributes.get("panel_type"), {"tn": 0.4, "ips": 0.75, "va": 0.7, "oled": 1.0})
        resolution = _safe_tier(attributes.get("resolution"), {"1080p": 0.55, "1440p": 0.8, "4k": 1.0})
        if refresh is None:
            return None
        perf = 0.5 * _normalize(refresh, 60, 240) + 0.25 * panel + 0.25 * resolution
        price_penalty = _normalize(effective_price, 200, 2500)
        return max(0.0, min(1.0, perf * 0.8 + (1 - price_penalty) * 0.2))

    if category_key == "phones":
        chipset = _safe_tier(attributes.get("chipset_tier"), {"entry": 0.4, "mid": 0.65, "high": 0.85, "flagship": 1.0})
        ram_gb = _to_float(attributes.get("ram_gb"))
        storage_gb = _to_float(attributes.get("storage_gb"))
        battery = _to_float(attributes.get("battery_mah"))
        if ram_gb is None or storage_gb is None:
            return None
        perf = (
            0.4 * chipset
            + 0.2 * _normalize(ram_gb, 4, 16)
            + 0.25 * _normalize(storage_gb, 64, 1024)
            + 0.15 * _normalize(battery or 4000, 3000, 6000)
        )
        price_penalty = _normalize(effective_price, 350, 2400)
        return max(0.0, min(1.0, perf * 0.82 + (1 - price_penalty) * 0.18))

    return None
