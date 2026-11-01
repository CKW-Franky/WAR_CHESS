from units.base_unit import BaseUnit


class Cavalry(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="槍騎兵", team=team, x=x, y=y,
            hp=2600, attack=2400, defense=200, range_=1, accuracy=100,
            speed=120, max_mp=6, is_cavalry=True, special="charge_pierce",
            max_soldiers=200, hp_per_soldier=13, curve="elite",
        )
        # 老兵 / 騎槍 / 小盾 / 札甲 / 戰馬
        self.apply_loadout(tier="老兵", weapon="騎槍", weapon2=None,
                           shield="小盾", armor="札甲", mount="戰馬")
