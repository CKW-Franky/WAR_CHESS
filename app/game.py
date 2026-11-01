"""Quick-mode game shell: menu -> unit picker -> deployment -> battle.

This is the only mode shipped in the public demo.  Campaign/rogue/general/meta
modules are intentionally absent from this branch.
"""
import sys

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE, GRID_HEIGHT,
    SELECTION_SCREEN, DEPLOYMENT_STAGE, GAMEPLAY, GAME_OVER,
    AWAITING_DIRECTION, MAIN_MENU, SETTINGS, BG_COLOR, t,
)
from ui.effects import DamagePopup, VisualArrow
from ai import AIController
from ui.renderer import GameRenderer
import equipment
from battle.combat import strike_damage
from battle.setup import SetupMixin
from battle.engine import EngineMixin
from battle.actions import ActionsMixin
from battle.economy import EconomyMixin
from battle.results import ResultsMixin
from battle.input import InputMixin
from app.menu import MenuMixin
from app.selection import SelectionMixin


class Game(MenuMixin, SelectionMixin, SetupMixin, EngineMixin, ActionsMixin,
           EconomyMixin, ResultsMixin, InputMixin):
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(t("app_title"))
        self.clock = pygame.time.Clock()

        self.grid_offset_x = 8
        self.grid_offset_y = (SCREEN_HEIGHT - GRID_HEIGHT * GRID_SIZE) // 2
        self.renderer = GameRenderer(self.screen, self.grid_offset_x,
                                     self.grid_offset_y)

        self._init_ui_rects()
        self._init_battle_state()
        self.population_limit = 5
        self.enemy_mult = 100
        self.player_won = False
        self.reset_entire_game(initial=True)

    def _init_ui_rects(self):
        cx = SCREEN_WIDTH // 2

        self.lang_btn = pygame.Rect(SCREEN_WIDTH - 280, 10, 240, 32)
        self.end_turn_btn = pygame.Rect(SCREEN_WIDTH - 280,
                                        SCREEN_HEIGHT - 75, 240, 45)
        self.charge_toggle_btn = pygame.Rect(SCREEN_WIDTH - 280, 610, 240, 38)
        self.follow_up_btn = pygame.Rect(SCREEN_WIDTH - 280, 610, 240, 38)
        self.context_btn = pygame.Rect(SCREEN_WIDTH - 280, 570, 240, 38)
        self.skill_btn = pygame.Rect(SCREEN_WIDTH - 280, 655, 240, 38)
        self.split_btn = pygame.Rect(SCREEN_WIDTH - 280, 696, 240, 36)
        self.merge_btn = pygame.Rect(SCREEN_WIDTH - 280, 734, 240, 36)
        self.deploy_finish_btn = pygame.Rect(SCREEN_WIDTH - 280,
                                             SCREEN_HEIGHT - 150, 240, 50)
        self.restart_btn = pygame.Rect(self.grid_offset_x + 100,
                                       SCREEN_HEIGHT // 2 + 40, 160, 50)
        self.exit_btn = pygame.Rect(self.grid_offset_x + 300,
                                    SCREEN_HEIGHT // 2 + 40, 160, 50)

        self.menu_start_btn = pygame.Rect(cx - 150, 280, 300, 60)
        self.menu_settings_btn = pygame.Rect(cx - 150, 380, 300, 60)
        self.menu_quit_btn = pygame.Rect(cx - 150, 480, 300, 60)

        self.settings_lang_btn = pygame.Rect(cx - 150, 300, 300, 60)
        self.settings_back_btn = pygame.Rect(cx - 150, 400, 300, 60)

    def _init_battle_state(self):
        self.is_split_targeting = False
        self.is_split_facing = False
        self.split_unit = None
        self.split_pos = None

    # ------------------------------------------------------------------
    # Contextual HUD action (reload / long shot / follow-up)
    # ------------------------------------------------------------------
    def context_action(self, unit):
        if unit is None or unit.team != "player":
            return None
        weapon = unit.active_weapon
        if weapon is not None and weapon.reload_required:
            return "reload" if not unit.loaded else None
        if unit.name == "弓箭手":
            return "longshot"
        return "follow_up"

    def context_info(self, unit, action):
        if action == "reload":
            return t("ctx_reload"), t("ctx_reload_tip")
        if action == "longshot":
            if getattr(unit, "archer_longshot", False):
                return t("ctx_longshot_on"), t("ctx_longshot_tip")
            return t("ctx_longshot"), t("ctx_longshot_tip")
        return t("ctx_follow_up"), t("ctx_follow_up_tip")

    def context_enabled(self, unit, action):
        if unit is None:
            return False
        if action == "reload":
            return unit.ap >= equipment.RELOAD_AP
        if action == "longshot":
            return (not getattr(unit, "archer_longshot", False)
                    and unit.ap >= equipment.get_skill("long_shot").ap_cost)
        if action == "follow_up":
            return (not unit.has_moved
                    and not getattr(unit, "follow_up_used", False)
                    and unit.ap >= equipment.FOLLOW_UP_AP)
        return False

    def trigger_context_action(self, action):
        unit = self.active_unit
        if unit is None:
            return
        if action == "reload":
            self.reload_crossbow(unit)
        elif action == "longshot":
            unit.execute_extra_skill(self)
        elif action == "follow_up":
            self.follow_up_attack(unit)

    # ------------------------------------------------------------------
    # State reset
    # ------------------------------------------------------------------
    def reset_entire_game(self, initial=False):
        if initial:
            self.game_state = MAIN_MENU

        self.player_team_composition = []
        self.selection_ui = self.create_selection_ui()
        self.units = []
        self.selected_unit = None
        self.unit_to_face = None
        self.turn_number = 1
        self.damage_popups = []
        self.visual_arrows = []
        self.terrain_map = self.generate_terrain()
        self.is_skill_targeting = False
        self.is_split_targeting = False
        self.is_split_facing = False
        self.split_unit = None
        self.split_pos = None
        self.active_unit = None
        self.round_queue = []
        self.timeline_queue = []
        self.ai_action_queue = []
        self.last_ai_action_time = 0
        self.ai_action_delay = 500
        self.combat_log = []
        self.last_move_state = None
        self.player_won = False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        while True:
            ct = pygame.time.get_ticks()
            gs = self.game_state

            if gs == MAIN_MENU:
                self.handle_main_menu_events()
                self.renderer.draw_main_menu(self)
            elif gs == SETTINGS:
                self.handle_settings_events()
                self.renderer.draw_settings(self)
            elif gs == SELECTION_SCREEN:
                self.handle_selection_events()
                self.draw_selection_screen()
            elif gs == DEPLOYMENT_STAGE:
                self.handle_deployment_events()
                self.draw_deployment_screen()
            elif gs in (GAMEPLAY, GAME_OVER, AWAITING_DIRECTION):
                self.handle_gameplay_events()
                self._tick_gameplay(ct)
                self.draw_gameplay_screen()

            pygame.display.flip()
            self.clock.tick(60)

    def _tick_gameplay(self, now_ms):
        if self.game_state != GAMEPLAY:
            return

        if self.active_unit is None or not self.active_unit.is_alive():
            self.advance_to_next_unit()
            return

        if self.active_unit.team != "ai":
            return

        if not self.ai_action_queue and self.last_ai_action_time == 0:
            self.ai_action_queue = AIController.generate_ai_actions(
                self, self.active_unit)
            self.last_ai_action_time = now_ms
        elif self.ai_action_queue:
            if now_ms - self.last_ai_action_time >= self.ai_action_delay:
                action = self.ai_action_queue.pop(0)
                self.execute_ai_action(action)
                self.last_ai_action_time = now_ms
        else:
            AIController.set_final_facing(self, self.active_unit)
            self.end_unit_turn()

    def handle_gameplay_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_gameplay_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                self._handle_gameplay_key(event.key)

    def _handle_gameplay_key(self, key):
        if self.game_state == AWAITING_DIRECTION and key == pygame.K_ESCAPE:
            self.end_unit_turn()
            return
        if self.game_state != GAMEPLAY:
            return
        if not (self.active_unit and self.active_unit.team == "player"):
            return

        unit = self.active_unit
        if key == pygame.K_SPACE:
            self.start_facing_selection()
        elif key == pygame.K_c and unit.is_cavalry:
            self.toggle_cavalry_charge(unit)
        elif key == pygame.K_e:
            self.trigger_skill_intent(unit)
        elif key == pygame.K_t and hasattr(unit, "execute_range_skill"):
            unit.execute_range_skill(self)
        elif key == pygame.K_z:
            self.undo_move()
        elif key == pygame.K_r:
            self.reload_crossbow(unit)
        elif key == pygame.K_f:
            self.toggle_fire_arrow(unit)
        elif key == pygame.K_q:
            self.follow_up_attack(unit)
        elif key == pygame.K_ESCAPE:
            if self.is_split_targeting or self.is_split_facing:
                self._clear_split_state()
            else:
                self.is_skill_targeting = False

    def draw_gameplay_screen(self):
        self.screen.fill(BG_COLOR)
        self.renderer.draw_grid(self.terrain_map, game=self)

        if self.game_state == AWAITING_DIRECTION:
            self.renderer.draw_facing_highlights(self)
        else:
            self.renderer.draw_highlights(self)

        self.renderer.draw_attack_range_outlines(self)
        self.renderer.draw_units(self.units, self.active_unit,
                                 self.selected_unit)
        self.renderer.draw_visual_arrows(self.visual_arrows)
        self.renderer.draw_damage_predictions(self)
        self.renderer.draw_damage_popups(self.damage_popups)
        self.renderer.draw_hint_bar(self)
        self.renderer.draw_info_panel(self)
        self.renderer.draw_hover_tooltip(self)

        if self.game_state == GAME_OVER:
            self.renderer.draw_game_over_modal(self)

    def trigger_visual_arrow(self, start, end, is_skill=False):
        self.visual_arrows.append(VisualArrow(start, end, is_skill=is_skill))

    def add_damage_popup(self, text, gx, gy, is_crit=False, is_miss=False,
                         is_wet=False):
        px = self.grid_offset_x + gx * GRID_SIZE + GRID_SIZE // 2
        py = self.grid_offset_y + gy * GRID_SIZE + 15
        if is_miss:
            color = (100, 200, 255)
        elif is_wet:
            color = (0, 190, 255)
        elif is_crit:
            color = (255, 215, 0)
        else:
            color = (255, 80, 80)
        self.damage_popups.append(DamagePopup(text, px, py, color))

    def skill_strike(self, attacker, defender):
        return strike_damage(attacker, defender, self)
