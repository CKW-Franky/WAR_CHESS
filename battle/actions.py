"""Move / attack / charge / split / merge actions."""
import equipment
import terrain
from config import *  # noqa: F401,F403
from units import create_unit, UNIT_CATALOG
from battle.combat import (calculate_combat_result, strike_damage,
                           is_ranged_attacker)
from battle.movement import get_zoc_tiles, engaged_count


def consume_arrow(attacker):
    """One-shot arrow stance: cleared once a real (non-preview) shot resolves."""
    if getattr(attacker, "archer_arrow", None):
        attacker.archer_arrow = None


class ActionsMixin:
    def perform_move(self, unit, nx, ny, mp_cost):
        if unit.team == "player":
            self._snapshot_move_state(unit)

        ox, oy = unit.x, unit.y
        unit.mp -= mp_cost
        unit.x, unit.y = nx, ny
        unit.has_moved = True
        if self.terrain_map[ny][nx] == "RIVER" and not unit.is_cavalry:
            self.add_damage_popup(t("pop_river_cross"), nx, ny, is_wet=True)
        triggered = False

        if self._check_pike_interception(unit, nx, ny):
            triggered = True
        if self._check_opportunity_attack(unit, ox, oy, nx, ny):
            triggered = True
        if self._apply_cavalry_momentum(unit, nx, ny, mp_cost):
            triggered = True

        if triggered:
            self.last_move_state = None

    def _snapshot_move_state(self, unit):
        self.last_move_state = {
            "unit": unit,
            "x": unit.x, "y": unit.y, "mp": unit.mp,
            "has_moved": unit.has_moved,
            "accumulated_momentum": unit.accumulated_momentum,
            "is_charging": unit.is_charging,
            "morale": unit.morale,
            "soldiers": unit.current_soldiers,
            "soldier_hp": unit.soldier_hp,
            "pike_wall_active": unit.pike_wall_active,
            "opportunity_attack_used": unit.opportunity_attack_used,
        }

    def _check_pike_interception(self, unit, nx, ny):
        for other in self.units:
            if not other.is_alive() or other.team == unit.team:
                continue
            if not other.pike_wall_active:
                continue
            if other.name != "長槍兵":
                continue
            if max(abs(other.x - nx), abs(other.y - ny)) > 1:
                continue

            unit.mp = 0
            damage = strike_damage(other, unit, self)
            if unit.is_cavalry:
                damage = damage * 2
                if "pike_vs_cavalry_x1_5" in getattr(other, "evolution_mechanics", []):
                    damage = damage * 3 // 2
            _, kills = unit.take_damage(max(1, damage), other, self)
            other.pike_wall_active = False
            self.add_damage_popup(f"槍陣! 擊殺 {kills}", nx, ny, is_crit=True)
            self.trigger_visual_arrow((other.x, other.y), (nx, ny))
            return True
        return False

    def _check_opportunity_attack(self, unit, ox, oy, nx, ny):
        triggered = False
        if not unit.is_alive():
            return False

        for enemy in self.units:
            if not enemy.is_alive() or enemy.team == unit.team:
                continue
            if enemy.name not in ("長槍兵", "盾兵"):
                continue
            if enemy.opportunity_attack_used:
                continue

            was_adjacent = max(abs(enemy.x - ox), abs(enemy.y - oy)) <= 1
            now_adjacent = max(abs(enemy.x - nx), abs(enemy.y - ny)) <= 1
            if not (was_adjacent and not now_adjacent):
                continue

            base = strike_damage(enemy, unit, self, scale=0.5)
            if unit.is_cavalry:
                base = base * 2
            _, kills = unit.take_damage(base, enemy, self)
            enemy.opportunity_attack_used = True
            self.add_damage_popup(f"機會! 擊殺 {kills}", nx, ny, is_crit=True)
            self.trigger_visual_arrow((enemy.x, enemy.y), (nx, ny))
            triggered = True
        return triggered

    def _apply_cavalry_momentum(self, unit, nx, ny, mp_cost):
        if not (unit.is_cavalry and unit.is_charging):
            return False

        if self.terrain_map[ny][nx] == "RIVER":
            unit.is_charging = False
            unit.accumulated_momentum = 0
            self.add_damage_popup(t("pop_water_break"), nx, ny, is_wet=True)
            return True

        gained = max(1, int(mp_cost + 0.5))
        mechanics = getattr(unit, "evolution_mechanics", [])
        momentum_cap = 9 if "charge_momentum_x2" in mechanics else 6
        unit.accumulated_momentum = min(momentum_cap,
                                        unit.accumulated_momentum + gained)
        self.add_damage_popup(t("pop_momentum", val=gained),
                              unit.x, unit.y, is_crit=True)
        return False

    def perform_attack(self, attacker, defender):
        moved_before_attack = bool(getattr(attacker, "has_moved", False))
        dist = max(abs(attacker.x - defender.x), abs(attacker.y - defender.y))
        actual_target = defender

        guard = None
        if dist > 1 and defender.guarded_by and defender.guarded_by.is_alive():
            guard = defender.guarded_by

        if guard and "guard_transfer_100" not in getattr(guard, "evolution_mechanics", []):
            full_result = calculate_combat_result(attacker, defender, self,
                                                  "NORMAL", preview=False)
            consume_arrow(attacker)
            total_dmg = full_result["predicted_damage"]
            main_dmg = int(total_dmg * 0.4)
            shield_dmg = int(total_dmg * 0.6)
            self.trigger_visual_arrow((attacker.x, attacker.y),
                                      (defender.x, defender.y))
            defender.take_damage(main_dmg, attacker, self)
            guard.take_damage(shield_dmg, attacker, self)
            self.add_damage_popup(t("pop_shield_guard"),
                                  defender.x, defender.y, is_crit=True)
            if attacker.is_rapid_salvo:
                attacker.is_rapid_salvo = False
            if attacker.is_calibrated:
                if getattr(attacker, "calibration_turns", 0) <= 1:
                    attacker.is_calibrated = False
                    attacker.calibration_turns = 0
                    attacker.no_counter_this_attack = False
                else:
                    attacker.calibration_turns -= 1
            attacker.ap -= self.get_attack_ap_cost(attacker)
            attacker.accumulated_momentum = 0
            shot = getattr(attacker, "active_weapon", None)
            if shot is not None and shot.reload_required:
                attacker.loaded = not moved_before_attack
                if attacker.loaded:
                    self.add_damage_popup("自動裝填", attacker.x, attacker.y,
                                          is_crit=True)
            self.check_game_over()
            return

        if guard:
            actual_target = guard
            self.add_damage_popup(t("pop_shield_guard"),
                                  defender.x, defender.y, is_crit=True)

        result = calculate_combat_result(attacker, actual_target, self,
                                         "NORMAL", preview=False)
        consume_arrow(attacker)
        hits = result.get("hits", 0)
        misses = result.get("misses", 0)
        damage = result["predicted_damage"]

        self.trigger_visual_arrow((attacker.x, attacker.y),
                                  (actual_target.x, actual_target.y))

        if attacker.is_rapid_salvo:
            attacker.is_rapid_salvo = False
        if attacker.is_calibrated:
            if getattr(attacker, "calibration_turns", 0) <= 1:
                attacker.is_calibrated = False
                attacker.calibration_turns = 0
                attacker.no_counter_this_attack = False
            else:
                attacker.calibration_turns -= 1

        shot = getattr(attacker, "active_weapon", None)
        if shot is not None and shot.reload_required:
            attacker.loaded = not moved_before_attack
            if attacker.loaded:
                self.add_damage_popup("自動裝填", attacker.x, attacker.y,
                                      is_crit=True)

        if damage > 0:
            if result.get("is_crit"):
                self.add_damage_popup("暴擊!", actual_target.x, actual_target.y,
                                      is_crit=True)
            dealt, kills = actual_target.take_damage(damage, attacker, self)
            if misses > 0 and hits > 0:
                self.add_damage_popup(f"命中 {hits}/{hits + misses}",
                                      actual_target.x, actual_target.y)
            if kills > 0:
                self.add_damage_popup(t("pop_model_loss", count=kills),
                                      actual_target.x, actual_target.y - 1,
                                      is_crit=True)
            else:
                self.add_damage_popup(f"-{dealt}", actual_target.x, actual_target.y)
            if "splash_30" in getattr(attacker, "evolution_mechanics", []):
                splash = int(damage * 0.3)
                if splash > 0:
                    for u in self.units:
                        if u is actual_target or not u.is_alive() or u.team == attacker.team:
                            continue
                        if max(abs(u.x - actual_target.x), abs(u.y - actual_target.y)) <= 1:
                            u.take_damage(splash, attacker, self)
        else:
            self.add_damage_popup("MISS!", actual_target.x, actual_target.y,
                                  is_miss=True)

        attacker.ap -= self.get_attack_ap_cost(attacker)
        attacker.accumulated_momentum = 0

        if actual_target.is_alive() and result["can_counter"]:
            counter_damage = result.get("counter_damage", 0)
            actual_target.ap -= 30
            _, counter_kills = attacker.take_damage(counter_damage, actual_target, self)
            self.add_damage_popup(f"反擊! 擊殺 {counter_kills}",
                                  attacker.x, attacker.y, is_crit=True)
            self.trigger_visual_arrow((actual_target.x, actual_target.y),
                                      (attacker.x, attacker.y))

        self._try_horse_archer_retreat(attacker)
        self.check_game_over()

    def _try_horse_archer_retreat(self, unit):
        if unit.name != "弓騎兵":
            return
        if unit.mp < 1:
            return

        enemies = [u for u in self.units if u.is_alive() and u.team != unit.team]
        if not enemies:
            return
        closest = min(enemies, key=lambda e: max(abs(e.x - unit.x), abs(e.y - unit.y)))

        mechanics = getattr(unit, "evolution_mechanics", [])
        max_steps = 2 if "retreat_plus_1" in mechanics else 1

        occupied = {(u.x, u.y) for u in self.units if u.is_alive() and u is not unit}
        for _ in range(max_steps):
            if unit.mp < 1:
                break
            best_tile = None
            best_dist = max(abs(closest.x - unit.x), abs(closest.y - unit.y))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = unit.x + dx, unit.y + dy
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    continue
                if (nx, ny) in occupied:
                    continue
                if self.terrain_map[ny][nx] == "MOUNTAIN":
                    continue
                d = max(abs(closest.x - nx), abs(closest.y - ny))
                if d > best_dist:
                    best_dist = d
                    best_tile = (nx, ny)
            if not best_tile:
                break
            unit.mp -= 1
            unit.x, unit.y = best_tile
            occupied.add(best_tile)

    def perform_charge_pierce(self, lancer, defender, landing):
        if not defender:
            return

        result = calculate_combat_result(lancer, defender, self, "PIERCE",
                                         preview=False)
        consume_arrow(lancer)
        self.trigger_visual_arrow((lancer.x, lancer.y),
                                  (defender.x, defender.y))
        _, pierce_kills = defender.take_damage(result["predicted_damage"], lancer, self)
        self.add_damage_popup(f"貫穿! 擊殺 {pierce_kills}",
                              defender.x, defender.y, is_crit=True)
        if result.get("is_crit"):
            self.add_damage_popup("暴擊!", defender.x, defender.y, is_crit=True)

        lancer.ap -= 40
        lancer.x, lancer.y = landing
        lancer.has_moved = True

        if self.terrain_map[landing[1]][landing[0]] == "RIVER":
            lancer.is_charging = False
        mechanics = getattr(lancer, "evolution_mechanics", [])
        momentum_cap = 9 if "charge_momentum_x2" in mechanics else 6
        if not defender.is_alive():
            lancer.accumulated_momentum = min(momentum_cap,
                                               lancer.accumulated_momentum // 2)
        else:
            lancer.accumulated_momentum = 0

        if defender.is_alive() and result["can_counter"]:
            counter_damage = result.get("counter_damage", 0)
            defender.ap -= 30
            _, intercept_kills = lancer.take_damage(counter_damage, defender, self)
            self.add_damage_popup(f"迎擊! 擊殺 {intercept_kills}",
                                  lancer.x, lancer.y, is_crit=True)

        self.check_game_over()

    def _get_split_targets(self, unit):
        occupied = {(u.x, u.y) for u in self.units if u.is_alive()}
        targets = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = unit.x + dx, unit.y + dy
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    continue
                if (nx, ny) in occupied:
                    continue
                targets.add((nx, ny))
        return targets

    def _find_merge_target(self, unit):
        if not unit:
            return None
        candidates = [u for u in self.units
                      if u is not unit and u.is_alive() and unit.can_merge_with(u)]
        if not candidates:
            return None
        return max(candidates, key=lambda u: (
            u.current_soldiers,
            -max(abs(u.x - unit.x), abs(u.y - unit.y))))

    def _trigger_merge(self, unit):
        target = self._find_merge_target(unit)
        if not target:
            self.add_damage_popup(t("merge_invalid"), unit.x, unit.y, is_miss=True)
            return
        self.perform_merge(unit, target)

    def _clear_split_state(self):
        self.is_split_targeting = False
        self.is_split_facing = False
        self.split_unit = None
        self.split_pos = None

    def trigger_split_intent(self, unit):
        if unit.current_soldiers < 200:
            self.add_damage_popup(t("split_soldier_lack"), unit.x, unit.y, is_miss=True)
            return
        if unit.ap < 30:
            self.add_damage_popup(t("split_ap_lack"), unit.x, unit.y, is_miss=True)
            return
        if not self._get_split_targets(unit):
            self.add_damage_popup(t("split_no_space"), unit.x, unit.y, is_miss=True)
            return
        self.is_split_targeting = True
        self.is_split_facing = False
        self.split_unit = unit
        self.split_pos = None

    def _handle_split_target_click(self, gx, gy):
        unit = self.split_unit
        if not unit or (gx, gy) not in self._get_split_targets(unit):
            return
        self.split_pos = (gx, gy)
        self.is_split_targeting = False
        self.is_split_facing = True

    def _handle_split_facing_click(self, gx, gy):
        if not self.split_pos:
            return
        sx, sy = self.split_pos
        dx, dy = gx - sx, gy - sy
        direction = -1
        if (dx, dy) == (0, -1):
            direction = DIR_UP
        elif (dx, dy) == (1, 0):
            direction = DIR_RIGHT
        elif (dx, dy) == (0, 1):
            direction = DIR_DOWN
        elif (dx, dy) == (-1, 0):
            direction = DIR_LEFT
        if direction == -1:
            return
        self.perform_split(self.split_unit, self.split_pos, direction)
        self._clear_split_state()

    def perform_split(self, unit, target_pos, new_facing):
        if not unit or not unit.can_split():
            return False
        if target_pos not in self._get_split_targets(unit):
            return False

        unit.ap -= 30
        half = unit.current_soldiers // 2
        unit.current_soldiers -= half
        unit.soldier_hp = unit.hp_per_soldier

        new_unit = create_unit(unit.name, unit.team, target_pos[0], target_pos[1])
        new_unit.evolution_mechanics = list(unit.evolution_mechanics)
        new_unit.evolution_star = unit.evolution_star
        new_unit.evolution_path = unit.evolution_path
        new_unit.equip_attack_bonus = unit.equip_attack_bonus
        new_unit.equip_defense_bonus = unit.equip_defense_bonus
        new_unit.elite_attack_bonus = unit.elite_attack_bonus
        new_unit.elite_defense_bonus = unit.elite_defense_bonus

        base_max = getattr(unit, "_base_max_soldiers", unit.max_soldiers)
        new_unit._base_max_soldiers = base_max
        new_unit.max_soldiers = base_max
        new_unit.hp_per_soldier = unit.hp_per_soldier
        new_unit.morale = unit.morale

        new_unit.is_temporary = True

        new_unit.current_soldiers = min(half, new_unit.max_soldiers)
        new_unit.soldier_hp = unit.hp_per_soldier
        new_unit.ap = 0
        new_unit.mp = 0
        new_unit.set_facing(new_facing)

        unit.split_sibling = new_unit
        new_unit.split_sibling = unit

        self.units.append(new_unit)
        self.add_damage_popup(t("pop_split", half=half), unit.x, unit.y, is_crit=True)
        return True

    def perform_merge(self, unit_a, unit_b):
        if not unit_a or not unit_b or not unit_a.can_merge_with(unit_b):
            return False
        unit_a.ap -= 20
        gained = unit_b.current_soldiers
        unit_a.current_soldiers = min(unit_a.max_soldiers,
                                      unit_a.current_soldiers + unit_b.current_soldiers)
        unit_a.morale = (unit_a.morale + unit_b.morale) // 2
        unit_a.soldier_hp = unit_a.hp_per_soldier
        unit_a.split_sibling = None

        self.units.remove(unit_b)
        if unit_b in self.round_queue:
            self.round_queue.remove(unit_b)
        if unit_b in self.timeline_queue:
            self.timeline_queue.remove(unit_b)
        self.add_damage_popup(t("pop_merge", count=gained), unit_a.x, unit_a.y, is_crit=True)
        return True
