import random

DIR_UP = 0
DIR_RIGHT = 1
DIR_DOWN = 2
DIR_LEFT = 3

DIRECTION_DELTAS = {
    DIR_UP: (0, -1),
    DIR_RIGHT: (1, 0),
    DIR_DOWN: (0, 1),
    DIR_LEFT: (-1, 0),
}

DEFENSE_K = 800.0


def get_attack_angle_type(attacker, defender):
    dx = attacker.x - defender.x
    dy = attacker.y - defender.y
    if abs(dx) > abs(dy):
        rel = DIR_LEFT if dx > 0 else DIR_RIGHT
    else:
        rel = DIR_UP if dy > 0 else DIR_DOWN
    facing = getattr(defender, "facing", DIR_DOWN)
    if rel == facing:
        return "REAR"
    if (rel + 2) % 4 == facing:
        return "FRONT"
    return "FLANK"


def check_line_of_sight(p1_x, p1_y, p2_x, p2_y, terrain_map):
    steps = max(abs(p1_x - p2_x), abs(p1_y - p2_y))
    if steps <= 1:
        return True
    for i in range(1, steps):
        ratio = i / steps
        cx = round(p1_x + (p2_x - p1_x) * ratio)
        cy = round(p1_y + (p2_y - p1_y) * ratio)
        if (cx, cy) in ((p1_x, p1_y), (p2_x, p2_y)):
            continue
        if terrain_map[cy][cx] in ("MOUNTAIN", "FOREST"):
            return False
    return True


ZOC_UNIT_NAMES = ("長槍兵", "盾兵")


def get_zoc_tiles(units, current_team, gw, gh):
    zoc = set()
    for u in units:
        if not u.is_alive() or u.team == current_team:
            continue
        if getattr(u, "name", "") not in ZOC_UNIT_NAMES:
            continue
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            zx, zy = u.x + dx, u.y + dy
            if 0 <= zx < gw and 0 <= zy < gh:
                zoc.add((zx, zy))
    return zoc


def simulate_kills(defender, damage):
    kills = 0
    remaining = damage
    sim_soldiers = defender.current_soldiers
    sim_hp = defender.soldier_hp
    while remaining > 0 and sim_soldiers > 0:
        if remaining >= sim_hp:
            remaining -= sim_hp
            sim_soldiers -= 1
            kills += 1
            sim_hp = defender.hp_per_soldier
        else:
            break
    return kills


def get_morale_status(morale):
    if morale >= 80:
        return "HIGH"
    if morale >= 50:
        return "STABLE"
    if morale >= 25:
        return "SHAKEN"
    if morale > 0:
        return "BREAKING"
    return "ROUTING"


