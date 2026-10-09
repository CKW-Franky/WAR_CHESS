import random
from save import save_temple, load_temple

SURNAMES = ["趙", "關", "張", "馬", "黃", "諸葛", "司馬", "周", "陸", "呂",
            "曹", "夏侯", "孫", "甘", "太史", "董", "袁", "公孫", "韓", "李"]
GIVEN_NAMES = ["雲", "羽", "飛", "超", "忠", "亮", "懿", "瑜", "遜", "布",
               "操", "淵", "權", "寧", "慈", "卓", "紹", "瓚", "信", "廣"]
ENEMY_NAMES = ["華雄", "顏良", "文醜", "張郃", "高覽", "淳于瓊", "紀靈", "嚴白虎",
               "劉璋", "張魯", "孟獲", "沙摩柯", "公孫度", "袁譚", "袁尚"]

STAT_KEYS = ["wu", "mou", "tong", "zhi", "yun"]
STAT_NAMES = {"wu": "武勇", "mou": "韜略", "tong": "統御", "zhi": "智略", "yun": "氣運"}

RANKS = ["", "什長", "隊正", "校尉"]
RANK_THRESHOLDS = [0, 100, 400, 1000]
MERIT_THRESHOLDS = [100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500, 5500]

STATUS_ACTIVE = "active"
STATUS_MOURNING = "mourning"
STATUS_RETIRED = "retired"
STATUS_DEAD = "dead"

UNIT_TYPE_BUFFS = {
    "騎兵": {"effect": "cavalry_charge_bonus", "value": 5, "name": "騎兵衝鋒 +5%"},
    "步兵": {"effect": "infantry_def_bonus", "value": 5, "name": "步兵防禦 +5%"},
    "弓兵": {"effect": "archer_hit_bonus", "value": 5, "name": "弓兵命中 +5%"},
}
MAX_BUFF_PER_TYPE = 15

REVIVE_MULTIPLIERS = [1.0, 0.9, 0.8, 0.7, 0.6]


def get_unit_category(name):
    if name in ("槍騎兵", "弓騎兵"):
        return "騎兵"
    if name in ("長槍兵", "盾兵"):
        return "步兵"
    if name in ("弓箭手", "弩手"):
        return "弓兵"
    return "步兵"


class General:
    def __init__(self, name=None, wu=None, mou=None, tong=None, zhi=None, yun=None,
                 merit=0, rank=0, status=STATUS_ACTIVE, mourning_remaining=0,
                 revive_count=0, unit_type=None, loyalty=50):
        self.name = name or (random.choice(SURNAMES) + random.choice(GIVEN_NAMES))
        self.wu = wu if wu is not None else random.randint(30, 50)
        self.mou = mou if mou is not None else random.randint(30, 50)
        self.tong = tong if tong is not None else random.randint(30, 50)
        self.zhi = zhi if zhi is not None else random.randint(30, 50)
        self.yun = yun if yun is not None else random.randint(30, 50)
        self.merit = merit
        self.rank = rank
        self.status = status
        self.mourning_remaining = mourning_remaining
        self.revive_count = revive_count
        self.unit_type = unit_type
        self.loyalty = loyalty

    @staticmethod
    def generate_enemy(act=1):
        base = 40 + act * 5
        return General(
            name=random.choice(ENEMY_NAMES),
            wu=random.randint(base, base + 15),
            mou=random.randint(base, base + 15),
            tong=random.randint(base, base + 15),
            zhi=random.randint(base, base + 15),
            yun=random.randint(base, base + 15),
            loyalty=random.randint(30, 70),
        )

    def get_level(self):
        lv = 0
        for th in MERIT_THRESHOLDS:
            if self.merit >= th:
                lv += 1
            else:
                break
        return lv

    def get_next_threshold(self):
        lv = self.get_level()
        if lv >= len(MERIT_THRESHOLDS):
            return None
        return MERIT_THRESHOLDS[lv]

    def get_current_base(self):
        lv = self.get_level()
        return MERIT_THRESHOLDS[lv - 1] if lv > 0 else 0

    def get_rank_name(self):
        return RANKS[min(self.rank, len(RANKS) - 1)]

    def update_rank(self):
        for i in range(len(RANK_THRESHOLDS) - 1, -1, -1):
            if self.merit >= RANK_THRESHOLDS[i]:
                self.rank = i
                return

    def get_revive_mult(self):
        idx = min(self.revive_count, len(REVIVE_MULTIPLIERS) - 1)
        return REVIVE_MULTIPLIERS[idx]

    def add_merit(self, amount):
        self.merit += int(amount * self.get_revive_mult())
        leveled = []
        for _ in range(len(MERIT_THRESHOLDS)):
            threshold = self.get_next_threshold()
            if threshold is None or self.merit < threshold:
                break
            candidates = [k for k in STAT_KEYS if getattr(self, k) < 100]
            if not candidates:
                break
            key = random.choice(candidates)
            setattr(self, key, getattr(self, key) + 1)
            leveled.append(key)
        self.update_rank()
        return leveled

    def get_bonuses(self):
        return {
            "damage_mult": 1.0 + self.wu * 0.005,
            "hit_bonus": self.mou * 0.3,
            "crit_bonus": (self.mou + self.yun) * 0.15,
            "soldier_flat": self.tong * 2,
            "defense_bonus": self.tong,
            "heal_ratio": self.zhi * 0.006,
            "income_mult": 1.0 + self.yun * 0.01,
            "exp_mult": 1.0 + self.tong * 0.005,
        }

    def to_dict(self):
        return {
            "name": self.name, "wu": self.wu, "mou": self.mou,
            "tong": self.tong, "zhi": self.zhi, "yun": self.yun,
            "merit": self.merit, "rank": self.rank, "status": self.status,
            "mourning_remaining": self.mourning_remaining,
            "revive_count": self.revive_count,
            "unit_type": self.unit_type, "loyalty": self.loyalty,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d.get("name"),
            wu=d.get("wu", 30), mou=d.get("mou", 30), tong=d.get("tong", 30),
            zhi=d.get("zhi", 30), yun=d.get("yun", 30),
            merit=d.get("merit", 0), rank=d.get("rank", 0),
            status=d.get("status", STATUS_ACTIVE),
            mourning_remaining=d.get("mourning_remaining", 0),
            revive_count=d.get("revive_count", 0),
            unit_type=d.get("unit_type"), loyalty=d.get("loyalty", 50),
        )


