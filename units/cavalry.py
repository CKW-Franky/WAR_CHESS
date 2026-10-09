from units.base_unit import BaseUnit
from config import GRID_WIDTH, GRID_HEIGHT


class Cavalry(BaseUnit):
    def __init__(self, team, x, y):
        super().__init__(
            name="槍騎兵", team=team, x=x, y=y,
            hp=2600, attack=2400, defense=200, range_=1, accuracy=100,
            speed=120, max_mp=6, is_cavalry=True, special="charge_pierce",
            skill_name="破陣衝撞", skill_cost=60,
            skill_desc="擊退相鄰敵人，阻擋時 +300 真傷。",
            max_soldiers=200, hp_per_soldier=13, curve="elite",
        )

    def get_skill_targets(self, game):
        targets = set()
        occupied = {(u.x, u.y): u for u in game.units if u.is_alive()}
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = self.x + dx, self.y + dy
            tgt = occupied.get((nx, ny))
            if tgt and tgt.team != self.team:
                targets.add((nx, ny))
        return targets

    def execute_skill(self, game, target_tile=None):
        if not target_tile:
            valid = self.get_skill_targets(game)
            if not valid:
                return
            target_tile = next(iter(valid))

        tx, ty = target_tile
        target = game.get_unit_at(tx, ty)
        if not target:
            return

        dx, dy = tx - self.x, ty - self.y
        kb_x, kb_y = tx + dx, ty + dy
        occupied = {(u.x, u.y) for u in game.units if u.is_alive()}

        in_bounds = 0 <= kb_x < GRID_WIDTH and 0 <= kb_y < GRID_HEIGHT
        blocked = (
            not in_bounds
            or (kb_x, kb_y) in occupied
            or game.terrain_map[kb_y][kb_x] in ("MOUNTAIN", "RIVER")
        )

        momentum_mult = 400 if "charge_momentum_x2" in self.evolution_mechanics else 250
        momentum_cap = 9 if "charge_momentum_x2" in self.evolution_mechanics else 6
        mom = min(self.accumulated_momentum, momentum_cap)
        dmg = self.attack_power - target.defense + mom * momentum_mult
        if blocked:
            dmg += 300
            target.is_stunned = True
        else:
            target.x, target.y = kb_x, kb_y

        _, k = target.take_damage(dmg, self, game)
        label = "暈眩! 擊殺" if blocked else "擊退! 擊殺"
        game.add_damage_popup(f"{label} {k}", tx, ty, is_crit=True)
        game.trigger_visual_arrow((self.x, self.y), target_tile, is_skill=True)