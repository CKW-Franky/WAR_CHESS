from units.base_unit import BaseUnit


class Lancer(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="長槍兵", team=team, x=x, y=y,
            hp=4000, attack=1150, defense=400, range_=1, accuracy=100,
            speed=95, max_mp=4, is_cavalry=False, special="counter_cavalry",
            max_soldiers=400, hp_per_soldier=10, curve="balanced",
        )
        # 老兵 / 長槍 / 無盾 / 札甲 / 無馬
        self.apply_loadout(tier="老兵", weapon="長槍", weapon2=None,
                           shield=None, armor="札甲", mount=None)
