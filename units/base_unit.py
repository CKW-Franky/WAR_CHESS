
from typing import NamedTuple

import equipment
from config import (DIR_DOWN, DIR_UP, DIRECTION_DELTAS,
                    GRID_WIDTH, GRID_HEIGHT)

CURVES = {
    "elite":    {"atk_floor": 40, "def_floor": 20},
    "balanced": {"atk_floor": 60, "def_floor": 50},
    "tank":     {"atk_floor": 60, "def_floor": 70},
    "glass":    {"atk_floor": 50, "def_floor": 0},
}

#: Legacy ``attack_power`` units per point of per-man, per-hit damage.
#: The pre-loadout game kept ``attack_power`` in the 900-3000 range while the
#: equipment model works with ~10-20 damage per soldier; deriving the legacy
#: number from the loadout channels at this scale keeps the secondary code
#: paths that still read ``attack_power`` (skills, opportunity attacks, gate
#: damage, UI readouts) in their familiar range.
ATTACK_SCALE_PER_CHANNEL = 100

#: Legacy ``defense`` units per point of per-man armor.  魚鱗甲 + 大盾 = 9
#: armor -> 450 defense, which is exactly the old 盾兵 value.
DEFENSE_SCALE_PER_ARMOR = 50


class Channels(NamedTuple):
    """Per-man attack channels, already scaled by tier multiplier and quality."""

    cut: float
    pierce: float
    blunt: float

    @property
    def total(self):
        return self.cut + self.pierce + self.blunt


