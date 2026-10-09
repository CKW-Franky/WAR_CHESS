from units.base_unit import BaseUnit


class Lancer(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="長槍兵", team=team, x=x, y=y,
            hp=4000, attack=1150, defense=400, range_=1, accuracy=100,
            speed=95, max_mp=4, is_cavalry=False, special="counter_cavalry",
            skill_name="拒馬槍陣", skill_cost=25,
            skill_desc="架設防線，敵方近戰進入相鄰格時中斷並受傷。",
            max_soldiers=400, hp_per_soldier=10, curve="balanced",
        )

    def execute_skill(self, game, target_tile=None):
        self.pike_wall_active = True
        game.add_damage_popup("槍陣已架設!", self.x, self.y, is_crit=True)