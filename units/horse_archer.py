from units.base_unit import BaseUnit
from config import t


class HorseArcher(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="弓騎兵", team=team, x=x, y=y,
            hp=2400, attack=2000, defense=150, range_=5, accuracy=95,
            speed=130, max_mp=7, is_cavalry=True, special="move_shoot_discount",
            skill_name="神速連射", skill_cost=40,
            skill_desc="連射姿態：下一擊 1.5 倍傷害、+20% 命中。",
            max_soldiers=200, hp_per_soldier=12, curve="elite"
        )

    def execute_skill(self, game, target_tile=None):
        self.is_rapid_salvo = True
        game.add_damage_popup("連射準備!", self.x, self.y, is_crit=True)