class WarTemple:
    def __init__(self):
        self.main_hall = []
        self.mourning = []
        self.hall_of_fame = []
        self.martyr_shrine = []
        self.permanent_buffs = {}

    def add_new(self, g):
        g.status = STATUS_ACTIVE
        self.main_hall.append(g)

    def on_battle_end(self, g, survived, retire=False):
        if not survived:
            g.status = STATUS_DEAD
            self.martyr_shrine.append(g)
            return "dead"
        if retire or g.rank >= 3:
            g.status = STATUS_RETIRED
            self.hall_of_fame.append(g)
            self._apply_fame_buff(g)
            return "retired"
        g.status = STATUS_MOURNING
        g.mourning_remaining = 1
        g.revive_count += 1
        self.mourning.append(g)
        return "mourning"

    def _apply_fame_buff(self, g):
        if not g.unit_type:
            return
        info = UNIT_TYPE_BUFFS.get(g.unit_type)
        if not info:
            return
        effect = info["effect"]
        current = self.permanent_buffs.get(effect, 0)
        self.permanent_buffs[effect] = min(current + info["value"], MAX_BUFF_PER_TYPE)

    def advance_mourning(self):
        still_mourning = []
        for g in self.mourning:
            g.mourning_remaining -= 1
            if g.mourning_remaining <= 0:
                g.status = STATUS_ACTIVE
                self.main_hall.append(g)
            else:
                still_mourning.append(g)
        self.mourning = still_mourning

    def get_active(self):
        return [g for g in self.main_hall if g.status == STATUS_ACTIVE]

    def to_dict(self):
        return {
            "main_hall": [g.to_dict() for g in self.main_hall],
            "mourning": [g.to_dict() for g in self.mourning],
            "hall_of_fame": [g.to_dict() for g in self.hall_of_fame],
            "martyr_shrine": [g.to_dict() for g in self.martyr_shrine],
            "permanent_buffs": self.permanent_buffs,
        }

    @classmethod
    def from_dict(cls, data):
        wt = cls()
        if not data:
            return wt
        wt.main_hall = [General.from_dict(d) for d in data.get("main_hall", [])]
        wt.mourning = [General.from_dict(d) for d in data.get("mourning", [])]
        wt.hall_of_fame = [General.from_dict(d) for d in data.get("hall_of_fame", [])]
        wt.martyr_shrine = [General.from_dict(d) for d in data.get("martyr_shrine", [])]
        wt.permanent_buffs = data.get("permanent_buffs", {})
        return wt

    def save(self):
        save_temple(self.to_dict())

    @classmethod
    def load(cls):
        return cls.from_dict(load_temple())