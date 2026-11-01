"""Turn order, action enumeration and pathing."""
import heapq
import random

import equipment
import terrain
from config import *  # noqa: F401,F403
from units import create_unit, UNIT_CATALOG
from battle.combat import (calculate_combat_result, strike_damage,
                           is_ranged_attacker)
from battle.movement import get_zoc_tiles, engaged_count


class EngineMixin:
    def advance_to_next_unit(self):
        self.round_queue = [u for u in self.round_queue if u.is_alive()]

        if not self.round_queue:
            living = [u for u in self.units if u.is_alive()]
            if not living:
                self.check_game_over()
                return
            self.round_queue = sorted(
                living, key=lambda u: u.speed + random.random() * 0.1,
                reverse=True)
            self.turn_number += 1

        if not self.round_queue:
            self.check_game_over()
            return

        self.active_unit = self.round_queue.pop(0)
        self.active_unit.reset_turn()
        _u = self.active_unit
        if self.terrain_map[_u.y][_u.x] == "BARRACKS" and _u.is_alive():
            heal = max(1, _u.max_soldiers // 20)
            _u.current_soldiers = min(_u.max_soldiers, _u.current_soldiers + heal)
        self.selected_unit = (self.active_unit
                              if self.active_unit.team == "player" else None)
        self.last_ai_action_time = 0
        self.last_move_state = None

        living = [u for u in self.units if u.is_alive()]
        self.timeline_queue = self.round_queue + sorted(
            living, key=lambda u: u.speed, reverse=True)

    def execute_ai_action(self, action):
        unit = self.active_unit
        if not unit or not unit.is_alive():
            return

        action_type = action["type"]
        if action_type == "SKILL":
            unit.ap -= unit.skill_cost
            unit.execute_skill(self, action.get("target"))
            unit.skill_used_this_turn = True
        elif action_type == "MOVE":
            self.perform_move(unit, action["target"][0], action["target"][1],
                              action["cost"])
        elif action_type == "ATTACK":
            self.perform_attack(unit, action["target"])
        elif action_type == "PIERCE":
            self.perform_charge_pierce(unit, self.get_unit_at(*action["target"]),
                                       action["landing"])
        elif action_type == "SPLIT":
            self.perform_split(unit, action.get("target"),
                               action.get("facing", DIR_DOWN))
        elif action_type == "RELOAD":
            self.reload_crossbow(unit)

    def get_possible_actions(self, unit):
        move_map, normal_atks, pierce_atks = {}, set(), {}
        occupied = {(u.x, u.y) for u in self.units if u.is_alive()}
        zoc = get_zoc_tiles(self.units, unit.team, GRID_WIDTH, GRID_HEIGHT)

        if unit.can_move and unit.mp >= 1.0:
            if unit.is_cavalry and unit.is_charging:
                self._compute_charge_moves(unit, occupied, zoc, move_map)
            else:
                self._compute_normal_moves(unit, occupied, zoc, move_map)

        self._compute_attack_targets(unit, occupied, normal_atks, pierce_atks)
        return move_map, normal_atks, pierce_atks

    def _compute_charge_moves(self, unit, occupied, zoc, move_map):
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0),
                      (1, 1), (-1, -1), (1, -1), (-1, 1)]
        for dx, dy in directions:
            step_cost = 2 if (dx != 0 and dy != 0) else 1
            accumulated = 0
            cx, cy = unit.x, unit.y
            while True:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    break
                if (nx, ny) in occupied:
                    break
                if self.terrain_map[ny][nx] == "MOUNTAIN":
                    break

                extra = terrain.move_extra(self.terrain_map[ny][nx], True)
                if extra is None:
                    break
                total_step = max(1, step_cost + extra)
                if accumulated + total_step > unit.mp:
                    break
                accumulated += total_step
                move_map[(nx, ny)] = accumulated
                cx, cy = nx, ny

    def _compute_normal_moves(self, unit, occupied, zoc, move_map):
        heap = [(0, unit.x, unit.y)]
        dists = {(unit.x, unit.y): 0}
        neighbor_offsets = [(dx, dy)
                            for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                            if not (dx == 0 and dy == 0)]

        while heap:
            current_cost, cx, cy = heapq.heappop(heap)
            if current_cost > dists.get((cx, cy), float("inf")):
                continue

            for dx, dy in neighbor_offsets:
                base_cost = 2 if (dx != 0 and dy != 0) else 1
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    continue
                if (nx, ny) in occupied:
                    continue

                extra = terrain.move_extra(self.terrain_map[ny][nx],
                                           unit.is_cavalry)
                if extra is None:
                    continue
                new_cost = current_cost + max(1, base_cost + extra)
                if new_cost > unit.mp:
                    continue
                if new_cost >= dists.get((nx, ny), float("inf")):
                    continue

                dists[(nx, ny)] = new_cost
                heapq.heappush(heap, (new_cost, nx, ny))
                move_map[(nx, ny)] = new_cost

    def _compute_attack_targets(self, unit, occupied, normal_atks, pierce_atks):
        ap_cost = self.get_attack_ap_cost(unit)
        attack_range = unit.get_actual_range(self)
        min_range = unit.get_minimum_range()

        if unit.ap < ap_cost:
            return
        if not getattr(unit, "can_fire", True):
            return

        for other in self.units:
            if not other.is_alive() or other.team == unit.team:
                continue

            chebyshev = max(abs(unit.x - other.x), abs(unit.y - other.y))
            manhattan = abs(unit.x - other.x) + abs(unit.y - other.y)

            if chebyshev < min_range:
                continue

            if (unit.special == "charge_pierce" and unit.is_charging
                    and manhattan == 1):
                self._try_add_pierce_target(unit, other, occupied, pierce_atks)

            if unit.is_cavalry and unit.is_charging:
                if manhattan == 1:
                    normal_atks.add((other.x, other.y))
            else:
                if chebyshev <= attack_range:
                    normal_atks.add((other.x, other.y))

    def _try_add_pierce_target(self, unit, other, occupied, pierce_atks):
        dx, dy = other.x - unit.x, other.y - unit.y
        landing_x, landing_y = other.x + dx, other.y + dy
        if not (0 <= landing_x < GRID_WIDTH and 0 <= landing_y < GRID_HEIGHT):
            return
        if (landing_x, landing_y) in occupied:
            return
        pierce_atks[(other.x, other.y)] = (landing_x, landing_y)

    def find_path(self, unit, target_x, target_y):
        if (unit.x, unit.y) == (target_x, target_y):
            return []

        occupied = {(u.x, u.y) for u in self.units
                    if u.is_alive() and u is not unit}
        zoc = get_zoc_tiles(self.units, unit.team, GRID_WIDTH, GRID_HEIGHT)

        heap = [(0, unit.x, unit.y)]
        dists = {(unit.x, unit.y): 0}
        prev = {}
        neighbor_offsets = [(dx, dy)
                            for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                            if not (dx == 0 and dy == 0)]

        while heap:
            current_cost, cx, cy = heapq.heappop(heap)
            if current_cost > dists.get((cx, cy), float("inf")):
                continue

            if (cx, cy) == (target_x, target_y):
                path = []
                cursor = (target_x, target_y)
                while cursor != (unit.x, unit.y):
                    path.append(cursor)
                    cursor = prev[cursor]
                path.reverse()
                return path

            for dx, dy in neighbor_offsets:
                base_cost = 2 if (dx != 0 and dy != 0) else 1
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    continue
                if (nx, ny) in occupied:
                    continue

                extra = terrain.move_extra(self.terrain_map[ny][nx],
                                           unit.is_cavalry)
                if extra is None:
                    continue
                new_cost = current_cost + max(1, base_cost + extra)
                if new_cost > unit.mp:
                    continue
                if new_cost >= dists.get((nx, ny), float("inf")):
                    continue

                dists[(nx, ny)] = new_cost
                prev[(nx, ny)] = (cx, cy)
                heapq.heappush(heap, (new_cost, nx, ny))
        return None

    def get_unit_at(self, x, y):
        return next((u for u in self.units
                     if u.is_alive() and u.x == x and u.y == y), None)

    def get_attack_ap_cost(self, unit):
        if unit.is_rapid_salvo:
            return 30
        if unit.special == "move_shoot_discount" and unit.has_moved:
            return 40
        return 60

    def toggle_cavalry_charge(self, unit):
        if unit.is_charging and unit.charge_locked_this_turn:
            self.add_damage_popup(t("pop_charge_locked"), unit.x, unit.y, is_miss=True)
            return

        if not unit.is_charging:
            if unit.ap < CHARGE_TOGGLE_AP:
                self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
                return
            unit.ap -= CHARGE_TOGGLE_AP
            unit.is_charging = True
            unit.charge_locked_this_turn = True
            unit.accumulated_momentum = 0
            self.add_damage_popup(t("pop_charge_on"), unit.x, unit.y, is_crit=True)
        else:
            unit.is_charging = False
            unit.accumulated_momentum = 0
            self.add_damage_popup(t("pop_charge_off"), unit.x, unit.y)
