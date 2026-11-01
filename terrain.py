TERRAINS = ("NORMAL", "FOREST", "HIGHLAND", "RIVER", "BRIDGE", "MOUNTAIN")

MOVE_EXTRA = {
    "NORMAL": 0,
    "FOREST": 0,
    "HIGHLAND": 1,
    "RIVER": None,
    "BRIDGE": 0,
    "MOUNTAIN": 2,
}

FRONTAGE = {
    "NORMAL": 220,
    "FOREST": 70,
    "HIGHLAND": 180,
    "RIVER": 120,
    "BRIDGE": 220,
    "MOUNTAIN": 50,
}

BLOCKED = ()


def move_extra(terrain, is_cavalry=False):
    if terrain in BLOCKED:
        return None
    if terrain == "MOUNTAIN":
        if is_cavalry:
            return None
        return 2
    if terrain == "RIVER":
        return 1 if is_cavalry else 2
    if terrain == "HIGHLAND":
        return 1
    return 0


def is_passable(terrain, is_cavalry=False):
    return move_extra(terrain, is_cavalry) is not None


def frontage(terrain):
    return FRONTAGE.get(terrain, FRONTAGE["NORMAL"])


def effect_keys(terrain):
    """Translation keys for the hover tooltip. Keep in sync with battle/combat.py."""
    if terrain == "FOREST":
        return ["terrain_fx_forest"]
    if terrain == "HIGHLAND":
        return ["terrain_fx_highland"]
    if terrain == "RIVER":
        return ["terrain_fx_river"]
    if terrain == "BRIDGE":
        return ["terrain_fx_bridge"]
    if terrain == "MOUNTAIN":
        return ["terrain_fx_mountain"]
    return []
