import numpy as np

PIXEL_SIZE_M  = 10        # Sentinel-2 resolution
PX_TO_KM2     = (PIXEL_SIZE_M ** 2) / 1e6

CLASS_NAMES   = ["Water", "Trees", "Buildings", "Open Land"]


def compute_livability(mask: np.ndarray) -> dict:
    total = mask.size
    counts = {
        "Water"    : int((mask == 0).sum()),
        "Trees"    : int((mask == 1).sum()),
        "Buildings": int((mask == 2).sum()),
        "Open Land": int((mask == 3).sum()),
    }
    pct     = {k: round(v / total * 100, 2) for k, v in counts.items()}
    area_km2 = {k: round(v * PX_TO_KM2, 4) for k, v in counts.items()}

    score = (
         0.40 * (counts["Trees"]     / total) +
         0.25 * (counts["Water"]     / total) -
         0.25 * (counts["Buildings"] / total) -
         0.10 * (counts["Open Land"] / total)
    )
    score = round(float(score), 4)

    if   score >= 0.10: zone = "Green"
    elif score >= 0.00: zone = "Yellow"
    else:               zone = "Red"

    alerts = []
    if pct["Buildings"] > 40:
        alerts.append("High urban density detected")
    if pct["Trees"] < 10:
        alerts.append("Very low vegetation coverage")
    if pct["Water"] < 5:
        alerts.append("Limited water body access")

    return {
        "score"     : score,
        "zone"      : zone,
        "pct"       : pct,
        "area_km2"  : area_km2,
        "total_px"  : int(total),
        "total_km2" : round(total * PX_TO_KM2, 4),
        "alerts"    : alerts,
    }
