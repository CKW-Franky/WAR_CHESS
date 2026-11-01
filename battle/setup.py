"""Terrain generation, deployment and AI setup for quick mode."""
import random

import terrain
from config import GRID_WIDTH, GRID_HEIGHT
from units import create_unit


class SetupMixin:
    def setup_initial_units(self, player_comp):
        self._setup_player_units(player_comp)
        self._setup_ai_units()

    def _deploy_tile(self, preferred_x, is_cavalry):
        y = 18
        while y > 16 and self.terrain_map[y][preferred_x] in ("RIVER", "MOUNTAIN"):
            y -= 1
        if (terrain.is_passable(self.terrain_map[y][preferred_x], is_cavalry)
                and self.get_unit_at(preferred_x, y) is None):
            return preferred_x, y
        for ny in range(19, 15, -1):
            for nx in range(GRID_WIDTH):
                if (terrain.is_passable(self.terrain_map[ny][nx], is_cavalry)
                        and self.get_unit_at(nx, ny) is None):
                    return nx, ny
        return preferred_x, y

    def _setup_player_units(self, player_comp):
        for i, name in enumerate(player_comp):
            unit = create_unit(name, "player", 0, 0)
            unit.x, unit.y = self._deploy_tile(i * 2 + 2, unit.is_cavalry)
            self.units.append(unit)

    def _setup_ai_units(self):
        ai_count = 5
        ai_pool = ["槍騎兵", "弓騎兵", "長槍兵", "盾兵", "弩手"]
        if random.random() < 0.5:
            for i, name in enumerate(ai_pool):
                if name in ("弩手", "弓騎兵"):
                    ai_pool[i] = "弓箭手"
                    break
        random.shuffle(ai_pool)
        ai_pool = ai_pool[:ai_count]

        melee_spots = [(x, 3) for x in range(GRID_WIDTH)]
        ranged_spots = [(x, y) for x in range(GRID_WIDTH)
                        for y in (0, 1, 2)]
        random.shuffle(melee_spots)
        random.shuffle(ranged_spots)

        for name in ai_pool:
            enemy = create_unit(name, "ai", 0, 0)
            spot = (ranged_spots.pop() if enemy.is_ranged_weapon
                    else melee_spots.pop())
            enemy.x, enemy.y = spot
            mult = self.enemy_mult / 100.0
            enemy.base_attack = int(enemy.base_attack * mult)
            enemy.base_defense = int(enemy.base_defense * mult)
            enemy.hp_per_soldier = max(1, int(enemy.hp_per_soldier * mult))
            enemy.soldier_hp = enemy.hp_per_soldier
            self.units.append(enemy)

    def generate_terrain(self):
        terrain_map = [["NORMAL" for _ in range(GRID_WIDTH)]
                       for _ in range(GRID_HEIGHT)]

        for y in (9, 10):
            for x in range(GRID_WIDTH):
                terrain_map[y][x] = "RIVER"

        for y in range(GRID_HEIGHT):
            if y in (9, 10):
                continue
            for x in range(GRID_WIDTH):
                roll = random.random()
                if roll < 0.15:
                    terrain_map[y][x] = "FOREST"
                elif roll < 0.25:
                    terrain_map[y][x] = "MOUNTAIN"
                elif roll < 0.33:
                    terrain_map[y][x] = "HIGHLAND"

        for x in (3, 8, 12):
            for y in (9, 10):
                terrain_map[y][x] = "BRIDGE"

        return terrain_map
