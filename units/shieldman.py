from units.base_unit import BaseUnit


class Shieldman(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="盾兵", team=team, x=x, y=y,
            hp=4500, attack=900, defense=450, range_=1, accuracy=100,
            speed=90, max_mp=4, is_cavalry=False, special="shield_wall",
            skill_name="援護架盾", skill_cost=40,
            skill_desc="援護相鄰友軍，承受其遠程傷害。",
            max_soldiers=500, hp_per_soldier=9, curve="tank",
        )

    def get_skill_targets(self, game):
        targets = set()
        occupied = {(u.x, u.y): u for u in game.units if u.is_alive()}
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = self.x + dx, self.y + dy
            tgt = occupied.get((nx, ny))
            if tgt and tgt.team == self.team and tgt is not self and tgt.name != "盾兵":
                targets.add((nx, ny))
        return targets

    def execute_skill(self, game, target_tile=None):
        if getattr(self, "guarding_used_this_turn", False):
            game.add_damage_popup("每回合只能援護一次", self.x, self.y, is_miss=True)
            return
        if not target_tile:
            valid = self.get_skill_targets(game)
            if not valid:
                game.add_damage_popup("不能援護盾兵", self.x, self.y, is_miss=True)
                return
            target_tile = next(iter(valid))

        tx, ty = target_tile
        target = game.get_unit_at(tx, ty)
        if not target:
            return
        target.guarded_by = self
        self.guarding_used_this_turn = True
        game.add_damage_popup("盾牆已架設!", tx, ty, is_crit=True)
        game.trigger_visual_arrow((self.x, self.y), target_tile, is_skill=True)