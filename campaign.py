import random
from rogue import (MVP_TEMPLATE, NODE_COMBAT, NODE_ELITE, NODE_SHOP,
                   NODE_REST, NODE_EVENT, NODE_SIEGE, NODE_BOSS,
                   pick_random_event)
from general import (General, WarTemple, get_unit_category,
                     STATUS_ACTIVE)
from meta import META


ACT_INFO = {
    1: {"enemy_count": 3, "enemy_mult": 100, "population": 3},
    2: {"enemy_count": 4, "enemy_mult": 120, "population": 4},
    3: {"enemy_count": 5, "enemy_mult": 150, "population": 5},
}

EVOLUTION_PATHS = {
    "槍騎兵": {
        "A": {"name": "破軍鐵騎", "desc": "衝鋒動能上限 +3"},
        "B": {"name": "鐵壁重騎", "desc": "衝鋒時受遠程傷害 -40%"},
    },
    "弓騎兵": {
        "A": {"name": "疾風獵手", "desc": "撤退距離 +1 格"},
        "B": {"name": "精準射手", "desc": "游擊傷害不再衰減"},
    },
    "長槍兵": {
        "A": {"name": "鐵壁長槍", "desc": "拒馬對騎兵傷害 ×1.5"},
        "B": {"name": "破甲槍兵", "desc": "對非騎兵攻擊 +40%"},
    },
    "盾兵": {
        "A": {"name": "守護者", "desc": "援護轉移 100% 傷害"},
        "B": {"name": "鐵壁戰士", "desc": "免疫背後加傷"},
    },
    "弓箭手": {
        "A": {"name": "神射手", "desc": "站樁傷害 +30%"},
        "B": {"name": "箭雨大師", "desc": "攻擊濺射相鄰格 30%"},
    },
    "弩手": {
        "A": {"name": "破甲專家", "desc": "破甲 50%"},
        "B": {"name": "連弩手", "desc": "校準可連續使用 2 回合"},
    },
}

STAR_THRESHOLD = {1: 100, 2: 300, 3: 600, 4: 1200, 5: 2000}
STAR_BONUS = {
    0: {"atk": 0,   "def": 0,   "hp": 0},
    1: {"atk": 15,  "def": 10,  "hp": 15},
    2: {"atk": 35,  "def": 25,  "hp": 30},
    3: {"atk": 60,  "def": 40,  "hp": 50},
    4: {"atk": 90,  "def": 65,  "hp": 75},
    5: {"atk": 130, "def": 100, "hp": 110},
}

PATH_MECHANICS = {
    ("槍騎兵", "A"): ["charge_momentum_x2"],
    ("槍騎兵", "B"): ["charge_ranged_resist"],
    ("弓騎兵", "A"): ["retreat_plus_1"],
    ("弓騎兵", "B"): ["skirmish_no_penalty"],
    ("長槍兵", "A"): ["pike_vs_cavalry_x1_5"],
    ("長槍兵", "B"): ["atk_vs_infantry_40"],
    ("盾兵", "A"): ["guard_transfer_100"],
    ("盾兵", "B"): ["rear_immunity"],
    ("弓箭手", "A"): ["stand_still_30"],
    ("弓箭手", "B"): ["splash_30"],
    ("弩手", "A"): ["armor_pierce_50"],
    ("弩手", "B"): ["double_calibration"],
}

MAX_GENERALS = 3

UNLOCK_ORDER = ["弩手", "盾兵", "槍騎兵", "弓騎兵"]

MAX_POPULATION = 5

MAP_COLUMNS = 10
MAP_ROWS = 3

BANDIT_UNITS = ["流寇", "馬匪", "林中強盜", "逃兵", "山賊"]
REGULAR_UNITS = ["槍騎兵", "弓騎兵", "長槍兵", "盾兵", "弩手", "弓箭手"]


def get_star_from_exp(exp):
    star = 0
    for s in sorted(STAR_THRESHOLD):
        if exp >= STAR_THRESHOLD[s]:
            star = s
    return star


