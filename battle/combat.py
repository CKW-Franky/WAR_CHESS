"""Single exchange resolution: angle, armor, aura, volley, counter."""
import random

import equipment
from config import DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, DIRECTION_DELTAS
from battle.movement import engaged_count


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



def _unit_has_loadout(unit):
    """True when the unit carries an equipment loadout (the six archetypes)."""
    return (getattr(unit, "weapon", None) is not None
            and getattr(unit, "armor", None) is not None)




def is_ranged_attacker(unit):
    """True when the unit's active weapon actually shoots.

    Reach weapons (長槍/鎌勾槍, range 2) are **melee**, so ``attack_range > 1``
    is not a valid ranged test once the weapon range is applied.
    """
    if getattr(unit, "weapon", None) is not None:
        return bool(equipment.get_weapon(unit.weapon).ranged)
    return getattr(unit, "attack_range", 1) > 1



def _melee_armor(defender, angle):
    """Per-man armor against a melee hit: body + shield (never the rear)."""
    if _unit_has_loadout(defender):
        armor = float(defender.body_armor) + float(defender.shield_armor_vs(angle))
        return armor * float(getattr(defender, "armor_multiplier", 1.0))
    return (float(getattr(defender, "per_man_armor", 0))
            * float(getattr(defender, "armor_multiplier", 1.0)))



def aura_ranged_block(defender, game):
    """大盾方陣：the ally directly in front projects block onto this unit.

    Not stacked with the unit's own shield: the higher value wins, capped at
    :data:`equipment.SHIELD_BLOCK_CAP` (60%).
    """
    if game is None:
        return 0.0
    dx, dy = DIRECTION_DELTAS.get(getattr(defender, "facing", DIR_DOWN), (0, 1))
    ally = game.get_unit_at(defender.x + dx, defender.y + dy)
    if ally is None or ally is defender or ally.team != defender.team:
        return 0.0
    return float(getattr(ally, "aura_block_bonus", 0.0))



def _ranged_armor(defender, game=None):
    """Per-man body armor and shield block against a ranged hit.

    Two-handed weapons stow the shield, so ``ranged_block`` is 0 for archers,
    crossbowmen and horse archers.
    """
    if _unit_has_loadout(defender):
        block = float(defender.ranged_block)
        aura = aura_ranged_block(defender, game)
        if aura > block:
            block = aura
        return (float(defender.body_armor)
                * float(getattr(defender, "armor_multiplier", 1.0)),
                min(block, equipment.SHIELD_BLOCK_CAP))
    return (float(getattr(defender, "per_man_armor", 0))
            * float(getattr(defender, "armor_multiplier", 1.0)), 0.0)



def _attack_multiplier(attacker):
    """Tier atk multiplier x quality multiplier (applied to the three channels)."""
    if hasattr(attacker, "attack_channel_multiplier"):
        return float(attacker.attack_channel_multiplier)
    return (float(getattr(attacker, "tier_attack_mult", 1.0))
            * float(getattr(attacker, "quality_multiplier", 1.0)))



