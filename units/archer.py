from units.base_unit import BaseUnit


class Archer(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="弓箭手", team=team, x=x, y=y,
            hp=2800, attack=2900, defense=100, range_=5, accuracy=95,
            speed=100, max_mp=4, is_cavalry=False, special="standard_archer",
            max_soldiers=300, hp_per_soldier=7, curve="elite",
        )
        # 老兵 / 長弓 / 無盾 / 布衣 / 無馬
        self.apply_loadout(tier="老兵", weapon="長弓", weapon2=None,
                           shield=None, armor="布衣", mount=None)
