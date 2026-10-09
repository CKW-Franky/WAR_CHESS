from combat import (calculate_combat_result, check_line_of_sight,
                    DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, get_zoc_tiles)
from config import GRID_WIDTH, GRID_HEIGHT


class AIController:

    @staticmethod
    def generate_ai_actions(game, unit):
        actions = []
        if not unit or not unit.is_alive():
            return actions
        if unit.is_routing:
            return actions

        split_action = AIController._plan_split(game, unit)
        if split_action:
            actions.append(split_action)
        else:
            if unit.ap >= unit.skill_cost and not unit.skill_used_this_turn:
                skill_action = AIController._plan_skill(game, unit)
                if skill_action:
                    actions.append(skill_action)

        player_units = [u for u in game.units if u.is_alive() and u.team == "player"]
        if not player_units:
            return actions

        move_map, normal_atks, pierce_atks = game.get_possible_actions(unit)
        best = AIController._find_best_attack(unit, player_units, game,
                                              normal_atks, pierce_atks)
        if best:
            actions.append(best)
            return actions

        if move_map and unit.can_move:
            best_dest, cost = AIController._choose_best_move_tile(
                unit, player_units, game, move_map)
            if best_dest:
                actions.append({"type": "MOVE", "target": best_dest, "cost": cost})
                actions.append(AIController._plan_post_move_attack(
                    game, unit, best_dest, cost, player_units))
                actions = [a for a in actions if a is not None]
        return actions

    @staticmethod
    def _plan_split(game, unit):
        if not unit.can_split():
            return None
        if unit.current_soldiers < 300:
            return None
        occupied = {(u.x, u.y) for u in game.units if u.is_alive()}
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = unit.x + dx, unit.y + dy
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    continue
                if (nx, ny) in occupied:
                    continue
                enemies = [u for u in game.units
                           if u.is_alive() and u.team != unit.team]
                if enemies:
                    nearest = min(enemies,
                                  key=lambda e: max(abs(e.x - unit.x), abs(e.y - unit.y)))
                    fx, fy = nearest.x - unit.x, nearest.y - unit.y
                    facing = (DIR_RIGHT if fx > 0 else DIR_LEFT) if abs(fx) >= abs(fy) \
                        else (DIR_DOWN if fy > 0 else DIR_UP)
                else:
                    facing = DIR_DOWN
                return {"type": "SPLIT", "target": (nx, ny), "facing": facing}
        return None

    @staticmethod
    def _plan_skill(game, unit):
        if unit.name in ("長槍兵", "弩手", "弓騎兵"):
            return {"type": "SKILL"}
        if unit.name == "盾兵":
            allies = [
                u for u in game.units
                if u.is_alive() and u.team == "ai" and u is not unit
                and max(abs(u.x - unit.x), abs(u.y - unit.y)) <= 1
                and u.name in ("弩手", "弓箭手", "弓騎兵")
            ]
            if allies:
                return {"type": "SKILL", "target": (allies[0].x, allies[0].y)}
        return None

    @staticmethod
    def _plan_post_move_attack(game, unit, dest, cost, player_units):
        original = (unit.x, unit.y, unit.mp)
        unit.x, unit.y, unit.mp = dest[0], dest[1], unit.mp - cost
        try:
            _, normal, pierce = game.get_possible_actions(unit)
            return AIController._find_best_attack(
                unit, player_units, game, normal, pierce)
        finally:
            unit.x, unit.y, unit.mp = original

    @staticmethod
    def set_final_facing(game, unit):
        player_units = [u for u in game.units
                        if u.is_alive() and u.team == "player"]
        if not player_units:
            unit.set_facing(DIR_DOWN)
            return
        closest = min(player_units,
                      key=lambda p: abs(p.x - unit.x) + abs(p.y - unit.y))
        dx, dy = closest.x - unit.x, closest.y - unit.y
        if abs(dx) > abs(dy):
            unit.set_facing(DIR_RIGHT if dx > 0 else DIR_LEFT)
        else:
            unit.set_facing(DIR_DOWN if dy > 0 else DIR_UP)

    @staticmethod
    def _find_best_attack(unit, targets, game, normal_atks, pierce_atks):
        best_score = float("-inf")
        chosen = None

        for pos, landing in pierce_atks.items():
            defender = game.get_unit_at(*pos)
            if not defender or defender.team == unit.team:
                continue
            res = calculate_combat_result(unit, defender, game,
                                          action_type="PIERCE", preview=True)
            score = res["predicted_damage"] * 2.0
            if res["kills"] >= defender.current_soldiers:
                score += 50000
            score += (1.0 - defender.soldier_ratio) * 5000
            score += (100 - defender.morale) * 30
            if score > best_score:
                best_score = score
                chosen = {"type": "PIERCE", "target": pos, "landing": landing}

        for pos in normal_atks:
            defender = game.get_unit_at(*pos)
            if not defender or defender.team == unit.team:
                continue
            res = calculate_combat_result(unit, defender, game,
                                          action_type="NORMAL", preview=True)
            score = res["predicted_damage"] * (res["hit_chance"] / 100.0) * 2.0
            if res["kills"] >= defender.current_soldiers and res["hit_chance"] >= 70:
                score += 40000
            score += (1.0 - defender.soldier_ratio) * 4000
            score += (100 - defender.morale) * 30
            if res["angle"] == "REAR":
                score += 3000
            elif res["angle"] == "FLANK":
                score += 1500
            if score > best_score:
                best_score = score
                chosen = {"type": "ATTACK", "target": defender}
        return chosen

    @staticmethod
    def _choose_best_move_tile(unit, targets, game, move_map):
        primary = min(targets, key=lambda t: (
            t.soldier_ratio, abs(t.x - unit.x) + abs(t.y - unit.y)))
        best_score = float("-inf")
        best_tile = None
        best_cost = 0

        attack_range = unit.get_actual_range(game)
        is_ranged = attack_range > 1
        zoc = get_zoc_tiles(game.units, unit.team, GRID_WIDTH, GRID_HEIGHT)

        for (mx, my), cost in move_map.items():
            dist = max(abs(mx - primary.x), abs(my - primary.y))
            score = AIController._score_move_tile(
                unit, game, mx, my, primary, dist, attack_range, is_ranged, zoc, cost)
            if score > best_score:
                best_score = score
                best_tile = (mx, my)
                best_cost = cost
        return best_tile, best_cost

    @staticmethod
    def _score_move_tile(unit, game, mx, my, primary, dist,
                         attack_range, is_ranged, zoc, cost):

        score = 0.0

        if unit.name == "弓騎兵":
            if 2 <= dist <= 3:
                score += 3000
            elif dist == 1:
                score -= 5000
            elif dist > attack_range:
                score -= (dist - attack_range) * 800

        if is_ranged:
            if dist <= attack_range:
                score += 6000
                if check_line_of_sight(mx, my, primary.x, primary.y,
                                       game.terrain_map):
                    score += 5000
            else:
                score -= abs(dist - attack_range) * 1000
        else:
            score -= dist * 1500
            if dist == 1:
                score += 5000
            adjacent_enemies = sum(
                1 for ot in game.units
                if ot.is_alive() and ot.team != unit.team
                and max(abs(ot.x - mx), abs(ot.y - my)) <= 1
            )
            if adjacent_enemies >= 2:
                score -= (adjacent_enemies - 1) * 2500

        angle = AIController._eval_angle((mx, my), primary)
        if angle == "REAR":
            score += 3500
        elif angle == "FLANK":
            score += 1500

        terrain = game.terrain_map[my][mx]
        if terrain == "FOREST":
            score += 2000
        elif terrain == "MOUNTAIN" and is_ranged:
            score += 3000
        elif terrain == "HIGHLAND":
            if is_ranged:
                score += 4000
            else:
                score += 1000
        elif terrain == "VILLAGE":
            score += 1500
            if unit.current_soldiers < unit.max_soldiers * 0.6:
                score += 3000
        elif terrain == "RUINS":
            score += 1000
        elif terrain == "ROAD":
            score += 300
        elif terrain == "SWAMP":
            if is_ranged:
                score -= 500
            else:
                score -= 2000
        elif terrain == "RIVER":
            score -= 4000

        if (mx, my) in zoc:
            score -= 1500
        score -= cost * 200
        return score

    @staticmethod
    def _eval_angle(sim_pos, defender):
        dx = sim_pos[0] - defender.x
        dy = sim_pos[1] - defender.y
        if abs(dx) > abs(dy):
            rel = DIR_LEFT if dx > 0 else DIR_RIGHT
        else:
            rel = DIR_UP if dy > 0 else DIR_DOWN
        facing = getattr(defender, "facing", DIR_DOWN)
        if rel == facing:
            return "REAR"
        if (rel + 2) % 4 == facing:
            return "FRONT"
        return "FLANK"