def _loadout_volley_damage(attacker, defender, game, dist, angle, is_ranged,
                           is_ranged_melee, arrow, mechanics, defender_mechanics,
                           momentum_mult, momentum_cap):
    """Full-strength volley damage under the per-man / three-channel model.

    ``equipment.per_hit_damage`` is the damage of *one* soldier's hit; the volley
    is the sum over the unit.  ``calculate_combat_result`` later scales it by the
    share of soldiers that actually hit, so the final damage is
    ``per_man_damage x hits``.
    """
    target_rattan = bool(getattr(defender, "is_rattan", False))
    fire_arrow = bool(getattr(attacker, "fire_arrow", False)) or arrow == "fire"
    attack_mult = _attack_multiplier(attacker)

    ignore_all_def = "armor_pierce_100" in mechanics
    armor_pierce_50 = "armor_pierce_50" in mechanics
    is_calibrated = getattr(attacker, "is_calibrated", False)

    if is_ranged and not is_ranged_melee:
        armor, block = _ranged_armor(defender, game)
    else:
        armor, block = _melee_armor(defender, angle), 0.0

    dt = game.terrain_map[defender.y][defender.x] if game is not None else "NORMAL"
    if dt == "HIGHLAND":
        armor *= 1.1            # legacy high-ground defense bonus, into armor

    # Campaign evolution features fold into the single per-man armor number.
    if ignore_all_def:
        armor = 0.0
    elif armor_pierce_50:
        armor *= 0.5
    elif is_calibrated:
        armor *= 0.25
    elif arrow == "armor_pierce":
        armor *= 0.6

    # 弩's 0.40 pierce factor (equipment.CROSSBOW_FACTOR) lives in
    # equipment.per_hit_damage via weapon.pierce_factor, so it is not repeated
    # here.  Fire arrows (pierce x0.70, x2 vs 藤甲 with armor ignored) are
    # handled there too.
    per_man = equipment.per_hit_damage(
        attacker.weapon, armor, quality=attack_mult,
        fire_arrow=fire_arrow, target_rattan=target_rattan)

    volley = per_man * engaged_count(attacker, game,
                                     is_ranged and not is_ranged_melee,
                                     defender)

    if block:
        volley *= (1.0 - block)
    if is_ranged_melee:
        # A ranged unit fighting at contact still uses its bow at 40% (legacy).
        volley *= 0.4
    if is_ranged and not is_ranged_melee:
        volley *= equipment.damage_multiplier(attacker.weapon, dist)

    if getattr(attacker, "is_rapid_salvo", False):
        volley *= 1.5
    if getattr(attacker, "is_cavalry", False) and getattr(attacker, "is_charging", False):
        volley += min(attacker.accumulated_momentum, momentum_cap) * momentum_mult

    if (angle == "REAR" and getattr(defender, "special", None) == "shield_wall"
            and "rear_immunity" not in defender_mechanics):
        volley *= 1.5

    if (is_ranged and not is_ranged_melee
            and getattr(attacker, "has_moved", False)
            and "skirmish_no_penalty" not in mechanics):
        if getattr(attacker, "special", None) == "move_shoot_discount":
            volley *= 0.75
        else:
            volley *= 0.5

    if dist > 1:
        if (getattr(defender, "special", None) == "shield_wall"
                and not is_calibrated and not ignore_all_def and angle != "REAR"):
            volley *= 0.65
        if dt == "FOREST" and not is_calibrated and not ignore_all_def:
            volley *= 0.5

    if is_ranged and dt == "RUINS":
        volley *= 0.7

    if angle == "FLANK":
        volley *= 1.25
    elif angle == "REAR":
        volley *= 1.5

    if (is_ranged and not is_ranged_melee
            and not getattr(attacker, "has_moved", False)
            and not attacker.is_cavalry):
        bonus = 30 if "stand_still_30" in mechanics else 15
        volley *= 1.0 + bonus / 100.0

    volley *= attacker.morale_damage_mult

    if "atk_vs_infantry_40" in mechanics and not getattr(defender, "is_cavalry", False):
        volley *= 1.4

    if ("charge_ranged_resist" in defender_mechanics
            and is_ranged
            and getattr(defender, "is_cavalry", False)
            and getattr(defender, "is_charging", False)):
        volley *= 0.6

    return max(0.0, volley)



def _counter_damage(attacker, defender, counter_mult, game=None):
    """Damage the defender deals back using its own weapon channels.

    Uses the defender's total per-man channels against the attacker's armor; a
    defender without a loadout keeps the legacy
    ``attack_power - defense`` exchange.
    """
    armor = _melee_armor(attacker, "FRONT")
    per_man = equipment.per_hit_damage(
        defender.weapon, armor,
        quality=_attack_multiplier(defender))
    raw = per_man * engaged_count(defender, game, False, attacker)
    raw *= defender.morale_damage_mult
    raw *= attacker.morale_taken_mult
    return int(max(50.0, raw) * counter_mult)



def strike_damage(attacker, defender, game, angle="FRONT", scale=1.0,
                  is_ranged=False):
    """Damage of a single special strike using the equipment channels.

    Shared by 破陣衝撞 / 槍陣攔截 / 機會攻擊 / 城門攻擊 so none of them keep
    the old ``attack_power - defense`` arithmetic.  Units without a loadout
    """
    if is_ranged:
        armor, block = _ranged_armor(defender, game)
    else:
        armor, block = _melee_armor(defender, angle), 0.0
    per_man = equipment.per_hit_damage(
        attacker.weapon, armor, quality=_attack_multiplier(attacker),
        fire_arrow=bool(getattr(attacker, "fire_arrow", False)),
        target_rattan=bool(getattr(defender, "is_rattan", False)))
    raw = per_man * engaged_count(attacker, game, is_ranged, defender)
    raw *= attacker.morale_damage_mult
    if block:
        raw *= (1.0 - block)
    raw *= defender.morale_taken_mult
    return max(1, int(raw * scale))



