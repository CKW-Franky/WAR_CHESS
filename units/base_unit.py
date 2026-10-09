
from combat import DIR_DOWN, DIR_UP

CURVES = {
    "elite":    {"atk_floor": 40, "def_floor": 20},
    "balanced": {"atk_floor": 60, "def_floor": 50},
    "tank":     {"atk_floor": 60, "def_floor": 70},
    "glass":    {"atk_floor": 50, "def_floor": 0},
}


class BaseUnit:
    def __init__(self, name, team, x, y, hp, attack, defense, range_, accuracy,
                 speed, max_mp, is_cavalry, special, skill_name, skill_cost,
                 skill_desc="", max_soldiers=500, hp_per_soldier=10,
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
        self.attack_range = range_
        self.speed = speed

        self.max_morale = 100
        self.morale = 80
        self.is_routing = False

        self.facing = DIR_DOWN if team == "ai" else DIR_UP

        self.is_cavalry = is_cavalry
        self.special = special
        self.skill_name = skill_name
        self.skill_cost = skill_cost
        self.skill_desc = skill_desc

        self.is_charging = False
        self.charge_locked_this_turn = False
        self.has_moved = False
        self.can_move = True
        self.accumulated_momentum = 0

        self.is_calibrated = False
        self.calibration_turns = 0
        self.no_counter_this_attack = False
        self.archer_arrow = None
        self.siege_wall_bonus = False
        self.roster_uid = None
        self.split_sibling = None
        self.split_penalized = False
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
        self.general_defense_bonus = 0

        self.evolution_path = None
        self.evolution_star = 0
        self.evolution_mechanics = []

        self.is_general = False
        self.general_name = ""
        self.general_bonuses = {}

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
        result += self.general_defense_bonus
        if "def_flat_400" in self.evolution_mechanics:
            result += 400
        if "def_flat_500" in self.evolution_mechanics:
            result += 500
        return result

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

        if not self.is_routing and self.morale < 80:
            self.morale = min(80, self.morale + 3)

        if self.morale <= 0:
            self.is_routing = True
        elif self.is_routing and self.morale >= 30:
            self.is_routing = False

        if self.is_routing:
            self.ap = 0
            self.mp = 0
            self.can_move = False

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
        if getattr(self, "archer_arrow", None) == "longshot":
            bonus += 1
        if getattr(self, "siege_wall_bonus", False):
            bonus += 1
        if game is not None and self.attack_range > 1 \
                and game.terrain_map[self.y][self.x] in ("MOUNTAIN", "HIGHLAND"):
            bonus += 1
        return self.attack_range + bonus

    def get_minimum_range(self):
        return 0

    def calculate_hit_chance(self, defender, game):
        dist = max(abs(self.x - defender.x), abs(self.y - defender.y))
        if dist <= 1:
            return self._melee_hit_chance(defender, game)

        hit = self.base_accuracy
        if self.is_calibrated or self.is_rapid_salvo:
            hit += 20
        if "accuracy_plus_15" in self.evolution_mechanics:
            hit += 15
        hit -= (dist - 1) * 15

        at = game.terrain_map[self.y][self.x]
        dt = game.terrain_map[defender.y][defender.x]
        if at in ("MOUNTAIN", "HIGHLAND"):
            hit += 15
        if getattr(self, "siege_wall_bonus", False):
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

    def _melee_hit_chance(self, defender, game):
        hit = 90
        if self.morale < 50:
            hit -= 15
        if game is not None and game.terrain_map[defender.y][defender.x] == "FOREST":
            hit -= 10
        if getattr(defender, "is_routing", False):
            hit += 20
        if getattr(defender, "is_cavalry", False) and getattr(defender, "is_charging", False):
            hit -= 15
        if getattr(self, "is_general", False):
            hit += int(self.general_bonuses.get("hit_bonus", 0) * 0.5)
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
        morale_loss = int(damage_ratio * 40 + kills_ratio * 60)
        self.morale = max(0, self.morale - morale_loss)

        if self.morale <= 0 and not self.split_penalized:
            sibling = getattr(self, "split_sibling", None)
            if sibling is not None and sibling is not self and sibling.is_alive():
                sibling.morale = max(0, sibling.morale - 10)
            self.split_penalized = True

        if self.current_soldiers <= 0 and game:
            for u in game.units:
                if u is self or not u.is_alive() or u.team != self.team:
                    continue
                if max(abs(u.x - self.x), abs(u.y - self.y)) <= 3:
                    u.morale = max(0, u.morale - 5)
        return final, kills

    def get_skill_targets(self, game):
        return set()

    def execute_skill(self, game, target_tile=None):
        pass