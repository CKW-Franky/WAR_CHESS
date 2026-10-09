from units.cavalry import Cavalry
from units.horse_archer import HorseArcher
from units.lancer import Lancer
from units.shieldman import Shieldman
from units.archer import Archer
from units.crossbow import Crossbow
from units.bandit import Bandit, HorseBandit, ForestBandit, Deserter, MountainBandit

UNIT_CATALOG = {
    "槍騎兵": {"class": Cavalry, "hp": 2600, "attack": 2400, "defense": 200, "skill_name": "破陣衝撞"},
    "弓騎兵": {"class": HorseArcher, "hp": 2400, "attack": 2000, "defense": 150, "skill_name": "神速連射"},
    "長槍兵": {"class": Lancer, "hp": 4000, "attack": 1150, "defense": 400, "skill_name": "拒馬槍陣"},
    "盾兵": {"class": Shieldman, "hp": 4500, "attack": 900, "defense": 450, "skill_name": "援護架盾"},
    "弓箭手": {"class": Archer, "hp": 2800, "attack": 2900, "defense": 100, "skill_name": "換矢"},
    "弩手": {"class": Crossbow, "hp": 2400, "attack": 3000, "defense": 0, "skill_name": "精密校準"},
    "流寇": {"class": Bandit, "hp": 300, "attack": 400, "defense": 50, "skill_name": "", "enemy_only": True},
    "馬匪": {"class": HorseBandit, "hp": 250, "attack": 500, "defense": 30, "skill_name": "", "enemy_only": True},
    "林中強盜": {"class": ForestBandit, "hp": 400, "attack": 350, "defense": 80, "skill_name": "", "enemy_only": True},
    "逃兵": {"class": Deserter, "hp": 350, "attack": 450, "defense": 60, "skill_name": "", "enemy_only": True},
    "山賊": {"class": MountainBandit, "hp": 500, "attack": 300, "defense": 100, "skill_name": "", "enemy_only": True},
}


def create_unit(name, team, x, y):
    if name not in UNIT_CATALOG:
        raise ValueError(f"Unknown unit: {name}")
    return UNIT_CATALOG[name]["class"](team, x, y)