def calculate_combat_result(attacker, defender, game,
                            action_type="NORMAL", preview=False):
    dist = max(abs(attacker.x - defender.x), abs(attacker.y - defender.y))
    angle = get_attack_angle_type(attacker, defender)

    empty = {
        "predicted_damage": 0, "hit_chance": 0, "angle": angle,
        "can_counter": False, "penetrated": False, "kills": 0,
        "hits": 0, "misses": 0, "counter_mult": 0.5,
        "counter_damage": 0, "is_crit": False,
    }

    if not attacker.is_alive():
        return empty

    is_ranged = is_ranged_attacker(attacker)
    is_ranged_melee = is_ranged and dist == 1

    arrow = getattr(attacker, "archer_arrow", None)

    hit_chance = attacker.calculate_hit_chance(defender, game)

    if angle == "FLANK":
        hit_chance = min(100, hit_chance + 15)
    elif angle == "REAR":
        hit_chance = min(100, hit_chance + 30)

    mechanics = getattr(attacker, "evolution_mechanics", [])
    defender_mechanics = getattr(defender, "evolution_mechanics", [])

    momentum_mult = 400 if "charge_momentum_x2" in mechanics else 250
    momentum_cap = 9 if "charge_momentum_x2" in mechanics else 6

    if action_type == "PIERCE":
        base_dmg = int(_loadout_volley_damage(
            attacker, defender, game, dist, angle, False, False, None,
            mechanics, defender_mechanics, momentum_mult, momentum_cap))
        predicted = max(1, int(base_dmg * defender.morale_taken_mult))
        can_counter = (
            getattr(defender, "special", None) == "counter_cavalry"
            and getattr(attacker, "is_cavalry", False)
            and defender.ap >= 30
        )
        counter_damage = (
            _counter_damage(attacker, defender, 3.0, game) if can_counter else 0
        )
        return {
            "predicted_damage": predicted, "hit_chance": 100,
            "angle": angle, "can_counter": can_counter, "penetrated": False,
            "kills": simulate_kills(defender, predicted),
            "hits": attacker.current_soldiers, "misses": 0,
            "counter_mult": 3.0 if can_counter else 0.0,
            "counter_damage": counter_damage, "is_crit": False,
        }

    base_dmg = _loadout_volley_damage(
        attacker, defender, game, dist, angle, is_ranged, is_ranged_melee,
        arrow, mechanics, defender_mechanics, momentum_mult, momentum_cap)
    base_dmg = int(max(0.0, base_dmg))

    crit_chance = 5
    if angle == "REAR":
        crit_chance += 15

    if preview:
        base_dmg = int(base_dmg * (1.0 + crit_chance / 100 * 0.5))
        is_crit = False
    else:
        is_crit = (random.random() * 100) < crit_chance
        if is_crit:
            base_dmg = base_dmg * 3 // 2

    attacker_count = engaged_count(attacker, game,
                                   is_ranged and not is_ranged_melee, defender)
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
    if actual_damage:
        actual_damage = max(1, int(actual_damage * defender.morale_taken_mult))
    kills = simulate_kills(defender, actual_damage)

    can_counter = (
        dist == 1
        and angle != "REAR"
        and defender.ap >= 30
        and not getattr(attacker, "no_counter_this_attack", False)
    )
    if (getattr(defender, "special", None) == "counter_cavalry"
            and getattr(attacker, "is_cavalry", False)):
        counter_mult = 3.0
    else:
        counter_mult = 0.5

    if can_counter:
        counter_damage = _counter_damage(attacker, defender, counter_mult, game)
    else:
        counter_damage = 0

    return {
        "predicted_damage": actual_damage,
        "hit_chance": hit_chance,
        "angle": angle,
        "can_counter": can_counter,
        "penetrated": bool(getattr(attacker, "is_calibrated", False)
                           or "armor_pierce_100" in mechanics),
        "kills": kills,
        "hits": hits,
        "misses": misses,
        "counter_mult": counter_mult,
        "counter_damage": counter_damage,
        "is_crit": is_crit,
    }
