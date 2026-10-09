from save import save_meta, load_meta
import atexit

atexit.register(lambda: META.save())

META_SKILLS = {
    "atk_1": {"name": "力量覺醒", "desc": "全隊攻擊 +3%/級", "branch": "攻擊",
              "max_level": 5, "cost_per_level": 50,
              "effect": "permanent_atk_percent", "value_per_level": 3},
    "atk_2": {"name": "致命一擊", "desc": "背刺 +20%/級", "branch": "攻擊",
              "max_level": 3, "cost_per_level": 80,
              "effect": "backstab_bonus", "value_per_level": 20},
    "def_1": {"name": "鋼鐵意志", "desc": "全隊防禦 +3%/級", "branch": "防禦",
              "max_level": 5, "cost_per_level": 50,
              "effect": "permanent_def_percent", "value_per_level": 3},
    "def_2": {"name": "堅韌壁壘", "desc": "士兵上限 +1/級", "branch": "防禦",
              "max_level": 3, "cost_per_level": 120,
              "effect": "extra_soldiers", "value_per_level": 1},
    "eco_1": {"name": "商人直覺", "desc": "金幣 +10%/級", "branch": "經濟",
              "max_level": 5, "cost_per_level": 40,
              "effect": "gold_bonus", "value_per_level": 10},
    "eco_2": {"name": "起始資金", "desc": "每局金幣 +50/級", "branch": "經濟",
              "max_level": 5, "cost_per_level": 60,
              "effect": "starting_gold", "value_per_level": 50},
    "mor_1": {"name": "領導光環", "desc": "初始士氣 +5/級", "branch": "士氣",
              "max_level": 5, "cost_per_level": 40,
              "effect": "starting_morale", "value_per_level": 5},
    "exp_1": {"name": "老兵傳承", "desc": "經驗 +10%/級", "branch": "經驗",
              "max_level": 5, "cost_per_level": 60,
              "effect": "exp_bonus", "value_per_level": 10},
    "spec_1": {"name": "額外槽位", "desc": "人口 +1（每 2 級）", "branch": "特殊",
               "max_level": 4, "cost_per_level": 150,
               "effect": "extra_population", "value_per_level": 0.5},
}
ACHIEVEMENTS = {
    "first_win":  {"name": "初戰告捷", "desc": "首次贏得戰鬥", "reward": 50},
    "first_siege": {"name": "攻城初體驗", "desc": "首次攻下城池", "reward": 100},
    "kill_100":   {"name": "百人斬", "desc": "累積擊殺 100 士兵", "reward": 80},
    "kill_1000":  {"name": "千人斬", "desc": "累積擊殺 1000 士兵", "reward": 300},
    "kill_10000": {"name": "萬人敵", "desc": "累積擊殺 10000 士兵", "reward": 1000},
    "clear_act_1": {"name": "初露鋒芒", "desc": "通關第 1 幕", "reward": 150},
    "clear_act_2": {"name": "勢如破竹", "desc": "通關第 2 幕", "reward": 250},
    "clear_act_3": {"name": "天下無敵", "desc": "通關第 3 幕", "reward": 500},
    "max_star":   {"name": "五星上將", "desc": "任一兵種 5★", "reward": 200},
    "rich":       {"name": "富甲一方", "desc": "單局金幣達 1000", "reward": 200},
}


class MetaState:
    def __init__(self):
        self.soul_points = 0
        self.skill_levels = {}
        self.unlocked_achievements = set()
        self.stats = {
            "total_kills": 0, "total_battles": 0, "total_wins": 0,
            "total_losses": 0, "siege_wins": 0, "act_clears": 0,
            "campaign_clears": 0, "best_star": 0, "total_gold_earned": 0,
        }
        self.ascension_level = 0

    def add_soul(self, amount):
        self.soul_points += amount

    def spend_soul(self, amount):
        if self.soul_points < amount:
            return False
        self.soul_points -= amount
        return True

    def get_skill_level(self, sid):
        return self.skill_levels.get(sid, 0)

    def get_skill_cost(self, sid):
        skill = META_SKILLS.get(sid)
        if not skill:
            return 0
        return skill["cost_per_level"] * (self.get_skill_level(sid) + 1)

    def can_upgrade(self, sid):
        skill = META_SKILLS.get(sid)
        if not skill:
            return False
        if self.get_skill_level(sid) >= skill["max_level"]:
            return False
        return self.soul_points >= self.get_skill_cost(sid)

    def upgrade_skill(self, sid):
        if not self.can_upgrade(sid):
            return False
        if not self.spend_soul(self.get_skill_cost(sid)):
            return False
        self.skill_levels[sid] = self.get_skill_level(sid) + 1
        return True

    def get_effect_value(self, effect):
        total = 0.0
        for skill in META_SKILLS.values():
            if skill["effect"] == effect:
                total += skill["value_per_level"] * self.get_skill_level(
                    self._sid_of(skill))
        return total

    def _sid_of(self, skill):
        for sid, s in META_SKILLS.items():
            if s is skill:
                return sid
        return None

    def record_gold(self, amount):
        self.stats["total_gold_earned"] = (
            self.stats.get("total_gold_earned", 0) + amount)

    def record_act_clear(self):
        self.stats["act_clears"] = self.stats.get("act_clears", 0) + 1

    def update_best_star(self, star):
        if star > self.stats.get("best_star", 0):
            self.stats["best_star"] = star

    def check_achievements(self):
        stats = self.stats
        checks = {
            "first_win":   stats["total_wins"] >= 1,
            "first_siege": stats["siege_wins"] >= 1,
            "kill_100":    stats["total_kills"] >= 100,
            "kill_1000":   stats["total_kills"] >= 1000,
            "kill_10000":  stats["total_kills"] >= 10000,
            "clear_act_1": stats["act_clears"] >= 1,
            "clear_act_2": stats["act_clears"] >= 2,
            "clear_act_3": stats["act_clears"] >= 3,
            "max_star":    stats["best_star"] >= 5,
            "rich":        stats["total_gold_earned"] >= 1000,
        }
        newly_unlocked = []
        for aid, cond in checks.items():
            if aid not in self.unlocked_achievements and cond:
                self.unlocked_achievements.add(aid)
                self.add_soul(ACHIEVEMENTS[aid]["reward"])
                newly_unlocked.append(aid)
        return newly_unlocked

    def get_ascension_mult(self):
        return 100 + self.ascension_level * 10

    def to_dict(self):
        return {
            "soul_points": self.soul_points,
            "skill_levels": self.skill_levels,
            "unlocked_achievements": list(self.unlocked_achievements),
            "stats": self.stats,
            "ascension_level": self.ascension_level,
        }

    @classmethod
    def from_dict(cls, data):
        m = cls()
        if not data:
            return m
        m.soul_points = data.get("soul_points", 0)
        m.skill_levels = data.get("skill_levels", {})
        m.unlocked_achievements = set(data.get("unlocked_achievements", []))
        m.stats = data.get("stats", m.stats)
        m.ascension_level = data.get("ascension_level", 0)
        return m

    def save(self):
        save_meta(self.to_dict())

    @classmethod
    def load(cls):
        return cls.from_dict(load_meta())


META = MetaState.load()


def reload_meta(slot_id=None):
    if slot_id is not None:
        from save import set_slot
        set_slot(slot_id)
    fresh = MetaState.load()
    META.__dict__.clear()
    META.__dict__.update(fresh.__dict__)