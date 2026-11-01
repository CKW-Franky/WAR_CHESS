from units.base_unit import BaseUnit


class Shieldman(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="盾兵", team=team, x=x, y=y,
            hp=4500, attack=900, defense=450, range_=1, accuracy=100,
            speed=90, max_mp=4, is_cavalry=False, special="shield_wall",
            max_soldiers=400, hp_per_soldier=9, curve="tank",
        )
        # 老兵 / 刀 / 大盾 / 魚鱗甲 / 無馬
        self.apply_loadout(tier="老兵", weapon="刀", weapon2=None,
                           shield="大盾", armor="魚鱗甲", mount=None)
