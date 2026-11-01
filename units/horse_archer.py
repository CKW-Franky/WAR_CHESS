from units.base_unit import BaseUnit


class HorseArcher(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="弓騎兵", team=team, x=x, y=y,
            hp=2400, attack=2000, defense=150, range_=5, accuracy=95,
            speed=130, max_mp=7, is_cavalry=True, special="move_shoot_discount",
            max_soldiers=200, hp_per_soldier=12, curve="elite"
        )
        # 精銳 / 短弓 / 無盾 / 皮甲 / 良駒
        self.apply_loadout(tier="精銳", weapon="短弓", weapon2=None,
                           shield=None, armor="皮甲", mount="良駒")
