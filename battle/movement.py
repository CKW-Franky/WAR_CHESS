"""Zones of control, frontage and engaged-strength rules."""
import terrain


ZOC_UNIT_NAMES = ("長槍兵", "盾兵")



def get_zoc_tiles(units, current_team, gw, gh):
    zoc = set()
    for u in units:
        if not u.is_alive() or u.team == current_team:
            continue
        reach_melee = (not getattr(u, "is_ranged_weapon", False)
                       and getattr(u, "attack_range", 1) >= 2)
        if getattr(u, "name", "") not in ZOC_UNIT_NAMES and not reach_melee:
            continue
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            zx, zy = u.x + dx, u.y + dy
            if 0 <= zx < gw and 0 <= zy < gh:
                zoc.add((zx, zy))
    return zoc


#: Soldiers that can bring a ranged weapon to bear at once (design v2 §1).
RANGED_CAP = 150



def engaged_count(unit, game, is_ranged=False, opponent=None):
    """How many soldiers actually get to strike in one exchange.

    Melee is capped by the narrower of the two contact tiles (the attacker's
    tile and the defender's tile), so attacking into a forest from open ground
    still only brings the forest's frontage to bear.  Ranged fire uses
    :data:`RANGED_CAP`.  Every consumer (volley, counter, preview, AI) goes
    through this helper so the numbers always agree.
    """
    soldiers = max(1, unit.current_soldiers)
    if is_ranged:
        return min(soldiers, RANGED_CAP)
    if game is None:
        return soldiers
    own = terrain.frontage(game.terrain_map[unit.y][unit.x])
    if opponent is None:
        return min(soldiers, own)
    other = terrain.frontage(game.terrain_map[opponent.y][opponent.x])
    return min(soldiers, own, other)