class BaseUnit:
    def __init__(self, name, team, x, y, hp, attack, defense, range_, accuracy,
                 speed, max_mp, is_cavalry, special,
                 max_soldiers=500, hp_per_soldier=10,
                 curve="balanced"):
        self.name = name
        self.team = team
        self.x, self.y = x, y

        self.max_soldiers = max_soldiers
        self.hp_per_soldier = hp_per_soldier
        self.current_soldiers = max_soldiers
        self.soldier_hp = hp_per_soldier

        self.max_ap, self.ap = 100, 100
        self.max_mp, self.mp = max_mp, max_mp

        self.base_attack = attack
        self.base_defense = defense
        self.curve = curve
        self.base_accuracy = accuracy
        #: Constructor accuracy, kept so late buffs (e.g. archer_hit_bonus can be
        #: measured as a delta when the loadout supplies its own base accuracy.
        self._accuracy_baseline = accuracy
        self.attack_range = range_
        self.speed = speed

        self.max_morale = 100
        self.morale = 100

        self.facing = DIR_DOWN if team == "ai" else DIR_UP

        self.is_cavalry = is_cavalry
        self.special = special

        self.is_charging = False
        self.charge_locked_this_turn = False
        self.has_moved = False
        self.can_move = True
        self.accumulated_momentum = 0

        self.is_calibrated = False
        self.calibration_turns = 0
        self.no_counter_this_attack = False
        self.archer_arrow = None
        self.archer_longshot = False
        self.split_sibling = None
        self.is_temporary = False
        self.pike_wall_active = False
        self.guarded_by = None
        self.is_stunned = False
        self.is_rapid_salvo = False

        self.opportunity_attack_used = False
        self.skill_used_this_turn = False
        self.guarding_used_this_turn = False

        self.equip_attack_bonus = 0
        self.equip_defense_bonus = 0
        self.elite_attack_bonus = 0
        self.elite_defense_bonus = 0

        self.evolution_path = None
        self.evolution_star = 0
        self.evolution_mechanics = []

        # --- equipment loadout -------------------------------------------
        # All shipped units carry a loadout; the legacy no-loadout path is gone.
        self.tier = None            # tier id, e.g. "veteran" (老兵)
        self.weapons = ()           # (main_weapon_id, sub_weapon_id)
        self.weapon = None          # active weapon id == weapons[active_slot]
        self.active_slot = 0        # 0 = main, 1 = sub
        self.shield = None          # shield id or None
        self.armor = None           # body armor id or None
        self.mount = None           # horse id or None
        self.quality = "refined"    # quality id / name / raw multiplier
        self.fire_arrow = False     # 火矢 toggle (short bow / long bow)
        self.loaded = True          # crossbow reload state
        self.follow_up_used = False
        self.loadout_issues = ()    # requirement problems reported by build_stats
        self._build = {}
        self._channels = None
        self._loadout_base_attack = 0   # pure loadout-derived values
        self._loadout_base_defense = 0

    # ------------------------------------------------------------------
    # Health / soldier bookkeeping (unchanged compatibility properties)
    # ------------------------------------------------------------------
    @property
    def max_hp(self):
        return self.max_soldiers * self.hp_per_soldier

    @property
    def hp(self):
        if self.current_soldiers <= 0:
            return 0
        return (self.current_soldiers - 1) * self.hp_per_soldier + self.soldier_hp

    @property
    def soldier_ratio(self):
        return self.current_soldiers / self.max_soldiers

    @property
    def morale_damage_mult(self):
        """100 = +20% outgoing damage; 50 = no bonus; below 50 = no bonus."""
        if self.morale <= 50:
            return 1.0
        return 1.0 + 0.20 * (self.morale - 50) / 50.0

    @property
    def morale_taken_mult(self):
        """50 = no penalty; 0 = +50% incoming damage."""
        if self.morale >= 50:
            return 1.0
        return 1.0 + 0.50 * (50 - self.morale) / 50.0

    @property
    def attack_power(self):
        if self.current_soldiers <= 0:
            return 1
        ratio = self.current_soldiers / self.max_soldiers
        floor = CURVES.get(self.curve, CURVES["balanced"])["atk_floor"]
        pct = floor + int((100 - floor) * ratio)
        result = self.base_attack * pct // 100
        result += self.equip_attack_bonus + self.elite_attack_bonus
        if "atk_flat_400" in self.evolution_mechanics:
            result += 400
        return max(1, result)

    @property
    def defense(self):
        if self.base_defense == 0:
            result = 0
        else:
            ratio = self.current_soldiers / self.max_soldiers
            floor = CURVES.get(self.curve, CURVES["balanced"])["def_floor"]
            pct = floor + int((100 - floor) * ratio)
            result = max(1, self.base_defense * pct // 100)
        result += self.equip_defense_bonus + self.elite_defense_bonus
        if "def_flat_400" in self.evolution_mechanics:
            result += 400
        if "def_flat_500" in self.evolution_mechanics:
            result += 500
        return result

    # ------------------------------------------------------------------
    # Equipment loadout (per-man / three-channel model)
    # ------------------------------------------------------------------
    @property
    def has_loadout(self):
        """True when this unit carries an equipment loadout."""
        return self.weapon is not None and self.armor is not None

    @property
    def per_man_hp(self):
        """HP of a single soldier (the unit's existing hp_per_soldier)."""
        return self.hp_per_soldier

    @property
    def total_hp(self):
        return self.max_soldiers * self.per_man_hp

    @property
    def body_armor(self):
        if self.armor is None:
            return 0
        return equipment.get_armor(self.armor).armor

    @property
    def shield_armor(self):
        """Shield melee armor in the current stance (front)."""
        return self.shield_armor_vs("FRONT")

    def shield_armor_vs(self, angle):
        """Shield melee armor for an incoming attack angle (rear = 0)."""
        if self.shield is None or self.weapon is None:
            return 0
        return equipment.shield_melee_armor(
            self.shield, equipment.get_weapon(self.weapon).hand, angle)

    @property
    def per_man_armor(self):
        """Effective melee armor per soldier (front) under the current loadout."""
        if self.has_loadout:
            return self.body_armor + self.shield_armor
        return max(0, int(self.base_defense // DEFENSE_SCALE_PER_ARMOR))

    @property
    def aura_block_bonus(self):
        """Ranged block this unit projects onto the ally directly behind it."""
        if not self.has_loadout:
            return 0.0
        return float(self._build.get("aura_block", 0.0))

    @property
    def can_fire(self):
        """False for an unloaded crossbow."""
        weapon = self.active_weapon
        if weapon is None or not weapon.reload_required:
            return True
        return bool(self.loaded)

    @property
    def ranged_block(self):
        """Ranged block fraction; 0 while a two-handed weapon stows the shield."""
        if not self.has_loadout or self.shield is None:
            return 0.0
        if equipment.get_weapon(self.weapon).is_two_handed:
            return 0.0
        return equipment.shield_ranged_block(self.shield)

    @property
    def is_rattan(self):
        """True when the body armor is 藤甲 (fire arrows x2, armor ignored)."""
        if not self.armor:
            return False
        return bool(equipment.get_armor(self.armor).fire_vulnerable)

    @property
    def channels(self):
        """Per-man cut / pierce / blunt channels.

        Units without a loadout fall back to a single cut channel carrying the
        legacy attack value, so the property never raises.
        """
        if self._channels is not None:
            return self._channels
        return Channels(
            max(0.0, self.base_attack / float(ATTACK_SCALE_PER_CHANNEL)), 0.0, 0.0)

    @property
    def tier_attack_mult(self):
        if self.tier is None:
            return 1.0
        return equipment.get_tier(self.tier).attack_mult

    @property
    def quality_multiplier(self):
        try:
            return equipment.quality_multiplier(self.quality)
        except (KeyError, TypeError, ValueError):
            return 1.0

    @property
    def attack_channel_multiplier(self):
        """Multiplier applied to the per-man channels in the damage model.

        Tier x quality, plus any legacy attack bonus that was folded into
        ``base_attack`` after the loadout was applied.
        upgrades, war temple buffs, AI difficulty scaling).  Keeping the ratio
        against the pure loadout value means those systems keep mattering.
        """
        tier_quality = self.tier_attack_mult * self.quality_multiplier
        baseline = self._loadout_base_attack
        if baseline <= 0:
            return tier_quality
        bonus = self.equip_attack_bonus + self.elite_attack_bonus
        if "atk_flat_400" in self.evolution_mechanics:
            bonus += 400
        total = max(1.0, self.base_attack + bonus)
        return tier_quality * total / baseline

    @property
    def armor_multiplier(self):
        """Multiplier applied to the per-man armor (legacy defense bonuses)."""
        baseline = self._loadout_base_defense
        if baseline <= 0:
            return 1.0
        bonus = self.equip_defense_bonus + self.elite_defense_bonus
        if "def_flat_400" in self.evolution_mechanics:
            bonus += 400
        if "def_flat_500" in self.evolution_mechanics:
            bonus += 500
        return max(0.0, (self.base_defense + bonus) / baseline)

    @property
    def loadout_accuracy(self):
        """Hit chance of the current loadout inside its free range."""
        if not self.has_loadout:
            return self.base_accuracy
        weapon = equipment.get_weapon(self.weapon)
        tier = equipment.get_tier(self.tier) if self.tier is not None else None
        base = tier.accuracy if tier is not None else self.base_accuracy
        return equipment.hit_chance(base, weapon, weapon.free_range,
                                    shield=self.shield,
                                    mounted=self.is_cavalry, tier=tier)

    @property
    def loadout_melee_accuracy(self):
        """Melee hit chance from the loadout (tier + weapon + shield + mount)."""
        if not self.has_loadout:
            return self.base_accuracy
        base = int(self._build.get("melee_accuracy", self.base_accuracy))
        return base + (self.base_accuracy - self._accuracy_baseline)

    @property
    def is_ranged_weapon(self):
        """True when the active weapon fires; reach weapons (range 2) are melee."""
        if self.weapon is None:
            return self.attack_range > 1
        return bool(equipment.get_weapon(self.weapon).ranged)

    @property
    def active_weapon(self):
        """Resolved :class:`equipment.Weapon` of the active slot (or None)."""
        if self.weapon is None:
            return None
        return equipment.get_weapon(self.weapon)

    def apply_loadout(self, tier, weapon, weapon2=None, shield=None, armor=None,
                      mount=None, quality="refined", active_slot=0):
        """Attach a loadout and derive the legacy stat block from it.

        ``weapon`` / ``weapon2`` are the main / sub weapon slots (v2 dual weapon).
        Everything accepts an object, an ASCII id or a Chinese name.
        """
        self.tier = equipment.get_tier(tier).id

        weapon_ids = []
        for entry in (weapon, weapon2):
            if entry is not None:
                weapon_ids.append(equipment.get_weapon(entry).id)
        self.weapons = tuple(weapon_ids)
        if self.weapons:
            self.active_slot = max(0, min(int(active_slot), len(self.weapons) - 1))
            self.weapon = self.weapons[self.active_slot]
        else:
            self.active_slot = 0
            self.weapon = None

        self.shield = equipment.get_shield(shield).id if shield is not None else None
        self.armor = equipment.get_armor(armor).id if armor is not None else None
        self.mount = equipment.get_horse(mount).id if mount is not None else None
        try:
            self.quality = equipment.resolve_quality(quality).id
        except (KeyError, TypeError):
            self.quality = quality

        self.refresh_loadout()
        return self

    def loadout_summary(self):
        """The complete fixed set: weapon, shield, armor and mount."""
        try:
            weapon = (equipment.get_weapon(self.weapons[0]).name
                      if self.weapons else "無")
            shield = equipment.get_shield(self.shield).name if self.shield else "無盾"
            armor = equipment.get_armor(self.armor).name if self.armor else "無甲"
            mount = equipment.get_horse(self.mount).name if self.mount else "無馬"
        except (KeyError, TypeError, IndexError):
            return ""
        return f"武器：{weapon}  盾：{shield}  甲：{armor}  馬：{mount}"

    def refresh_loadout(self):
        """Recompute channels / legacy stats from the current loadout."""
        if not self.has_loadout:
            self._build = {}
            self._channels = None
            return
        try:
            build = equipment.build_stats(self.tier, self.weapon, self.shield,
                                          self.armor, self.mount, self.quality)
        except (KeyError, TypeError, ValueError):
            build = {}
        self._build = build
        self.loadout_issues = tuple(build.get("issues", ()))

        mult = self.tier_attack_mult
        self._channels = Channels(
            build.get("attack_cut", 0.0) * mult,
            build.get("attack_pierce", 0.0) * mult,
            build.get("attack_blunt", 0.0) * mult,
        )
        self.base_attack = int(round(self._channels.total * ATTACK_SCALE_PER_CHANNEL))
        self.base_defense = int(round(self.per_man_armor * DEFENSE_SCALE_PER_ARMOR))
        self._loadout_base_attack = self.base_attack
        self._loadout_base_defense = self.base_defense

        # Per-man HP comes from the tier (民兵12 / 新兵15 / 老兵18 / 精銳21 / 親衛24).
        # max_soldiers stays as constructed.
        tier_obj = equipment.get_tier(self.tier)
        self.hp_per_soldier = int(tier_obj.hp_per_soldier)
        if self.current_soldiers >= self.max_soldiers:
            self.soldier_hp = self.hp_per_soldier
        elif self.soldier_hp > self.hp_per_soldier:
            self.soldier_hp = self.hp_per_soldier

        # Reach follows the active weapon (長槍2 / 長弓6 / 短弓4 / 弩5 / 標槍3).
        self.attack_range = int(build.get("range", self.attack_range))

    # ------------------------------------------------------------------
    # Turn / hit resolution
    # ------------------------------------------------------------------
    def set_facing(self, direction):
        if direction in (0, 1, 2, 3):
            self.facing = direction

    def reset_turn(self):
        self.ap = self.max_ap
        self.mp = self.max_mp
        if self.is_stunned:
            self.ap = max(20, self.ap - 30)
            self.mp = max(1, self.mp - 1)
            self.is_stunned = False

        self.has_moved = False
        self.can_move = True
        self.charge_locked_this_turn = False
        self.pike_wall_active = False
        self.guarded_by = None
        self.is_rapid_salvo = False
        self.opportunity_attack_used = False
        self.skill_used_this_turn = False
        self.guarding_used_this_turn = False
        self.follow_up_used = False
        self.archer_longshot = False

    def is_alive(self):
        return self.current_soldiers > 0

    def can_split(self):
        return self.current_soldiers >= 200 and self.ap >= 30

    def can_merge_with(self, other):
        return (self.name == other.name
                and self.team == other.team
                and max(abs(self.x - other.x), abs(self.y - other.y)) == 1
                and self.current_soldiers + other.current_soldiers <= self.max_soldiers)

    def get_actual_range(self, game):
        bonus = 0
        if self.is_calibrated:
            bonus += 1
        if "range_plus_1" in self.evolution_mechanics:
            bonus += 1
        if getattr(self, "archer_longshot", False):
            bonus += 1
        if game is not None and self.is_ranged_weapon \
                and game.terrain_map[self.y][self.x] in ("MOUNTAIN", "HIGHLAND"):
            bonus += 1
        return self.attack_range + bonus

    def get_minimum_range(self):
        return 0

    def calculate_hit_chance(self, defender, game):
        dist = max(abs(self.x - defender.x), abs(self.y - defender.y))
        if dist <= 1:
            return self._melee_hit_chance(defender, game)

        # Ranged shots use the equipment free-range formula; units without a
        # loadout keep the legacy (distance - 1) * 15 penalty.
        if self.has_loadout:
            hit = self._loadout_ranged_hit_chance(dist)
        else:
            hit = self.base_accuracy - (dist - 1) * 15

        if self.is_calibrated or self.is_rapid_salvo:
            hit += 20
        if "accuracy_plus_15" in self.evolution_mechanics:
            hit += 15

        at = game.terrain_map[self.y][self.x]
        dt = game.terrain_map[defender.y][defender.x]
        if at in ("MOUNTAIN", "HIGHLAND"):
            hit += 15
        if dt == "FOREST":
            hit -= 20
        if dt == "RIVER":
            hit += 20
        if defender.is_cavalry and defender.is_charging:
            hit -= 20
        if self.is_cavalry and self.is_charging:
            hit -= 20
        return max(15, min(95, hit))

    def _loadout_ranged_hit_chance(self, dist):
        """Base hit chance of the active weapon, without situational modifiers."""
        weapon = equipment.get_weapon(self.weapon)
        tier = equipment.get_tier(self.tier) if self.tier is not None else None
        base = tier.accuracy if tier is not None else self.base_accuracy
        # Late accuracy buffs (e.g. war temple archer_hit_bonus) are measured as
        # a delta against the constructor value so they still apply here.
        base += self.base_accuracy - self._accuracy_baseline
        return equipment.hit_chance(base, weapon, dist, shield=self.shield,
                                    mounted=self.is_cavalry, tier=tier)

    def _melee_hit_chance(self, defender, game):
        hit = self.loadout_melee_accuracy if self.has_loadout else 90
        if game is not None and game.terrain_map[defender.y][defender.x] == "FOREST":
            hit -= 10
        if getattr(defender, "is_cavalry", False) and getattr(defender, "is_charging", False):
            hit -= 15
        return max(50, min(100, hit))

    def take_damage(self, damage, attacker, game):
        final = max(1, int(damage))
        kills = 0
        remaining = final
        while remaining > 0 and self.current_soldiers > 0:
            if remaining >= self.soldier_hp:
                remaining -= self.soldier_hp
                self.current_soldiers -= 1
                kills += 1
                self.soldier_hp = self.hp_per_soldier
            else:
                self.soldier_hp -= remaining
                remaining = 0

        damage_ratio = final / max(1, self.max_hp)
        kills_ratio = kills / max(1, self.max_soldiers)
        loss = int(40 * damage_ratio + 60 * kills_ratio)
        self.morale = max(0, self.morale - loss)
        return final, kills

    @property
    def weapon_skill(self):
        weapon = self.active_weapon
        return equipment.get_skill(weapon.skill_id) if weapon is not None else None

    @property
    def weapon_extra_skill(self):
        weapon = self.active_weapon
        if weapon is None or not weapon.extra_skill_id:
            return None
        return equipment.get_skill(weapon.extra_skill_id)

    @property
    def skill_name(self):
        skill = self.weapon_skill
        return skill.name if skill is not None else ""

    @property
    def skill_cost(self):
        skill = self.weapon_skill
        return skill.ap_cost if skill is not None else 0

    @property
    def skill_desc(self):
        skill = self.weapon_skill
        return skill.description if skill is not None else ""

    def get_skill_targets(self, game):
        skill = self.weapon_skill
        if skill is None:
            return set()
        if skill.id == "guard":
            return {(u.x, u.y) for u in game.units
                    if u.is_alive() and u.team == self.team and u is not self
                    and u.name != "盾兵"
                    and max(abs(u.x - self.x), abs(u.y - self.y)) <= 1}
        if skill.id == "break_charge":
            return {(u.x, u.y) for u in game.units
                    if u.is_alive() and u.team != self.team
                    and max(abs(u.x - self.x), abs(u.y - self.y)) <= 1}
        return set()

    def toggle_arrow(self):
        if self.archer_arrow == "armor_pierce":
            self.archer_arrow = "fire"
            self.fire_arrow = True
        else:
            self.archer_arrow = "armor_pierce"
            self.fire_arrow = False
        return self.archer_arrow

    def execute_skill(self, game, target_tile=None):
        skill = self.weapon_skill
        if skill is None:
            return False

        if skill.id == "guard":
            if self.guarding_used_this_turn:
                game.add_damage_popup("每回合只能援護一次", self.x, self.y,
                                      is_miss=True)
                return False
            if not target_tile:
                targets = self.get_skill_targets(game)
                if not targets:
                    game.add_damage_popup("沒有可援護的友軍", self.x, self.y,
                                          is_miss=True)
                    return False
                target_tile = next(iter(targets))
            target = game.get_unit_at(*target_tile)
            if target is None:
                return False
            target.guarded_by = self
            self.guarding_used_this_turn = True
            game.add_damage_popup("盾牆已架設!", target.x, target.y,
                                  is_crit=True)
            game.trigger_visual_arrow((self.x, self.y), target_tile,
                                      is_skill=True)
            return True

        if skill.id == "break_charge":
            if not target_tile:
                targets = self.get_skill_targets(game)
                if not targets:
                    return False
                target_tile = next(iter(targets))
            tx, ty = target_tile
            target = game.get_unit_at(tx, ty)
            if target is None or target.team == self.team:
                return False
            dx, dy = tx - self.x, ty - self.y
            kb_x, kb_y = tx + dx, ty + dy
            occupied = {(u.x, u.y) for u in game.units if u.is_alive()}
            blocked = (
                not (0 <= kb_x < GRID_WIDTH and 0 <= kb_y < GRID_HEIGHT)
                or (kb_x, kb_y) in occupied
                or game.terrain_map[kb_y][kb_x] in ("MOUNTAIN", "RIVER")
            )
            momentum_mult = 400 if "charge_momentum_x2" in self.evolution_mechanics else 250
            momentum_cap = 9 if "charge_momentum_x2" in self.evolution_mechanics else 6
            mom = min(self.accumulated_momentum, momentum_cap)
            dmg = game.skill_strike(self, target) + mom * momentum_mult
            if blocked:
                dmg += 300
                target.is_stunned = True
            else:
                target.x, target.y = kb_x, kb_y
            _, kills = target.take_damage(dmg, self, game)
            label = "暈眩! 擊殺" if blocked else "擊退! 擊殺"
            game.add_damage_popup(f"{label} {kills}", tx, ty, is_crit=True)
            game.trigger_visual_arrow((self.x, self.y), target_tile,
                                      is_skill=True)
            return True

        if skill.id == "pike_wall":
            self.pike_wall_active = True
            game.add_damage_popup("槍陣已架設!", self.x, self.y, is_crit=True)
            return True
        if skill.id == "rapid_fire":
            self.is_rapid_salvo = True
            game.add_damage_popup("連射準備!", self.x, self.y, is_crit=True)
            return True
        if skill.id == "calibration":
            self.is_calibrated = True
            self.no_counter_this_attack = True
            self.calibration_turns = (
                2 if "double_calibration" in self.evolution_mechanics else 1)
            game.add_damage_popup("校準完畢!", self.x, self.y, is_crit=True)
            return True
        if skill.id == "fire_arrow":
            mode = self.toggle_arrow()
            label = "火矢" if mode == "fire" else "穿甲箭"
            game.add_damage_popup(f"換矢: {label}!", self.x, self.y,
                                  is_crit=True)
            return True
        return False

    def execute_extra_skill(self, game, target_tile=None):
        skill = self.weapon_extra_skill
        if skill is None:
            return False
        if skill.id == "reload":
            return game.reload_crossbow(self)
        if skill.id == "long_shot":
            if self.archer_longshot:
                game.add_damage_popup("本回合已開遠射", self.x, self.y,
                                      is_miss=True)
                return False
            if self.ap < skill.ap_cost:
                game.add_damage_popup("AP 不足", self.x, self.y, is_miss=True)
                return False
            self.ap -= skill.ap_cost
            self.archer_longshot = True
            game.add_damage_popup("遠射：射程 +1", self.x, self.y,
                                  is_crit=True)
            return True
        return False
