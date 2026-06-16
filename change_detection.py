import numpy as np

PIXEL_SIZE_M = 10
PX_TO_KM2    = (PIXEL_SIZE_M ** 2) / 1e6

CLASS_NAMES  = ["Water", "Trees", "Buildings", "Open Land"]

# Change overlay colors (RGBA)
# New buildings  → red
# Lost trees     → orange
# New water      → cyan
# Lost water     → brown
# Unchanged      → transparent

CHANGE_COLORS = {
    "new_buildings" : [220,  50,  32, 200],
    "lost_trees"    : [230, 120,  20, 200],
    "new_water"     : [ 20, 180, 220, 200],
    "lost_water"    : [160,  90,  30, 200],
    "new_openland"  : [200, 200,  50, 160],
    "unchanged"     : [  0,   0,   0,   0],
}


def compute_change(mask_old: np.ndarray, mask_new: np.ndarray) -> dict:
    """
    Compare two class masks (same spatial extent).
    Returns change statistics and RGBA change overlay.
    """
    assert mask_old.shape == mask_new.shape, "Masks must be same shape"

    H, W  = mask_old.shape
    total = H * W

    # per-class areas
    def areas(mask):
        return {
            name: int((mask == i).sum())
            for i, name in enumerate(CLASS_NAMES)
        }

    old_areas = areas(mask_old)
    new_areas = areas(mask_new)

    delta_km2 = {
        name: round((new_areas[name] - old_areas[name]) * PX_TO_KM2, 4)
        for name in CLASS_NAMES
    }
    delta_pct = {
        name: round((new_areas[name] - old_areas[name]) / (old_areas[name] + 1e-6) * 100, 2)
        for name in CLASS_NAMES
    }

    # build RGBA change mask
    rgba = np.zeros((H, W, 4), dtype=np.uint8)

    # new buildings (was not building, now is)
    new_build = (mask_old != 2) & (mask_new == 2)
    rgba[new_build] = CHANGE_COLORS["new_buildings"]

    # lost trees (was tree, now is not)
    lost_tree = (mask_old == 1) & (mask_new != 1)
    rgba[lost_tree] = CHANGE_COLORS["lost_trees"]

    # new water (was not water, now is)
    new_water = (mask_old != 0) & (mask_new == 0)
    rgba[new_water] = CHANGE_COLORS["new_water"]

    # lost water (was water, now is not)
    lost_water = (mask_old == 0) & (mask_new != 0)
    rgba[lost_water] = CHANGE_COLORS["lost_water"]

    # alerts
    alerts = []
    if delta_pct["Buildings"] > 20:
        alerts.append(f"Rapid urbanization: buildings grew by {delta_pct['Buildings']:.1f}%")
    if delta_pct["Trees"] < -15:
        alerts.append(f"Deforestation warning: tree cover reduced by {abs(delta_pct['Trees']):.1f}%")
    if delta_pct["Water"] < -10:
        alerts.append(f"Water body reduction: {abs(delta_pct['Water']):.1f}% water loss")
    if not alerts:
        alerts.append("No critical environmental changes detected")

    return {
        "old_area_km2"  : {k: round(v * PX_TO_KM2, 4) for k, v in old_areas.items()},
        "new_area_km2"  : {k: round(v * PX_TO_KM2, 4) for k, v in new_areas.items()},
        "delta_km2"     : delta_km2,
        "delta_pct"     : delta_pct,
        "alerts"        : alerts,
        "change_rgba"   : rgba,
        "changed_pixels": int(((mask_old != mask_new)).sum()),
        "change_pct"    : round(float((mask_old != mask_new).sum()) / total * 100, 2),
    }
