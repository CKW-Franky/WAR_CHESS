from units.base_unit import BaseUnit


class Bandit(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="流寇", team=team, x=x, y=y,
            hp=300, attack=400, defense=50, range_=1, accuracy=90,
            speed=90, max_mp=3, is_cavalry=False, special=None,
            skill_name="", skill_cost=0,
            max_soldiers=50, hp_per_soldier=6, curve="balanced",
        )
        self.morale = 50


class HorseBandit(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="馬匪", team=team, x=x, y=y,
            hp=250, attack=500, defense=30, range_=1, accuracy=90,
            speed=115, max_mp=5, is_cavalry=True, special=None,
            skill_name="", skill_cost=0,
            max_soldiers=30, hp_per_soldier=8, curve="glass",
        )


class ForestBandit(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="林中強盜", team=team, x=x, y=y,
            hp=400, attack=350, defense=80, range_=1, accuracy=90,
            speed=90, max_mp=3, is_cavalry=False, special=None,
            skill_name="", skill_cost=0,
            max_soldiers=60, hp_per_soldier=7, curve="balanced",
        )


class Deserter(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="逃兵", team=team, x=x, y=y,
            hp=350, attack=450, defense=60, range_=1, accuracy=90,
            speed=90, max_mp=3, is_cavalry=False, special=None,
            skill_name="", skill_cost=0,
            max_soldiers=40, hp_per_soldier=9, curve="balanced",
        )
        self.morale = 40


class MountainBandit(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="山賊", team=team, x=x, y=y,
            hp=500, attack=300, defense=100, range_=1, accuracy=90,
            speed=80, max_mp=2, is_cavalry=False, special=None,
            skill_name="", skill_cost=0,
            max_soldiers=70, hp_per_soldier=7, curve="tank",
        )