def get_star_bonus(star):
    return STAR_BONUS.get(star, STAR_BONUS[0])


def get_mechanics(name, path):
    if not path:
        return []
    return PATH_MECHANICS.get((name, path), [])


class MapNode:
    def __init__(self, column, row, node_type, data=None):
        self.column = column
        self.row = row
        self.layer = column
        self.node_type = node_type
        self.data = data or {}
        self.connections = []
        self.completed = False


class CampaignState:
    def __init__(self):
        self.act = 1
        self.unit_exp = {}
        self.unit_path = {}
        self.gold = 150
        self.unlocked_units = ["長槍兵", "弓箭手"]
        self.pending_buffs = []
        self.permanent_buffs = []
        self.population_bonus = 0
        self.rogue_map = []
        self.current_layer = 0
        self.last_node = None
        self.seen_events = []

        self.roster = []

        self.current_generals = []
        self.general_assignments = {}
        self.general_roster_slots = {}
        self._uid_counter = 0
        self.war_temple = WarTemple.load()

    def new_roster_uid(self):
        self._uid_counter += 1
        return self._uid_counter

    @property
    def base_population(self):
        return 2

    @property
    def population(self):
        return min(MAX_POPULATION, self.base_population + self.population_bonus)

    def generate_rogue_map(self):
        self.rogue_map = []
        for col in range(MAP_COLUMNS):
            for row in range(MAP_ROWS):
                node_type = self._roll_node_type(col)
                node = MapNode(col, row, node_type)
                if node_type in (NODE_COMBAT, NODE_ELITE):
                    node.data = self._gen_combat_data(node_type, col)
                elif node_type == NODE_SIEGE:
                    node.data = self._gen_siege_data(col)
                self.rogue_map.append(node)
        for i, node in enumerate(self.rogue_map):
            if node.column < MAP_COLUMNS - 1:
                node.connections = [j for j, n in enumerate(self.rogue_map)
                                    if n.column == node.column + 1]
        self.current_layer = 0

    def _roll_node_type(self, col):
        if col == 4 or col == 9:
            return NODE_SIEGE
        if col == 0:
            return NODE_COMBAT
        r = random.random()
        if r < 0.40:
            return NODE_COMBAT
        if r < 0.55:
            return NODE_SHOP
        if r < 0.70:
            return NODE_REST
        if r < 0.85:
            return NODE_EVENT
        return NODE_ELITE

    def _gen_combat_data(self, node_type, layer):
        mult = 100 + (self.act - 1) * 15
        count = 3 + (self.act - 1)
        if node_type == NODE_ELITE:
            mult += 20
            count += 1
        if node_type == NODE_COMBAT and layer <= 2:
            count += random.randint(1, 2)
        pool = self._build_enemy_pool(node_type, layer, count)
        return {
            "enemy_count": len(pool),
            "enemy_mult": mult,
            "gold": 50 if node_type == NODE_COMBAT else 100,
            "exp": 100 if node_type == NODE_COMBAT else 180,
            "enemy_pool": pool,
        }

    def _build_enemy_pool(self, node_type, layer, count):
        bandits = list(BANDIT_UNITS)
        regulars = list(REGULAR_UNITS)
        if node_type in (NODE_SIEGE, NODE_BOSS):
            return [random.choice(regulars) for _ in range(count)]
        if node_type == NODE_ELITE:
            pool = [random.choice(regulars)]
            pool += [random.choice(bandits) for _ in range(max(0, count - 1))]
            random.shuffle(pool)
            return pool
        if layer <= 2:
            return [random.choice(bandits) for _ in range(count)]
        if layer <= 6:
            half = max(1, count // 2)
            pool = [random.choice(regulars) for _ in range(half)]
            pool += [random.choice(bandits) for _ in range(count - half)]
            random.shuffle(pool)
            return pool
        return [random.choice(regulars) for _ in range(count)]

    def _gen_siege_data(self, column):
        if self.act == 1:
            count = 2 if column == 4 else 3
        else:
            count = 4 if column == 4 else 5
        mult = 100 + (self.act - 1) * 20 + (column - 4) * 10
        pool = [random.choice(REGULAR_UNITS) for _ in range(count)]
        return {
            "enemy_count": count,
            "enemy_mult": mult,
            "gold": 150 + column * 20,
            "exp": 220 + column * 20,
            "is_boss": (column == 9),
            "enemy_pool": pool,
        }

    def get_current_node(self):
        return self.last_node

    def get_available_layer(self):
        return self.current_layer

    def is_map_complete(self):
        return self.current_layer >= MAP_COLUMNS

    def complete_current_node(self):
        if self.last_node:
            self.last_node.completed = True
        self.current_layer += 1

    def apply_permanent_buff(self, buff):
        effect = buff.get("effect")
        value = buff.get("value", 0)
        if effect == "permanent_population":
            self.population_bonus += value
        elif effect == "permanent_unlock":
            self.unlock_next_unit()
        else:
            self.permanent_buffs.append({"effect": effect, "value": value})

    def get_permanent_bonus(self, effect):
        return sum(b["value"] for b in self.permanent_buffs if b["effect"] == effect)

    def get_shop_cost(self, base):
        discount = self.get_permanent_bonus("permanent_shop_discount")
        return max(1, int(base * (100 - discount) / 100))

    def add_exp(self, name, amount):
        bonus = self.get_permanent_bonus("permanent_exp")
        bonus += int(META.get_effect_value("exp_bonus"))
        real = int(amount * (100 + bonus) / 100)
        self.unit_exp[name] = self.unit_exp.get(name, 0) + real
        star = self.get_star(name)
        if star > META.stats.get("best_star", 0):
            META.stats["best_star"] = star

    def add_exp_all(self, amount):
        for name in list(self.unlocked_units):
            self.add_exp(name, amount)

    def get_exp(self, name):
        return self.unit_exp.get(name, 0)

    def get_star(self, name):
        return get_star_from_exp(self.unit_exp.get(name, 0))

    def get_path(self, name):
        return self.unit_path.get(name)

    def set_path(self, name, path):
        self.unit_path[name] = path

    def needs_path_choice(self, name):
        return self.get_star(name) >= 3 and self.get_path(name) is None

    def pending_path_names(self):
        return [n for n in self.unit_exp if self.needs_path_choice(n)]

    def add_gold(self, amount):
        self.gold = max(0, self.gold + amount)

    def spend_gold(self, amount):
        if self.gold < amount:
            return False
        self.gold -= amount
        return True

    def add_buff(self, effect, value):
        self.pending_buffs.append({"effect": effect, "value": value})

    def consume_buffs(self):
        buffs = list(self.pending_buffs)
        self.pending_buffs = []
        return buffs

    def is_unlocked_unit(self, name):
        return name in self.unlocked_units

    def unlock_next_unit(self):
        for u in UNLOCK_ORDER:
            if u not in self.unlocked_units:
                self.unlocked_units.append(u)
                return u
        return None

    def roster_unit_names(self):
        return [u["name"] for u in self.roster]

    def is_roster_full(self):
        return len(self.roster) >= self.population

    def _roster_max_soldiers(self, name):
        from units import create_unit
        unit = create_unit(name, "player", 0, 0)
        return unit.max_soldiers + int(META.get_effect_value("extra_soldiers"))

    def recruit_unit_to_roster(self, name):
        if self.is_roster_full():
            return False
        if name not in self.unlocked_units:
            return False
        self.roster.append({"name": name,
                            "current_soldiers": self._roster_max_soldiers(name),
                            "uid": self.new_roster_uid()})
        return True

    def reinforce_unit(self, index, soldiers):
        if not (0 <= index < len(self.roster)):
            return 0
        entry = self.roster[index]
        max_soldiers = self._roster_max_soldiers(entry["name"])
        current = entry.get("current_soldiers", max_soldiers)
        if current >= max_soldiers:
            return 0
        gained = min(soldiers, max_soldiers - current)
        entry["current_soldiers"] = current + gained
        return gained

    def remove_dead_unit(self):
        self.roster = [u for u in self.roster if u.get("current_soldiers", 0) > 0]

    def clear_roster(self):
        self.roster = []

    def can_add_general(self):
        return len(self.current_generals) < MAX_GENERALS

    def add_general(self, g):
        if not self.can_add_general():
            return False
        g.status = STATUS_ACTIVE
        self.current_generals.append(g)
        return True

    def get_available_generals(self):
        assigned = set(self.general_assignments)
        return [g for g in self.current_generals if g.name not in assigned]

    def assign_general(self, g, unit):
        self.general_assignments[g.name] = unit
        self._apply_general_bonuses(g, unit)
        g.unit_type = get_unit_category(unit.name)

    def _apply_general_bonuses(self, g, unit):
        bonuses = g.get_bonuses()
        unit.is_general = True
        unit.general_name = g.name
        unit.general_bonuses = bonuses
        if not hasattr(unit, "_base_max_soldiers"):
            unit._base_max_soldiers = unit.max_soldiers
        unit.max_soldiers = unit._base_max_soldiers + bonuses.get("soldier_flat", 0)
        unit.general_defense_bonus = bonuses.get("defense_bonus", 0)
        unit.current_soldiers = min(unit.current_soldiers, unit.max_soldiers)
        unit.soldier_hp = unit.hp_per_soldier

    def clear_assignments(self):
        self.general_assignments = {}

    def roll_event(self):
        ev = pick_random_event(exclude_ids=self.seen_events)
        self.seen_events.append(ev["id"])
        if len(self.seen_events) > 5:
            self.seen_events.pop(0)
        return ev

    def next_act(self):
        self.act += 1
        if self.act > 2:
            return False
        self.generate_rogue_map()
        return True

    def to_dict(self):
        return {
            "act": self.act,
            "gold": self.gold,
            "unlocked_units": self.unlocked_units,
            "unit_exp": self.unit_exp,
            "unit_path": self.unit_path,
            "population_bonus": self.population_bonus,
            "permanent_buffs": self.permanent_buffs,
            "current_layer": self.current_layer,
            "completed_layers": [n.layer for n in self.rogue_map if n.completed],
            "roster": self.roster,
            "general_roster_slots": self.general_roster_slots,
            "uid_counter": self._uid_counter,
            "current_general_names": [g.name for g in self.current_generals],
        }

    @classmethod
    def from_dict(cls, data):
        cs = cls()
        if not data:
            return cs

        cs.act = data.get("act", 1)
        cs.gold = data.get("gold", 150)
        cs.unlocked_units = data.get("unlocked_units", ["長槍兵", "弓箭手"])
        cs.unit_exp = data.get("unit_exp", {})
        cs.unit_path = data.get("unit_path", {})
        cs.population_bonus = data.get("population_bonus", 0)
        cs.permanent_buffs = data.get("permanent_buffs", [])
        cs.roster = data.get("roster", [])
        cs.general_roster_slots = data.get("general_roster_slots", {})
        cs._uid_counter = data.get("uid_counter", 0)
        for entry in cs.roster:
            if "uid" not in entry:
                entry["uid"] = cs.new_roster_uid()
            cs._uid_counter = max(cs._uid_counter, entry["uid"])

        cs.generate_rogue_map()
        cs.current_layer = data.get("current_layer", 0)
        completed = set(data.get("completed_layers", []))
        for node in cs.rogue_map:
            if node.layer in completed:
                node.completed = True

        general_names = data.get("current_general_names", [])
        if general_names:
            wt = cs.war_temple
            picked = []
            for name in general_names:
                for g in wt.main_hall:
                    if g.name == name and g not in picked:
                        picked.append(g)
                        break
            for g in picked:
                if g in wt.main_hall:
                    wt.main_hall.remove(g)
            cs.current_generals = picked

        return cs