def calculate_combat_result(attacker, defender, game,
                            action_type="NORMAL", preview=False):
    dist = max(abs(attacker.x - defender.x), abs(attacker.y - defender.y))
    angle = get_attack_angle_type(attacker, defender)

    empty = {
        "predicted_damage": 0, "hit_chance": 0, "angle": angle,
        "can_counter": False, "penetrated": False, "kills": 0,
        "hits": 0, "misses": 0, "counter_mult": 0.5, "is_crit": False,
    }

    if getattr(attacker, "is_routing", False) or attacker.morale <= 0:
        return empty

    is_ranged = attacker.attack_range > 1
    is_ranged_melee = is_ranged and dist == 1

    arrow = getattr(attacker, "archer_arrow", None)

    hit_chance = attacker.calculate_hit_chance(defender, game)
    if getattr(attacker, "is_general", False):
        hit_chance += attacker.general_bonuses.get("hit_bonus", 0)

    if angle == "FLANK":
        hit_chance = min(100, hit_chance + 15)
    elif angle == "REAR":
        hit_chance = min(100, hit_chance + 30)

    if attacker.morale >= 80:
        hit_chance = min(100, hit_chance + 10)
    elif attacker.morale < 50:
        hit_chance = max(5, hit_chance - 15)

    if arrow == "longshot":
        hit_chance = min(100, hit_chance + 10)

    mechanics = getattr(attacker, "evolution_mechanics", [])
    defender_mechanics = getattr(defender, "evolution_mechanics", [])

    momentum_mult = 400 if "charge_momentum_x2" in mechanics else 250
    momentum_cap = 9 if "charge_momentum_x2" in mechanics else 6

    dt = game.terrain_map[defender.y][defender.x]
    def_mult = 1.0
    if dt == "SWAMP":
        def_mult = 0.8
    elif dt == "VILLAGE":
        def_mult = 1.2
    elif dt == "HIGHLAND":
        def_mult = 1.1
    eff_defense = int(defender.defense * def_mult)

    if action_type == "PIERCE":
        mom = min(attacker.accumulated_momentum, momentum_cap)
        base_dmg = (attacker.attack_power - eff_defense + mom * momentum_mult)
        if angle == "REAR":
            base_dmg = base_dmg * 3 // 2
        elif angle == "FLANK":
            base_dmg = base_dmg * 5 // 4
        predicted = max(1, base_dmg)
        can_counter = (
            getattr(defender, "special", None) == "counter_cavalry"
            and getattr(attacker, "is_cavalry", False)
            and defender.morale > 30
            and not getattr(defender, "is_routing", False)
            and defender.ap >= 30
        )
        counter_damage = (
            int(max(50, defender.attack_power - attacker.defense) * 3.0)
            if can_counter else 0
        )
        return {
            "predicted_damage": predicted, "hit_chance": 100,
            "angle": angle, "can_counter": can_counter, "penetrated": False,
            "kills": simulate_kills(defender, predicted),
            "hits": attacker.current_soldiers, "misses": 0,
            "counter_mult": 3.0 if can_counter else 0.0,
            "counter_damage": counter_damage, "is_crit": False,
        }

    if is_ranged_melee:
        raw_dmg = attacker.attack_power * 4 // 10
    else:
        raw_dmg = attacker.attack_power

    if getattr(attacker, "is_rapid_salvo", False):
        raw_dmg = raw_dmg * 3 // 2
    if getattr(attacker, "is_cavalry", False) and getattr(attacker, "is_charging", False):
        raw_dmg += min(attacker.accumulated_momentum, momentum_cap) * momentum_mult

    if (angle == "REAR" and getattr(defender, "special", None) == "shield_wall"
            and "rear_immunity" not in defender_mechanics):
        raw_dmg = raw_dmg * 3 // 2

    is_calibrated = getattr(attacker, "is_calibrated", False)
    ignore_all_def = "armor_pierce_100" in mechanics
    armor_pierce_50 = "armor_pierce_50" in mechanics
    if ignore_all_def:
        used_defense = 0
    elif armor_pierce_50:
        used_defense = eff_defense // 2
    elif is_calibrated:
        used_defense = eff_defense // 4
    elif getattr(attacker, "name", "") == "弩手":
        used_defense = eff_defense * 3 // 4
    elif arrow == "armor_pierce":
        used_defense = eff_defense * 3 // 5
    else:
        used_defense = eff_defense

    defense_reduction = used_defense / (used_defense + DEFENSE_K)
    base_dmg = int(raw_dmg * (1.0 - defense_reduction))

    if not is_ranged_melee:
        if is_ranged and getattr(attacker, "has_moved", False) \
                and "skirmish_no_penalty" not in mechanics:
            if getattr(attacker, "special", None) == "move_shoot_discount":
                base_dmg = base_dmg * 3 // 4
            else:
                base_dmg = base_dmg // 2
        if is_ranged and dist > 1:
            dist_penalty = min((dist - 1) * 20, 80)
            base_dmg = base_dmg * (100 - dist_penalty) // 100

    if dist > 1:
        if (getattr(defender, "special", None) == "shield_wall"
                and not is_calibrated and not ignore_all_def
                and angle != "REAR"):
            base_dmg = base_dmg * 65 // 100
        if (game.terrain_map[defender.y][defender.x] == "FOREST"
                and not is_calibrated and not ignore_all_def):
            base_dmg = base_dmg // 2

    if is_ranged and game.terrain_map[defender.y][defender.x] == "RUINS":
        base_dmg = base_dmg * 7 // 10

    if angle == "FLANK":
        base_dmg = base_dmg * 5 // 4
    elif angle == "REAR":
        base_dmg = base_dmg * 3 // 2

    if attacker.morale >= 80:
        base_dmg = base_dmg * 11 // 10
    elif attacker.morale < 50:
        base_dmg = base_dmg * 9 // 10

    if getattr(attacker, "is_general", False):
        base_dmg = int(base_dmg * attacker.general_bonuses.get("damage_mult", 1.0))

    if (is_ranged and not is_ranged_melee
            and not getattr(attacker, "has_moved", False)
            and not attacker.is_cavalry):
        bonus = 30 if "stand_still_30" in mechanics else 15
        base_dmg = base_dmg * (100 + bonus) // 100

    if arrow == "fire":
        base_dmg = base_dmg * 6 // 5

    if "atk_vs_infantry_40" in mechanics and not getattr(defender, "is_cavalry", False):
        base_dmg = base_dmg * 14 // 10

    if ("charge_ranged_resist" in defender_mechanics
            and is_ranged
            and getattr(defender, "is_cavalry", False)
            and getattr(defender, "is_charging", False)):
        base_dmg = base_dmg * 6 // 10

    base_dmg = max(0, base_dmg)

    crit_chance = 5
    if getattr(attacker, "is_general", False):
        crit_chance += attacker.general_bonuses.get("crit_bonus", 0)
    if angle == "REAR":
        crit_chance += 15
    if attacker.morale >= 80:
        crit_chance += 10

    if preview:
        base_dmg = int(base_dmg * (1.0 + crit_chance / 100 * 0.5))
        is_crit = False
    else:
        is_crit = (random.random() * 100) < crit_chance
        if is_crit:
            base_dmg = base_dmg * 3 // 2

    attacker_count = attacker.current_soldiers
    if attacker_count > 0:
        expected_hits = (attacker_count * hit_chance) // 100
        variance = max(1, attacker_count // 10)
        if preview:
            hits = expected_hits
        else:
            hits = expected_hits + random.randint(-variance, variance)
        hits = max(0, min(attacker_count, hits))
        misses = attacker_count - hits
        actual_damage = (base_dmg * hits) // attacker_count
    else:
        hits = 0
        misses = 0
        actual_damage = 0

    actual_damage = max(1, actual_damage) if hits > 0 else 0
    kills = simulate_kills(defender, actual_damage)

    can_counter = (
        dist == 1
        and angle != "REAR"
        and defender.morale > 30
        and not getattr(defender, "is_routing", False)
        and defender.ap >= 30
        and not getattr(attacker, "no_counter_this_attack", False)
    )
    if (getattr(defender, "special", None) == "counter_cavalry"
            and getattr(attacker, "is_cavalry", False)):
        counter_mult = 3.0
    else:
        counter_mult = 0.5

    if can_counter:
        counter_damage = int(max(50, defender.attack_power - attacker.defense) * counter_mult)
    else:
        counter_damage = 0

    if getattr(attacker, "archer_arrow", None) and not preview:
        attacker.archer_arrow = None

    return {
        "predicted_damage": actual_damage,
        "hit_chance": hit_chance,
        "angle": angle,
        "can_counter": can_counter,
        "penetrated": is_calibrated or ignore_all_def,
        "kills": kills,
        "hits": hits,
        "misses": misses,
        "counter_mult": counter_mult,
        "counter_damage": counter_damage,
        "is_crit": is_crit,
    }