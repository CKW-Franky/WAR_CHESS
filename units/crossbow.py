from units.base_unit import BaseUnit


class Crossbow(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="弩手", team=team, x=x, y=y,
            hp=2400, attack=3000, defense=0, range_=5, accuracy=85,
            speed=80, max_mp=4, is_cavalry=False, special="calibration",
            skill_name="精密校準", skill_cost=40,
            skill_desc="校準：下一擊射程+1、命中+20%，本回合攻擊不受反擊。",
            max_soldiers=400, hp_per_soldier=6, curve="glass",
        )

    def execute_skill(self, game, target_tile=None):
        self.is_calibrated = True
        self.no_counter_this_attack = True
        self.calibration_turns = 2 if "double_calibration" in self.evolution_mechanics else 1
        game.add_damage_popup("校準完畢!", self.x, self.y, is_crit=True)