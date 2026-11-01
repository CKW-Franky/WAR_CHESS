from units.base_unit import BaseUnit


class Crossbow(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="弩手", team=team, x=x, y=y,
            hp=2400, attack=3000, defense=0, range_=5, accuracy=85,
            speed=80, max_mp=4, is_cavalry=False, special="calibration",
            max_soldiers=300, hp_per_soldier=6, curve="glass",
        )
        # 老兵 / 弩 / 無盾 / 皮甲 / 無馬
        self.apply_loadout(tier="老兵", weapon="弩", weapon2=None,
                           shield=None, armor="皮甲", mount=None)
