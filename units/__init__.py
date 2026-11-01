from units.cavalry import Cavalry
from units.horse_archer import HorseArcher
from units.lancer import Lancer
from units.shieldman import Shieldman
from units.archer import Archer
from units.crossbow import Crossbow

UNIT_CATALOG = {
    "槍騎兵": {"class": Cavalry, "hp": 2600, "attack": 2400, "defense": 200},
    "弓騎兵": {"class": HorseArcher, "hp": 2400, "attack": 2000, "defense": 150},
    "長槍兵": {"class": Lancer, "hp": 4000, "attack": 1150, "defense": 400},
    "盾兵": {"class": Shieldman, "hp": 4500, "attack": 900, "defense": 450},
    "弓箭手": {"class": Archer, "hp": 2800, "attack": 2900, "defense": 100},
    "弩手": {"class": Crossbow, "hp": 2400, "attack": 3000, "defense": 0},
}


def create_unit(name, team, x, y):
    if name not in UNIT_CATALOG:
        raise ValueError(f"Unknown unit: {name}")
    return UNIT_CATALOG[name]["class"](team, x, y)