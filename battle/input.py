"""Battlefield clicks, facing, skill targeting, undo."""
import heapq
import random

import equipment
import terrain
from config import *  # noqa: F401,F403
from units import create_unit, UNIT_CATALOG
from battle.combat import (calculate_combat_result, strike_damage,
                           is_ranged_attacker)
from battle.movement import get_zoc_tiles, engaged_count


class InputMixin:
    def _handle_gameplay_click(self, pos):
        if self.lang_btn.collidepoint(pos):
            toggle_language()
            return
        if self.game_state == GAME_OVER:
            self._handle_game_over_click(pos)
            return
        if self.game_state == AWAITING_DIRECTION:
            self.handle_facing_click(pos)
            return
        if self.game_state == GAMEPLAY and self.active_unit and self.active_unit.team == "player":
            self.handle_click(pos)

    def handle_click(self, pos):
        if self.end_turn_btn.collidepoint(pos):
            self.start_facing_selection()
            return
        if (self.active_unit and self.active_unit.team == "player"
                and self.active_unit.is_cavalry
                and self.charge_toggle_btn.collidepoint(pos)):
            self.toggle_cavalry_charge(self.active_unit)
            return
        if (self.active_unit and self.active_unit.team == "player"
                and self.active_unit.name == "弓箭手"
                and self.follow_up_btn.collidepoint(pos)):
            self.follow_up_attack(self.active_unit)
            return
        ctx = (self.context_action(self.active_unit)
               if self.active_unit and self.active_unit.team == "player" else None)
        if ctx and self.context_btn.collidepoint(pos):
            self.trigger_context_action(ctx)
            return
        if (self.active_unit and self.active_unit.team == "player"
                and self.skill_btn.collidepoint(pos)):
            self.trigger_skill_intent(self.active_unit)
            return
        if (self.active_unit and self.active_unit.team == "player"
                and self.split_btn.collidepoint(pos)):
            self.trigger_split_intent(self.active_unit)
            return
        if (self.active_unit and self.active_unit.team == "player"
                and self.merge_btn.collidepoint(pos)):
            self._trigger_merge(self.active_unit)
            return
        if self.game_state != GAMEPLAY:
            return
        if not (self.active_unit and self.active_unit.team == "player"):
            return

        actor = self.active_unit
        self.selected_unit = actor

        gx = (pos[0] - self.grid_offset_x) // GRID_SIZE
        gy = (pos[1] - self.grid_offset_y) // GRID_SIZE
        if not (0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT):
            return

        if self.is_split_facing:
            self._handle_split_facing_click(gx, gy)
            return
        if self.is_split_targeting:
            self._handle_split_target_click(gx, gy)
            return

        target = self.get_unit_at(gx, gy)
        if self.is_skill_targeting:
            self._handle_skill_target_click(actor, gx, gy)
            return

        self._handle_action_click(actor, gx, gy, target)

    def _handle_skill_target_click(self, actor, gx, gy):
        if actor.skill_used_this_turn:
            self.add_damage_popup("本回合已使用技能", actor.x, actor.y, is_miss=True)
            self.is_skill_targeting = False
            return
        valid = actor.get_skill_targets(self)
        if (gx, gy) in valid:
            actor.ap -= actor.skill_cost
            actor.execute_skill(self, (gx, gy))
            actor.skill_used_this_turn = True
        self.is_skill_targeting = False

    def _handle_action_click(self, actor, gx, gy, target):
        move, normal, pierce = self.get_possible_actions(actor)

        if (gx, gy) in pierce:
            self.perform_charge_pierce(actor, target, pierce[(gx, gy)])
            self.last_move_state = None
        elif (gx, gy) in normal and target and target.team != actor.team:
            self.perform_attack(actor, target)
            self.last_move_state = None
        elif (gx, gy) in move:
            self.perform_move(actor, gx, gy, move[(gx, gy)])
        else:
            self.is_skill_targeting = False

    def handle_facing_click(self, pos):
        if not self.unit_to_face:
            self.end_unit_turn()
            return

        gx = (pos[0] - self.grid_offset_x) // GRID_SIZE
        gy = (pos[1] - self.grid_offset_y) // GRID_SIZE
        unit = self.unit_to_face
        dx, dy = gx - unit.x, gy - unit.y

        direction = -1
        if (dx, dy) == (0, -1):
            direction = DIR_UP
        elif (dx, dy) == (1, 0):
            direction = DIR_RIGHT
        elif (dx, dy) == (0, 1):
            direction = DIR_DOWN
        elif (dx, dy) == (-1, 0):
            direction = DIR_LEFT

        if direction != -1:
            unit.set_facing(direction)
        self.end_unit_turn()

    def trigger_skill_intent(self, unit):
        skill = unit.weapon_skill
        if skill is None:
            return
        if unit.skill_used_this_turn:
            self.add_damage_popup("本回合已使用技能", unit.x, unit.y, is_miss=True)
            return
        if unit.ap < skill.ap_cost:
            self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
            return

        targets = unit.get_skill_targets(self)
        if targets:
            self.is_skill_targeting = not self.is_skill_targeting
        elif skill.id in ("guard", "break_charge"):
            self.add_damage_popup("沒有合法目標", unit.x, unit.y, is_miss=True)
            return
        else:
            unit.ap -= skill.ap_cost
            unit.execute_skill(self)
            unit.skill_used_this_turn = True
            self.is_skill_targeting = False

    def start_facing_selection(self):
        if self.active_unit and self.active_unit.team == "player":
            self.game_state = AWAITING_DIRECTION
            self.unit_to_face = self.active_unit

    def end_unit_turn(self):
        self.game_state = GAMEPLAY
        self.active_unit = None
        self.selected_unit = None
        self.unit_to_face = None
        self.is_skill_targeting = False
        self.ai_action_queue = []
        self.last_move_state = None
        self.check_game_over()

    def undo_move(self):
        if not self.last_move_state:
            return

        state = self.last_move_state
        unit = state["unit"]
        unit.x, unit.y = state["x"], state["y"]
        unit.mp = state["mp"]
        unit.has_moved = state["has_moved"]
        unit.accumulated_momentum = state["accumulated_momentum"]
        unit.is_charging = state["is_charging"]
        unit.morale = state.get("morale", unit.morale)
        unit.current_soldiers = state.get("soldiers", unit.current_soldiers)
        unit.soldier_hp = state.get("soldier_hp", unit.soldier_hp)
        unit.pike_wall_active = state.get("pike_wall_active", unit.pike_wall_active)
        unit.opportunity_attack_used = state.get("opportunity_attack_used",
                                                 unit.opportunity_attack_used)
        self.last_move_state = None
