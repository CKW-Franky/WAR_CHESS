from units.base_unit import BaseUnit

ARROW_LABELS = {"armor_pierce": "穿甲箭", "fire": "火矢", "longshot": "長箭"}


class Archer(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="弓箭手", team=team, x=x, y=y,
            hp=2800, attack=2900, defense=100, range_=5, accuracy=95,
            speed=100, max_mp=4, is_cavalry=False, special="standard_archer",
            skill_name="換矢", skill_cost=30,
            skill_desc="切換箭矢：穿甲箭(無視40%防) / 火矢(+20%傷) / 長箭(射程+1、命中+10)。",
            max_soldiers=400, hp_per_soldier=7, curve="elite",
        )

    def execute_skill(self, game, target_tile=None):
        if self.archer_arrow is None:
            self.archer_arrow = "armor_pierce"
        elif self.archer_arrow == "armor_pierce":
            self.archer_arrow = "fire"
        elif self.archer_arrow == "fire":
            self.archer_arrow = "longshot"
        else:
            self.archer_arrow = None
        label = ARROW_LABELS.get(self.archer_arrow, "普通箭")
        game.add_damage_popup(f"換矢: {label}!", self.x, self.y, is_crit=True)
