import sys
import heapq
import random

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE, GRID_WIDTH, GRID_HEIGHT,
    CHARGE_TOGGLE_AP, WHITE, GRID_COLOR, PLAYER_COLOR, AI_COLOR,
    DEPLOY_HIGHLIGHT_COLOR, SELECTED_COLOR, TEXT_COLOR, BG_COLOR,
    INFO_PANEL_COLOR, BUTTON_COLOR, BUTTON_HOVER_COLOR, BUTTON_DISABLED_COLOR,
    SELECTION_SCREEN, DEPLOYMENT_STAGE, GAMEPLAY, GAME_OVER, AWAITING_DIRECTION,
    MAIN_MENU, SETTINGS, MODE_SELECT, ROGUE_MAP, EVENT_SCREEN, ROGUE_SHOP,
    ROGUE_REST, ROSTER_SCREEN, SIEGE_REWARD, CAPTIVE_SCREEN, WAR_TEMPLE, META_SCREEN,
    GENERAL_SELECT, CAMPAIGN_PATH_SELECT, SLOT_SELECT,
    DamagePopup, VisualArrow, t, toggle_language,
)
from units import create_unit, UNIT_CATALOG
from ai import AIController
from renderer import GameRenderer
from campaign import CampaignState, get_star_bonus, get_mechanics
from rogue import (NODE_COMBAT, NODE_ELITE, NODE_SHOP, NODE_REST,
                   NODE_EVENT, NODE_SIEGE, NODE_BOSS,
                   ROGUE_SHOP_ITEMS, pick_rewards)
from general import (General, STATUS_ACTIVE, STATUS_DEAD, STAT_NAMES,
                     WarTemple, save_temple)
from meta import META, reload_meta
from save import (set_slot, slot_exists, delete_slot,
                  load_slot_summary, load_temple as load_temple_save,
                  load_campaign as load_campaign_save,
                  save_campaign as save_campaign_data)
from combat import (DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT,
                    calculate_combat_result, get_zoc_tiles)


def terrain_move_extra(terrain, is_cavalry=False):
    if terrain in ("FENCE", "WALL", "HOUSE", "GATE"):
        return None
    if terrain == "RIVER":
        return 1 if is_cavalry else 2
    if terrain == "ROAD":
        return -1
    if terrain in ("SWAMP", "VILLAGE", "RUINS"):
        return 1
    return 0


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(t("app_title"))
        self.clock = pygame.time.Clock()

        self.grid_offset_x = 8
        self.grid_offset_y = (SCREEN_HEIGHT - GRID_HEIGHT * GRID_SIZE) // 2
        self.renderer = GameRenderer(self.screen, self.grid_offset_x, self.grid_offset_y)

        self._init_ui_rects()
        self._init_rogue_state()
        self._init_general_state()
        self._init_captive_state()
        self._init_temple_and_meta_state()
        self._init_path_and_slot_state()

        self.game_mode = "quick"
        self.campaign_state = CampaignState()
        self.population_limit = 5
        self.enemy_mult = 100
        self.campaign_win = False
        self.quest_result_msg = ""
        self._quest_enemy_count = 3
        self._quest_enemy_pool = None
        self._is_siege_node = False
        self._siege_is_boss = False
        self.general_reward_given = False
        self.selecting_initial_roster = False

        set_slot(1)
        reload_meta(1)

        self.reset_entire_game(initial=True)

    def _init_ui_rects(self):
        cx = SCREEN_WIDTH // 2

        self.lang_btn = pygame.Rect(SCREEN_WIDTH - 280, 10, 240, 32)
        self.end_turn_btn = pygame.Rect(SCREEN_WIDTH - 280, SCREEN_HEIGHT - 75, 240, 45)
        self.charge_toggle_btn = pygame.Rect(SCREEN_WIDTH - 280, 610, 240, 38)
        self.catapult_btn = pygame.Rect(SCREEN_WIDTH - 280, 570, 240, 38)
        self.skill_btn = pygame.Rect(SCREEN_WIDTH - 280, 655, 240, 38)
        self.split_btn = pygame.Rect(SCREEN_WIDTH - 280, 696, 240, 36)
        self.merge_btn = pygame.Rect(SCREEN_WIDTH - 280, 734, 240, 36)
        self.deploy_finish_btn = pygame.Rect(SCREEN_WIDTH - 280, SCREEN_HEIGHT - 150, 240, 50)
        self.restart_btn = pygame.Rect(self.grid_offset_x + 100, SCREEN_HEIGHT // 2 + 40, 160, 50)
        self.exit_btn = pygame.Rect(self.grid_offset_x + 300, SCREEN_HEIGHT // 2 + 40, 160, 50)

        self.menu_start_btn = pygame.Rect(cx - 150, 250, 300, 60)
        self.menu_temple_btn = pygame.Rect(cx - 150, 330, 300, 60)
        self.menu_meta_btn = pygame.Rect(cx - 150, 410, 300, 60)
        self.menu_settings_btn = pygame.Rect(cx - 150, 490, 300, 60)
        self.menu_quit_btn = pygame.Rect(cx - 150, 570, 300, 60)

        self.mode_quick_btn = pygame.Rect(cx - 400, 300, 350, 220)
        self.mode_campaign_btn = pygame.Rect(cx + 50, 300, 350, 220)
        self.mode_back_btn = pygame.Rect(cx - 100, 620, 200, 55)

        self.settings_lang_btn = pygame.Rect(cx - 150, 300, 300, 60)
        self.settings_back_btn = pygame.Rect(cx - 150, 400, 300, 60)

    def _init_rogue_state(self):
        self.rogue_node_rects = []
        self.rogue_event_option_rects = []
        self.rogue_shop_rects = []
        self.rogue_rest_rects = []
        self.siege_reward_rects = []
        self.current_event = None
        self.event_result_msg = ""
        self.pending_siege_buffs = []
        self.pending_siege_is_boss = False
        self.shop_back_btn = pygame.Rect(30, 30, 150, 50)
        self.roster_unit_rects = []
        self.roster_recruit_rects = []
        self.roster_back_btn = pygame.Rect(30, 30, 150, 50)
        self.roster_map_btn = pygame.Rect(SCREEN_WIDTH - 200, SCREEN_HEIGHT - 80, 160, 45)
        self.is_split_targeting = False
        self.is_split_facing = False
        self.split_unit = None
        self.split_pos = None

    def _init_general_state(self):
        self.general_appoint_btn = pygame.Rect(SCREEN_WIDTH - 280, 700, 240, 36)
        self.general_assign_list_rects = []
        self.is_choosing_general = False
        self.general_msg = ""
        self.general_saved = False
        self.general_save_btn = pygame.Rect(SCREEN_WIDTH - 280, 745, 240, 40)
        self.general_select_cards = []
        cx = SCREEN_WIDTH // 2
        self.general_select_confirm_btn = pygame.Rect(cx - 100, 720, 200, 60)
        self.general_select_new_btn = pygame.Rect(cx - 320, 720, 200, 60)
        self.general_select_pick = None
        self.general_recruit_used = False

    def _init_captive_state(self):
        cx = SCREEN_WIDTH // 2
        self.captive_accept_btn = pygame.Rect(cx - 240, 520, 200, 60)
        self.captive_refuse_btn = pygame.Rect(cx + 40, 520, 200, 60)
        self.captive_general = None
        self.pending_captive = None

    def _init_temple_and_meta_state(self):
        self.war_temple_back_btn = pygame.Rect(30, 30, 150, 50)
        self.war_temple_tabs = []
        self.war_temple_tab = "main"
        self.war_temple_cards = []

        self.meta_tab = "skills"
        self.meta_tab_buttons = []
        self.meta_skill_rects = []
        self.meta_back_btn = pygame.Rect(30, 30, 150, 50)

    def _init_path_and_slot_state(self):
        cx = SCREEN_WIDTH // 2
        self.path_select_A_btn = pygame.Rect(cx - 380, 280, 320, 260)
        self.path_select_B_btn = pygame.Rect(cx + 60, 280, 320, 260)
        self.path_choice_name = None
        self.path_choice_queue = []
        self.pending_level = None

        self.slot_select_back_btn = pygame.Rect(30, 30, 150, 50)
        self.slot_cards = []
        self.current_slot = 1
        self.pending_delete_slot = None
        self.slot_delete_yes_btn = pygame.Rect(cx - 220, 480, 200, 60)
        self.slot_delete_no_btn = pygame.Rect(cx + 20, 480, 200, 60)

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
        self.terrain_map = (self.generate_siege_terrain() if self._is_siege_node
                            else self.generate_terrain())
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
        self.campaign_win = False
        self.general_msg = ""
        self.general_saved = False
        self.general_reward_given = False


    def _save_campaign(self):
        if self.game_mode not in ("campaign", "rogue"):
            return
        try:
            save_campaign_data(self.campaign_state.to_dict())
        except OSError as e:
            print(f"[Auto Save] {e}")

    def _save_temple(self):
        try:
            if hasattr(self.campaign_state, "war_temple"):
                self.campaign_state.war_temple.save()
        except OSError as e:
            print(f"[Temple Save] {e}")


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
            elif gs == SLOT_SELECT:
                self.handle_slot_select_events()
                self.renderer.draw_slot_select(self)
            elif gs == MODE_SELECT:
                self.handle_mode_select_events()
                self.renderer.draw_mode_select(self)
            elif gs == WAR_TEMPLE:
                self.handle_war_temple_events()
                self.renderer.draw_war_temple(self)
            elif gs == META_SCREEN:
                self.handle_meta_screen_events()
                self.renderer.draw_meta_screen(self)
            elif gs == GENERAL_SELECT:
                self.handle_general_select_events()
                self.renderer.draw_general_select(self)
            elif gs == ROGUE_MAP:
                self.handle_rogue_map_events()
                self.renderer.draw_rogue_map(self)
            elif gs == EVENT_SCREEN:
                self.handle_event_screen_events()
                self.renderer.draw_event_screen(self)
            elif gs == ROGUE_SHOP:
                self.handle_rogue_shop_events()
                self.renderer.draw_rogue_shop(self)
            elif gs == ROGUE_REST:
                self.handle_rogue_rest_events()
                self.renderer.draw_rest_screen(self)
            elif gs == ROSTER_SCREEN:
                self.handle_roster_screen_events()
                self.renderer.draw_roster_screen(self)
            elif gs == SIEGE_REWARD:
                self.handle_siege_reward_events()
                self.renderer.draw_siege_reward(self)
            elif gs == CAPTIVE_SCREEN:
                self.handle_captive_events()
                self.renderer.draw_captive_screen(self)
            elif gs == CAMPAIGN_PATH_SELECT:
                self.handle_path_select_events()
                self.renderer.draw_path_select(self)
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
            self.ai_action_queue = AIController.generate_ai_actions(self, self.active_unit)
            self.last_ai_action_time = now_ms
        elif self.ai_action_queue:
            if now_ms - self.last_ai_action_time >= self.ai_action_delay:
                action = self.ai_action_queue.pop(0)
                self.execute_ai_action(action)
                self.last_ai_action_time = now_ms
        else:
            AIController.set_final_facing(self, self.active_unit)
            self.end_unit_turn()

    def handle_main_menu_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.menu_start_btn.collidepoint(event.pos):
                    self.game_state = SLOT_SELECT
                elif self.menu_temple_btn.collidepoint(event.pos):
                    self.game_state = WAR_TEMPLE
                elif self.menu_meta_btn.collidepoint(event.pos):
                    self.game_state = META_SCREEN
                elif self.menu_settings_btn.collidepoint(event.pos):
                    self.game_state = SETTINGS
                elif self.menu_quit_btn.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

    def handle_settings_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.settings_lang_btn.collidepoint(event.pos):
                    toggle_language()
                elif self.settings_back_btn.collidepoint(event.pos):
                    self.game_state = MAIN_MENU


    def handle_slot_select_events(self):
        if self.pending_delete_slot is not None:
            self._handle_delete_confirm_events()
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            pos = event.pos
            if self.slot_select_back_btn.collidepoint(pos):
                self.game_state = MAIN_MENU
                return
            for card in self.slot_cards:
                slot_id = card["slot_id"]
                has_save = card["summary"] is not None
                if card["enter_btn"].collidepoint(pos):
                    self._enter_slot(slot_id)
                    return
                if has_save and card["delete_btn"].collidepoint(pos):
                    self.pending_delete_slot = slot_id
                    return

    def _handle_delete_confirm_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.slot_delete_yes_btn.collidepoint(event.pos):
                    delete_slot(self.pending_delete_slot)
                    self.pending_delete_slot = None
                elif self.slot_delete_no_btn.collidepoint(event.pos):
                    self.pending_delete_slot = None

    def _enter_slot(self, slot_id):
        set_slot(slot_id)
        reload_meta(slot_id)
        self.current_slot = slot_id

        temple_data = load_temple_save()
        self.campaign_state.war_temple = (
            WarTemple.from_dict(temple_data) if temple_data else WarTemple()
        )

        if not slot_exists(slot_id):
            self.game_state = MODE_SELECT
            return

        campaign_data = load_campaign_save()
        if not campaign_data:
            self.game_state = MODE_SELECT
            return

        self.campaign_state = CampaignState.from_dict(campaign_data)
        self.campaign_state.war_temple = (
            WarTemple.from_dict(temple_data) if temple_data else WarTemple()
        )

        if not self.campaign_state.current_generals:
            available = self.campaign_state.war_temple.get_active()[:3]
            for g in available:
                if g in self.campaign_state.war_temple.main_hall:
                    self.campaign_state.war_temple.main_hall.remove(g)
            self.campaign_state.current_generals = list(available)
            self.campaign_state.war_temple.save()
            self._save_campaign()

        self.game_mode = "campaign"
        self.game_state = ROGUE_MAP

    def handle_mode_select_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if self.mode_quick_btn.collidepoint(event.pos):
                self._start_quick_mode()
            elif self.mode_campaign_btn.collidepoint(event.pos):
                self._start_campaign_mode()
            elif self.mode_back_btn.collidepoint(event.pos):
                self.game_state = MAIN_MENU

    def _start_quick_mode(self):
        self.game_mode = "quick"
        self.population_limit = 5 + int(META.get_effect_value("extra_population"))
        self.enemy_mult = 100
        self.campaign_state = CampaignState()
        self.selecting_initial_roster = False
        self.reset_entire_game()
        self.game_state = SELECTION_SCREEN

    def _start_campaign_mode(self):
        self.game_mode = "campaign"
        self.campaign_state = CampaignState()
        self.campaign_state.war_temple.advance_mourning()
        self.campaign_state.war_temple.save()
        self.campaign_state.generate_rogue_map()
        self.campaign_state.gold += int(META.get_effect_value("starting_gold"))
        self._save_campaign()
        self._start_initial_roster_selection()

    def _start_initial_roster_selection(self):
        self.population_limit = 3
        self.selecting_initial_roster = True
        self.reset_entire_game()
        self.game_state = SELECTION_SCREEN

    def _enter_general_select(self):
        self.general_select_pick = None
        self.general_msg = ""
        self.general_recruit_used = False
        self.game_state = GENERAL_SELECT

    def handle_general_select_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            pos = event.pos
            wt = self.campaign_state.war_temple

            for rect, g in self.general_select_cards:
                if rect.collidepoint(pos):
                    self.general_select_pick = g
                    return

            if self.general_select_new_btn.collidepoint(pos):
                self._recruit_general(wt)
                return

            if self.general_select_confirm_btn.collidepoint(pos):
                self._confirm_general_select(wt)

    def _recruit_general(self, war_temple):
        if self.general_recruit_used:
            self.general_msg = "本局招募機會已用完"
            return
        new_general = General()
        war_temple.add_new(new_general)
        war_temple.save()
        self.general_recruit_used = True
        self.general_msg = t("general_generated", name=new_general.name)

    def _confirm_general_select(self, war_temple):
        if not self.general_select_pick:
            return
        war_temple.main_hall = [
            g for g in war_temple.main_hall
            if g.name != self.general_select_pick.name
        ]
        war_temple.save()
        self.campaign_state.current_generals = [self.general_select_pick]
        self._save_campaign()
        self.game_state = ROGUE_MAP

    def handle_rogue_map_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if self.roster_map_btn.collidepoint(event.pos):
                self.game_state = ROSTER_SCREEN
                return

            cs = self.campaign_state
            for rect, node in self.rogue_node_rects:
                if not rect.collidepoint(event.pos):
                    continue
                if node.completed:
                    return
                if node.layer != cs.get_available_layer():
                    return
                self._enter_node(node)
                return

    def _enter_node(self, node):
        cs = self.campaign_state
        cs.last_node = node
        node_type = node.node_type

        if node_type in (NODE_COMBAT, NODE_ELITE):
            self._start_node_battle(node)
        elif node_type in (NODE_SIEGE, NODE_BOSS):
            self._start_siege(node)
        elif node_type == NODE_EVENT:
            self.current_event = cs.roll_event()
            self.event_result_msg = ""
            self.game_state = EVENT_SCREEN
        elif node_type == NODE_SHOP:
            self.quest_result_msg = ""
            self.game_state = ROGUE_SHOP
        elif node_type == NODE_REST:
            self.game_state = ROGUE_REST

    def _start_node_battle(self, node):
        cs = self.campaign_state
        data = node.data
        self.game_mode = "rogue"
        self.population_limit = cs.population + int(META.get_effect_value("extra_population"))
        self.enemy_mult = data["enemy_mult"]
        self._quest_enemy_count = data["enemy_count"]
        self._quest_enemy_pool = data.get("enemy_pool")
        self._is_siege_node = False
        self._save_campaign()

        if not cs.roster:
            self.quest_result_msg = "部隊已全滅，無法出征"
            self.game_state = ROGUE_MAP
            return

        pending = cs.pending_path_names()
        if pending:
            self.path_choice_queue = list(pending[1:])
            self.path_choice_name = pending[0]
            self.pending_level = ("rogue", None)
            self.game_state = CAMPAIGN_PATH_SELECT
            return

        self._begin_roster_battle()

    def _start_siege(self, node):
        cs = self.campaign_state
        data = node.data
        self.game_mode = "rogue"
        self.population_limit = cs.population + int(META.get_effect_value("extra_population"))
        self.enemy_mult = data["enemy_mult"]
        self._quest_enemy_count = data["enemy_count"]
        self._quest_enemy_pool = data.get("enemy_pool")
        self._is_siege_node = True
        self._siege_is_boss = data.get("is_boss", False)
        self._save_campaign()

        if not cs.roster:
            self.quest_result_msg = "部隊已全滅，無法出征"
            self.game_state = ROGUE_MAP
            return

        pending = cs.pending_path_names()
        if pending:
            self.path_choice_queue = list(pending[1:])
            self.path_choice_name = pending[0]
            self.pending_level = ("rogue", None)
            self.game_state = CAMPAIGN_PATH_SELECT
            return

        self._begin_roster_battle()

    def _begin_roster_battle(self):
        self.reset_entire_game()
        self.campaign_state.clear_assignments()
        self._setup_roster_units()
        self._setup_ai_units()
        self._apply_pending_buffs()
        self.game_state = DEPLOYMENT_STAGE

    def handle_event_screen_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if self.event_result_msg:
                self.event_result_msg = ""
                self.current_event = None
                self.campaign_state.complete_current_node()
                self._save_campaign()
                self.game_state = ROGUE_MAP
                return

            for rect, opt in self.rogue_event_option_rects:
                if rect.collidepoint(event.pos):
                    self._apply_event_option(opt)
                    return

    def _apply_event_option(self, opt):
        cs = self.campaign_state
        effect = opt["effect"]
        value = opt.get("value", 0)

        if effect == "none":
            msg = "你選擇離開"
        elif effect == "morale":
            cs.add_buff("morale_buff", value)
            msg = f"+{value} 士氣"
        elif effect == "exp":
            cs.add_exp_all(value)
            msg = f"全隊 +{value} 經驗"
        elif effect == "gold":
            cs.add_gold(value)
            msg = f"+{value} 金"
        elif effect == "altar_blood":
            cs.add_buff("atk_buff", value)
            cs.add_buff("morale_penalty", 20)
            msg = f"+{value}% ATK, -20 士氣"
        elif effect == "hire_knight":
            if cs.spend_gold(80):
                cs.add_exp_all(50)
                msg = "+50 經驗"
            else:
                msg = "金幣不足"
        elif effect == "help_plague":
            if cs.spend_gold(50):
                cs.add_exp_all(value)
                msg = f"全隊 +{value} 經驗"
            else:
                msg = "金幣不足"
        elif effect == "loot_plague":
            cs.add_gold(value)
            cs.add_buff("morale_penalty", 20)
            msg = f"+{value} 金, -20 士氣"
        elif effect == "search_caravan":
            gold = random.randint(30, 150)
            cs.add_gold(gold)
            msg = f"+{gold} 金"
        elif effect == "buy_potion":
            if cs.spend_gold(60):
                cs.add_buff("heal_buff", value)
                msg = f"下場 +{value}% HP"
            else:
                msg = "金幣不足"
        elif effect == "witch_curse":
            cs.add_buff("atk_buff", value)
            cs.add_buff("morale_penalty", 20)
            msg = f"+{value}% ATK, -20 士氣"
        elif effect == "open_chest":
            if random.random() < 0.5:
                gold = random.randint(50, 200)
                cs.add_gold(gold)
                msg = f"寶箱: +{gold} 金"
            else:
                cs.add_exp_all(100)
                msg = "寶箱: 全隊 +100 經驗"
        else:
            msg = ""

        self.event_result_msg = msg

    def handle_rogue_shop_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if self.shop_back_btn.collidepoint(event.pos):
                self.campaign_state.complete_current_node()
                self._save_campaign()
                self.game_state = ROGUE_MAP
                return

            for rect, key in self.rogue_shop_rects:
                if rect.collidepoint(event.pos):
                    self._buy_rogue_item(key)
                    return

    def _buy_rogue_item(self, key):
        cs = self.campaign_state
        item = ROGUE_SHOP_ITEMS[key]
        cost = cs.get_shop_cost(item["cost"])
        if not cs.spend_gold(cost):
            self.quest_result_msg = "金幣不足"
            return

        effect = item["effect"]
        value = item["value"]
        if effect == "exp":
            cs.add_exp_all(value)
        elif effect in ("permanent_atk", "permanent_def"):
            cs.apply_permanent_buff({"effect": effect, "value": value})
        else:
            cs.add_buff(effect, value)
        self.quest_result_msg = f"已購買 {item['name']}"

    def handle_rogue_rest_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue
            for rect, action in self.rogue_rest_rects:
                if rect.collidepoint(event.pos):
                    self._apply_rest_action(action)
                    return

    def _apply_rest_action(self, action):
        cs = self.campaign_state
        if action == "heal":
            cs.add_buff("morale_buff", 30)
        elif action == "train":
            cs.add_exp_all(80)
        elif action == "gold":
            cs.add_gold(40)
        cs.complete_current_node()
        self._save_campaign()
        self.game_state = ROGUE_MAP

    def handle_roster_screen_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            pos = event.pos
            if self.roster_back_btn.collidepoint(pos):
                self.game_state = ROGUE_MAP
                return
            for rect, idx in self.roster_unit_rects:
                if rect.collidepoint(pos):
                    self._try_reinforce(idx)
                    return
            for rect, name in self.roster_recruit_rects:
                if rect.collidepoint(pos):
                    self._try_recruit_unit(name)
                    return

    def _try_reinforce(self, index):
        cs = self.campaign_state
        cost = 50
        if cs.gold < cost:
            self.quest_result_msg = "金幣不足"
            return
        gained = cs.reinforce_unit(index, 50)
        if gained > 0:
            cs.spend_gold(cost)
            self.quest_result_msg = f"補充 {gained} 兵力"
        else:
            self.quest_result_msg = "已滿員"
        self._save_campaign()

    def _try_recruit_unit(self, name):
        cs = self.campaign_state
        cost = 100
        if cs.gold < cost:
            self.quest_result_msg = "金幣不足"
            return
        if cs.recruit_unit_to_roster(name):
            cs.spend_gold(cost)
            self.quest_result_msg = f"招募 {name}"
        else:
            self.quest_result_msg = "人口已滿或未解鎖"
        self._save_campaign()

    def handle_siege_reward_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            for rect, buff in self.siege_reward_rects:
                if rect.collidepoint(event.pos):
                    self._apply_siege_reward(buff)
                    return

    def _apply_siege_reward(self, buff):
        cs = self.campaign_state
        cs.apply_permanent_buff(buff)
        cs.complete_current_node()
        META.stats["siege_wins"] = META.stats.get("siege_wins", 0) + 1
        if buff.get("effect") != "permanent_population":
            cs.population_bonus += 1
        META.add_soul(30 if not self.pending_siege_is_boss else 100)
        META.save()
        self.pending_siege_buffs = []

        if self.pending_captive:
            self.captive_general = self.pending_captive
            self.pending_captive = None
            self.game_state = CAPTIVE_SCREEN
            return

        self._after_siege_reward()

    def _after_siege_reward(self):

        if not self.pending_siege_is_boss:
            self._save_campaign()
            self.game_state = ROGUE_MAP
            return

        cs = self.campaign_state
        if not cs.is_map_complete():
            self._save_campaign()
            self.game_state = ROGUE_MAP
            return

        if cs.next_act():
            META.record_act_clear()
            META.save()
            self._save_campaign()
            self.game_state = ROGUE_MAP
            return

        META.stats["campaign_clears"] = META.stats.get("campaign_clears", 0) + 1
        META.record_act_clear()
        META.ascension_level += 1
        META.save()
        cs.act = 1
        cs.generate_rogue_map()
        self._save_campaign()
        self.game_state = ROGUE_MAP

    def handle_captive_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if self.captive_accept_btn.collidepoint(event.pos):
                self._try_recruit_captive()
                return
            if self.captive_refuse_btn.collidepoint(event.pos):
                self.captive_general = None
                self._save_campaign()
                self.game_state = GAME_OVER
                return

    def _try_recruit_captive(self):
        g = self.captive_general
        cs = self.campaign_state
        if not g:
            self.game_state = GAME_OVER
            return

        cost = 100 + g.loyalty
        if cs.gold < cost:
            self.general_msg = t("captive_gold_lack")
            self.captive_general = None
            self._save_campaign()
            self.game_state = GAME_OVER
            return

        cs.spend_gold(cost)
        chance = max(10, min(90, 70 - g.loyalty))
        if random.random() * 100 < chance:
            g.status = STATUS_ACTIVE
            cs.add_general(g)
            self.general_msg = t("captive_success", name=g.name)
        else:
            self.general_msg = t("captive_fail", name=g.name)

        self.captive_general = None
        self._save_campaign()
        self.game_state = GAME_OVER

    def handle_path_select_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            name = self.path_choice_name
            if not name:
                return

            if self.path_select_A_btn.collidepoint(event.pos):
                self.campaign_state.set_path(name, "A")
                self._advance_path_choice()
            elif self.path_select_B_btn.collidepoint(event.pos):
                self.campaign_state.set_path(name, "B")
                self._advance_path_choice()

    def _advance_path_choice(self):
        if self.path_choice_queue:
            self.path_choice_name = self.path_choice_queue.pop(0)
            return

        self.path_choice_name = None
        self.pending_level = None
        self.reset_entire_game()
        self.game_state = SELECTION_SCREEN


    def handle_war_temple_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            if self.war_temple_back_btn.collidepoint(event.pos):
                self.game_state = MAIN_MENU
                return
            for rect, key in self.war_temple_tabs:
                if rect.collidepoint(event.pos):
                    self.war_temple_tab = key
                    return

    def handle_meta_screen_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            pos = event.pos
            if self.meta_back_btn.collidepoint(pos):
                self.game_state = MAIN_MENU
                return
            for rect, key in self.meta_tab_buttons:
                if rect.collidepoint(pos):
                    self.meta_tab = key
                    return
            if self.meta_tab == "skills":
                for rect, sid in self.meta_skill_rects:
                    if rect.collidepoint(pos):
                        if META.upgrade_skill(sid):
                            META.save()
                        return

    def handle_selection_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            pos = event.pos
            if self.lang_btn.collidepoint(pos):
                toggle_language()
                return

            for card in self.selection_ui["pool_cards"]:
                if card["button"].collidepoint(pos):
                    self._try_add_unit(card["name"])

            for i, slot in enumerate(self.selection_ui["team_slots"]):
                if i >= self.population_limit:
                    break
                if slot["rect"].collidepoint(pos) and i < len(self.player_team_composition):
                    self.player_team_composition.pop(i)
                    break

            if self.selection_ui["start_button"].collidepoint(pos):
                if len(self.player_team_composition) == self.population_limit:
                    if self.selecting_initial_roster:
                        self._finish_initial_roster_selection()
                    else:
                        self.setup_initial_units(self.player_team_composition)
                        self.game_state = DEPLOYMENT_STAGE

    def _try_add_unit(self, name):
        if len(self.player_team_composition) >= self.population_limit:
            return
        if self.game_mode in ("campaign", "rogue") and not self.campaign_state.is_unlocked_unit(name):
            return
        self.player_team_composition.append(name)

    def _finish_initial_roster_selection(self):
        cs = self.campaign_state
        cs.clear_roster()
        for name in self.player_team_composition:
            cs.recruit_unit_to_roster(name)
        self.selecting_initial_roster = False
        self._save_campaign()
        self._enter_general_select()

    def handle_deployment_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            pos = event.pos
            if self.lang_btn.collidepoint(pos):
                toggle_language()
                return

            if self.is_choosing_general:
                self._handle_general_choose_click(pos)
                return

            if self.campaign_state.current_generals and \
                    self.general_appoint_btn.collidepoint(pos):
                self._open_general_list()
                return

            if self.deploy_finish_btn.collidepoint(pos):
                self.game_state = GAMEPLAY
                self.selected_unit = None
                return

            self._handle_deploy_grid_click(pos)

    def _handle_general_choose_click(self, pos):
        for rect, g in self.general_assign_list_rects:
            if rect.collidepoint(pos):
                self._do_assign_general(g)
                return
        self.is_choosing_general = False

    def _handle_deploy_grid_click(self, pos):
        gx = (pos[0] - self.grid_offset_x) // GRID_SIZE
        gy = (pos[1] - self.grid_offset_y) // GRID_SIZE
        clicked = self.get_unit_at(gx, gy)

        if clicked and clicked.team == "player":
            self.selected_unit = clicked
            return

        if self.selected_unit and not clicked:
            if 0 <= gx < GRID_WIDTH and 16 <= gy <= 19:
                self.selected_unit.x, self.selected_unit.y = gx, gy
                self.selected_unit.set_facing(DIR_UP)
                self.selected_unit = None

    def _open_general_list(self):
        if not self.selected_unit or self.selected_unit.team != "player":
            self.general_msg = t("general_no_selected")
            return
        if not self.campaign_state.get_available_generals():
            self.general_msg = t("general_no_available")
            return
        self.is_choosing_general = True

    def _do_assign_general(self, g):
        cs = self.campaign_state
        unit = self.selected_unit
        if not unit:
            self.is_choosing_general = False
            return

        if unit.is_general and unit.general_name in cs.general_assignments:
            del cs.general_assignments[unit.general_name]

        cs.assign_general(g, unit)
        root = self._squad_root(unit)
        uid = getattr(root, "roster_uid", None)
        if uid is not None:
            cs.general_roster_slots[g.name] = uid
        self.general_msg = t("general_appointed", name=g.name)
        self.is_choosing_general = False

    def handle_gameplay_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_gameplay_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                self._handle_gameplay_key(event.key)

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
        elif key == pygame.K_z:
            self.undo_move()
        elif key == pygame.K_ESCAPE:
            if self.is_split_targeting or self.is_split_facing:
                self._clear_split_state()
            else:
                self.is_skill_targeting = False

    def _handle_game_over_click(self, pos):
        if self.general_save_btn.collidepoint(pos):
            self._save_to_war_temple()
            return

        if self.game_mode in ("rogue", "campaign"):
            self._save_campaign()
            self.game_state = ROGUE_MAP
            return

        if self.restart_btn.collidepoint(pos):
            self._start_quick_mode()
        elif self.exit_btn.collidepoint(pos):
            self.game_state = MAIN_MENU

    def _save_to_war_temple(self):
        if self.general_saved:
            return
        cs = self.campaign_state
        if not cs.current_generals:
            return
        wt = cs.war_temple
        survivors = []
        for g in cs.current_generals:
            survived = g.status != STATUS_DEAD
            if g.name in cs.general_assignments:
                unit = cs.general_assignments[g.name]
                if not unit.is_alive():
                    survived = False
                    g.status = STATUS_DEAD
            became_fame = (g.rank >= 3 and g.revive_count >= 3)
            if not survived or became_fame:
                wt.on_battle_end(g, survived, became_fame)
            else:
                survivors.append(g)
        cs.current_generals = survivors
        alive = {g.name for g in cs.current_generals}
        cs.general_roster_slots = {n: u for n, u in cs.general_roster_slots.items()
                                   if n in alive}

        wt.save()
        self.general_saved = True
        self.general_msg = t("general_saved")
        self._save_campaign()

    def draw_selection_screen(self):
        self.screen.fill(BG_COLOR)
        self.renderer.draw_language_button(self.lang_btn)

        title = self.renderer.big_font.render(t("select_title"), True, TEXT_COLOR)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 35))
        pop = self.renderer.font.render(f"人口: {self.population_limit}",
                                        True, SELECTED_COLOR)
        self.screen.blit(pop, (SCREEN_WIDTH // 2 - pop.get_width() // 2, 75))

        for card in self.selection_ui["pool_cards"]:
            self._draw_unit_pool_card(card)

        for i, slot in enumerate(self.selection_ui["team_slots"]):
            self._draw_team_slot(slot, i)

        self._draw_start_button()

    def _draw_unit_pool_card(self, card):
        unlocked = True
        if self.game_mode in ("campaign", "rogue"):
            unlocked = self.campaign_state.is_unlocked_unit(card["name"])

        bg = INFO_PANEL_COLOR if unlocked else (30, 30, 35)
        border = PLAYER_COLOR if unlocked else (60, 60, 60)
        pygame.draw.rect(self.screen, bg, card["rect"], border_radius=8)
        pygame.draw.rect(self.screen, border, card["rect"], 2, border_radius=8)

        name_color = WHITE if unlocked else (100, 100, 100)
        self.screen.blit(
            self.renderer.font.render(t(f"unit_{card['name']}"), True, name_color),
            (card["rect"].x + 15, card["rect"].y + 10))

        star = (self.campaign_state.get_star(card["name"])
                if self.game_mode in ("campaign", "rogue") else 0)
        stars = "★" * star + "☆" * (5 - star)
        self.screen.blit(
            self.renderer.small_font.render(stars, True, (255, 220, 50)),
            (card["rect"].right - 100, card["rect"].y + 12))

        stats = card["stats"]
        stat_text = f"HP:{stats['hp']} ATK:{stats['attack']} DEF:{stats['defense']}"
        stat_color = GRID_COLOR if unlocked else (80, 80, 80)
        self.screen.blit(
            self.renderer.small_font.render(stat_text, True, stat_color),
            (card["rect"].x + 15, card["rect"].y + 40))

        full = len(self.player_team_composition) >= self.population_limit
        if full or not unlocked:
            btn_color = BUTTON_DISABLED_COLOR
        elif card["button"].collidepoint(pygame.mouse.get_pos()):
            btn_color = BUTTON_HOVER_COLOR
        else:
            btn_color = BUTTON_COLOR
        pygame.draw.rect(self.screen, btn_color, card["button"], border_radius=6)
        add = self.renderer.font.render(t("add_btn"), True, WHITE)
        self.screen.blit(add, add.get_rect(center=card["button"].center))

    def _draw_team_slot(self, slot, index):
        if index >= self.population_limit:
            pygame.draw.rect(self.screen, (20, 20, 25), slot["rect"], border_radius=8)
            lock = self.renderer.font.render("未解鎖", True, (80, 80, 80))
            self.screen.blit(lock, lock.get_rect(center=slot["rect"].center))
            return

        pygame.draw.rect(self.screen, INFO_PANEL_COLOR, slot["rect"], border_radius=8)
        if index < len(self.player_team_composition):
            label = t(f"unit_{self.player_team_composition[index]}")
            color = WHITE
        else:
            label = t("empty_slot", idx=index + 1)
            color = GRID_COLOR
        rendered = self.renderer.font.render(label, True, color)
        self.screen.blit(rendered, rendered.get_rect(center=slot["rect"].center))

    def _draw_start_button(self):
        ready = len(self.player_team_composition) == self.population_limit
        btn = self.selection_ui["start_button"]
        if ready and btn.collidepoint(pygame.mouse.get_pos()):
            color = BUTTON_HOVER_COLOR
        elif ready:
            color = BUTTON_COLOR
        else:
            color = BUTTON_DISABLED_COLOR
        pygame.draw.rect(self.screen, color, btn, border_radius=8)

        if ready:
            label = t("ready_start")
        else:
            label = f"已選 {len(self.player_team_composition)}/{self.population_limit}"
        sf = self.renderer.big_font.render(label, True, WHITE)
        self.screen.blit(sf, sf.get_rect(center=btn.center))

    def draw_deployment_screen(self):
        self.screen.fill(BG_COLOR)
        self.renderer.draw_grid(self.terrain_map, game=self)

        deploy_tile = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        deploy_tile.fill(DEPLOY_HIGHLIGHT_COLOR)
        for y in range(16, 20):
            for x in range(GRID_WIDTH):
                self.screen.blit(deploy_tile, (
                    self.grid_offset_x + x * GRID_SIZE,
                    self.grid_offset_y + y * GRID_SIZE))

        self.renderer.draw_units(self.units, self.active_unit, self.selected_unit)

        panel = pygame.Rect(SCREEN_WIDTH - 300, 0, 300, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, INFO_PANEL_COLOR, panel)
        self.renderer.draw_language_button(self.lang_btn)
        self.renderer.draw_general_panel_deploy(self)

        btn = self.deploy_finish_btn
        color = (BUTTON_HOVER_COLOR if btn.collidepoint(pygame.mouse.get_pos())
                 else BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, btn, border_radius=8)
        txt = self.renderer.font.render(t("deploy_finish"), True, WHITE)
        self.screen.blit(txt, txt.get_rect(center=btn.center))

    def draw_gameplay_screen(self):
        self.screen.fill(BG_COLOR)
        self.renderer.draw_grid(self.terrain_map, game=self)

        if self.game_state == AWAITING_DIRECTION:
            self.renderer.draw_facing_highlights(self)
        else:
            self.renderer.draw_highlights(self)

        self.renderer.draw_attack_range_outlines(self)
        self.renderer.draw_units(self.units, self.active_unit, self.selected_unit)
        self.renderer.draw_visual_arrows(self.visual_arrows)
        self.renderer.draw_damage_predictions(self)
        self.renderer.draw_damage_popups(self.damage_popups)
        self.renderer.draw_hint_bar(self)
        self.renderer.draw_info_panel(self)

        if self.game_state == GAME_OVER:
            self.renderer.draw_game_over_modal(self)

    def create_selection_ui(self):
        ui = {"pool_cards": [], "team_slots": [], "start_button": None}

        pool = [(n, s) for n, s in UNIT_CATALOG.items() if not s.get("enemy_only")]

        px, py, pw, ph = 50, 110, 400, 85
        for i, (name, stats) in enumerate(pool):
            rect = pygame.Rect(px, py + i * (ph + 12), pw, ph)
            btn = pygame.Rect(rect.right + 10, rect.centery - 18, 75, 36)
            ui["pool_cards"].append(
                {"name": name, "stats": stats, "rect": rect, "button": btn})

        tx, ty, tw, th = 600, 110, 360, 55
        for i in range(5):
            ui["team_slots"].append({
                "name": None,
                "rect": pygame.Rect(tx, ty + i * (th + 12), tw, th),
            })

        ui["start_button"] = pygame.Rect(tx, ty + 5 * (th + 12) + 20, tw, 60)
        return ui

    def generate_terrain(self):
        terrain = [["NORMAL" for _ in range(GRID_WIDTH)]
                   for _ in range(GRID_HEIGHT)]
        self.fence_hp = {}

        for y in (9, 10):
            for x in range(GRID_WIDTH):
                terrain[y][x] = "RIVER"

        bridge_count = random.randint(1, 2)
        bridge_cols = random.sample(range(GRID_WIDTH), bridge_count)
        for x in bridge_cols:
            terrain[9][x] = "BRIDGE"
            terrain[10][x] = "BRIDGE"

        for y in range(GRID_HEIGHT):
            if y in (9, 10):
                continue
            for x in range(GRID_WIDTH):
                roll = random.random()
                if roll < 0.15:
                    terrain[y][x] = "FOREST"
                elif roll < 0.25:
                    terrain[y][x] = "MOUNTAIN"
                elif roll < 0.30:
                    terrain[y][x] = "SWAMP"
                elif roll < 0.35:
                    terrain[y][x] = "HIGHLAND"
                elif roll < 0.38:
                    terrain[y][x] = "VILLAGE"
                elif roll < 0.40:
                    terrain[y][x] = "RUINS"

        for x in bridge_cols:
            for y in range(GRID_HEIGHT):
                if y in (9, 10):
                    continue
                if terrain[y][x] == "NORMAL":
                    terrain[y][x] = "ROAD"

        fence_count = random.randint(3, 5)
        placed = 0
        attempts = 0
        while placed < fence_count and attempts < 200:
            attempts += 1
            fx = random.randint(0, GRID_WIDTH - 1)
            fy = random.randint(4, 15)
            if fy in (9, 10):
                continue
            if terrain[fy][fx] not in ("NORMAL", "ROAD"):
                continue
            terrain[fy][fx] = "FENCE"
            self.fence_hp[(fx, fy)] = 100
            placed += 1

        return terrain

    def generate_siege_terrain(self):
        terrain = [["NORMAL"] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.gate_hp = {}
        self.catapult_positions = set()

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                r = random.random()
                if r < 0.12:
                    terrain[y][x] = "FOREST"
                elif r < 0.18:
                    terrain[y][x] = "MOUNTAIN"
                elif r < 0.28:
                    terrain[y][x] = "ROAD"

        gate_x = random.randint(3, GRID_WIDTH - 4)
        for x in range(GRID_WIDTH):
            if x == gate_x:
                terrain[6][x] = "GATE"
                self.gate_hp[(x, 6)] = 500
            else:
                terrain[6][x] = "WALL"

        for x in random.sample(range(GRID_WIDTH), 2):
            terrain[2][x] = "BARRACKS"

        for _ in range(3):
            terrain[random.randint(3, 4)][random.randint(0, GRID_WIDTH - 1)] = "HOUSE"

        for x in random.sample(range(GRID_WIDTH), 2):
            terrain[16][x] = "CATAPULT"
            self.catapult_positions.add((x, 16))

        return terrain

    def setup_initial_units(self, player_comp):
        self._setup_player_units(player_comp)
        self._setup_ai_units()
        self._apply_pending_buffs()

    def _setup_player_units(self, player_comp):
        for i, name in enumerate(player_comp):
            x = i * 2 + 2
            y = 18
            while y > 16 and self.terrain_map[y][x] in ("FENCE", "RIVER", "MOUNTAIN"):
                y -= 1

            unit = create_unit(name, "player", x, y)
            if self.game_mode in ("campaign", "rogue"):
                self._apply_campaign_bonus(unit)
            self._apply_meta_bonus(unit)
            self.units.append(unit)

    def _setup_roster_units(self):
        cs = self.campaign_state
        slot_general = {}
        for gname, uid in getattr(cs, "general_roster_slots", {}).items():
            g = next((x for x in cs.current_generals if x.name == gname), None)
            if g is not None:
                slot_general[uid] = g

        for i, entry in enumerate(cs.roster):
            name = entry["name"]
            x = i * 2 + 2
            y = 18
            while y > 16 and self.terrain_map[y][x] in ("FENCE", "RIVER", "MOUNTAIN"):
                y -= 1

            unit = create_unit(name, "player", x, y)
            self._apply_campaign_bonus(unit)
            self._apply_meta_bonus(unit)

            max_soldiers = unit.max_soldiers
            stored = entry.get("current_soldiers", max_soldiers)
            unit.current_soldiers = max(1, min(stored, max_soldiers))
            unit.soldier_hp = unit.hp_per_soldier
            uid = entry.get("uid")
            if uid is None:
                uid = cs.new_roster_uid()
                entry["uid"] = uid
            unit.roster_uid = uid
            g = slot_general.get(uid)
            if g is not None:
                cs.assign_general(g, unit)
            self.units.append(unit)

    def _setup_ai_units(self):
        if self.game_mode == "campaign":
            ai_count = self._quest_enemy_count
        elif self.game_mode == "rogue":
            ai_count = self._quest_enemy_count
        else:
            ai_count = 5

        if self.game_mode == "rogue" and self._quest_enemy_pool:
            ai_pool = list(self._quest_enemy_pool)
        else:
            ai_pool = ["槍騎兵", "弓騎兵", "長槍兵", "盾兵", "弩手"]
            if random.random() < 0.5:
                for i, n in enumerate(ai_pool):
                    if n in ("弩手", "弓騎兵"):
                        ai_pool[i] = "弓箭手"
                        break
            random.shuffle(ai_pool)
            ai_pool = ai_pool[:ai_count]

        blocked = ("FENCE", "WALL", "HOUSE", "GATE")
        melee_spots = [(x, 3) for x in range(GRID_WIDTH)
                       if self.terrain_map[3][x] not in blocked]
        ranged_spots = [(x, y) for x in range(GRID_WIDTH) for y in (0, 1, 2)
                        if self.terrain_map[y][x] not in blocked]
        if not melee_spots:
            melee_spots = [(x, 3) for x in range(GRID_WIDTH)]
        if not ranged_spots:
            ranged_spots = [(x, y) for x in range(GRID_WIDTH) for y in (0, 1, 2)]
        random.shuffle(melee_spots)
        random.shuffle(ranged_spots)

        ascension_mult = META.get_ascension_mult() / 100.0
        for name in ai_pool:
            enemy = create_unit(name, "ai", 0, 0)
            spot = (melee_spots.pop() if enemy.attack_range <= 1
                    else ranged_spots.pop())
            enemy.x, enemy.y = spot
            if self._is_siege_node and enemy.attack_range > 1:
                enemy.siege_wall_bonus = True

            mult = self.enemy_mult / 100.0 * ascension_mult
            enemy.base_attack = int(enemy.base_attack * mult)
            enemy.base_defense = int(enemy.base_defense * mult)
            enemy.hp_per_soldier = max(1, int(enemy.hp_per_soldier * mult))
            enemy.soldier_hp = enemy.hp_per_soldier
            self.units.append(enemy)

    def _apply_campaign_bonus(self, unit):
        cs = self.campaign_state
        name = unit.name
        star = cs.get_star(name)
        path = cs.get_path(name)

        unit.evolution_star = star
        unit.evolution_path = path
        unit.evolution_mechanics = get_mechanics(name, path)

        bonus = get_star_bonus(star)
        unit.equip_attack_bonus = unit.base_attack * bonus["atk"] // 100
        unit.equip_defense_bonus = unit.base_defense * bonus["def"] // 100

        if bonus["hp"] > 0:
            old_hp = unit.hp_per_soldier
            unit.hp_per_soldier = unit.hp_per_soldier * (100 + bonus["hp"]) // 100
            if unit.soldier_hp == old_hp:
                unit.soldier_hp = unit.hp_per_soldier

    def _apply_meta_bonus(self, unit):
        atk_pct = META.get_effect_value("permanent_atk_percent")
        def_pct = META.get_effect_value("permanent_def_percent")
        extra_soldiers = META.get_effect_value("extra_soldiers")
        start_morale = META.get_effect_value("starting_morale")

        if atk_pct:
            unit.equip_attack_bonus += int(unit.base_attack * atk_pct / 100)
        if def_pct:
            unit.equip_defense_bonus += int(unit.base_defense * def_pct / 100)
        if extra_soldiers:
            unit.max_soldiers += int(extra_soldiers)
            unit.current_soldiers = unit.max_soldiers
        if start_morale:
            unit.morale = min(100, unit.morale + int(start_morale))

    def _apply_pending_buffs(self):
        cs = self.campaign_state

        perm_atk = cs.get_permanent_bonus("permanent_atk")
        perm_def = cs.get_permanent_bonus("permanent_def")
        perm_morale = cs.get_permanent_bonus("permanent_morale")
        perm_ap = cs.get_permanent_bonus("permanent_ap")

        wt = cs.war_temple
        cavalry_bonus = wt.permanent_buffs.get("cavalry_charge_bonus", 0)
        infantry_bonus = wt.permanent_buffs.get("infantry_def_bonus", 0)
        archer_bonus = wt.permanent_buffs.get("archer_hit_bonus", 0)

        for buff in cs.consume_buffs():
            self._apply_single_pending_buff(buff)

        for unit in self.units:
            if unit.team != "player":
                continue
            self._apply_player_buffs(unit, perm_atk, perm_def, perm_morale,
                                     perm_ap, cavalry_bonus, infantry_bonus,
                                     archer_bonus)

    def _apply_single_pending_buff(self, buff):
        effect = buff["effect"]
        value = buff["value"]
        for unit in self.units:
            if unit.team != "player":
                continue
            if effect == "atk_buff":
                unit.equip_attack_bonus += unit.base_attack * value // 100
            elif effect == "def_buff":
                unit.equip_defense_bonus += unit.base_defense * value // 100
            elif effect == "morale_buff":
                unit.morale = min(100, unit.morale + value)
            elif effect == "morale_penalty":
                unit.morale = max(0, unit.morale - value)

    def _apply_player_buffs(self, unit, perm_atk, perm_def, perm_morale, perm_ap,
                            cavalry_bonus, infantry_bonus, archer_bonus):
        if perm_atk:
            unit.equip_attack_bonus += unit.base_attack * perm_atk // 100
        if perm_def:
            unit.equip_defense_bonus += unit.base_defense * perm_def // 100
        if perm_morale:
            unit.morale = min(100, unit.morale + perm_morale)
        if perm_ap:
            unit.ap = min(unit.max_ap, unit.ap + perm_ap)
        if cavalry_bonus and unit.is_cavalry:
            unit.equip_attack_bonus += unit.base_attack * cavalry_bonus // 100
        if infantry_bonus and unit.name in ("長槍兵", "盾兵"):
            unit.equip_defense_bonus += unit.base_defense * infantry_bonus // 100
        if archer_bonus and unit.attack_range > 1:
            unit.base_accuracy += archer_bonus

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
        if self.terrain_map[_u.y][_u.x] in ("VILLAGE", "BARRACKS") and _u.is_alive():
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

    def trigger_skill_intent(self, unit):

        if unit.skill_used_this_turn:
            self.add_damage_popup("本回合已使用技能", unit.x, unit.y, is_miss=True)
            return
        if unit.ap < unit.skill_cost:
            self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
            return

        if unit.name in ("弩手", "長槍兵", "弓騎兵", "弓箭手"):
            unit.ap -= unit.skill_cost
            unit.execute_skill(self)
            unit.skill_used_this_turn = True
            self.is_skill_targeting = False
        else:
            self.is_skill_targeting = not self.is_skill_targeting

    def trigger_visual_arrow(self, start, end, is_skill=False):
        self.visual_arrows.append(VisualArrow(start, end, is_skill=is_skill))

    def add_damage_popup(self, text, gx, gy, is_crit=False, is_miss=False, is_wet=False):
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

    def get_unit_at(self, x, y):
        return next((u for u in self.units
                     if u.is_alive() and u.x == x and u.y == y), None)

    def get_attack_ap_cost(self, unit):
        if unit.is_rapid_salvo:
            return 30
        if unit.special == "move_shoot_discount" and unit.has_moved:
            return 40
        return 60


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

                extra = terrain_move_extra(self.terrain_map[ny][nx], True)
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

                extra = terrain_move_extra(self.terrain_map[ny][nx],
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

        for other in self.units:
            if not other.is_alive() or other.team == unit.team:
                continue

            chebyshev = max(abs(unit.x - other.x), abs(unit.y - other.y))
            manhattan = abs(unit.x - other.x) + abs(unit.y - other.y)

            if chebyshev < min_range:
                continue
            if chebyshev > 1 and not self.check_line_of_sight(
                    unit.x, unit.y, other.x, other.y):
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

    def check_line_of_sight(self, p1x, p1y, p2x, p2y):
        steps = max(abs(p1x - p2x), abs(p1y - p2y))
        if steps <= 1:
            return True
        for i in range(1, steps):
            ratio = i / steps
            cx = round(p1x + (p2x - p1x) * ratio)
            cy = round(p1y + (p2y - p1y) * ratio)
            if (cx, cy) in ((p1x, p1y), (p2x, p2y)):
                continue
            if self.terrain_map[cy][cx] in ("MOUNTAIN", "FOREST"):
                return False
        return True

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

                extra = terrain_move_extra(self.terrain_map[ny][nx],
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
                and self.skill_btn.collidepoint(pos)):
            self.trigger_skill_intent(self.active_unit)
            return
        if (self.active_unit and self.active_unit.team == "player"
                and self._is_siege_node
                and self.terrain_map[self.active_unit.y][self.active_unit.x] == "CATAPULT"
                and self.catapult_btn.collidepoint(pos)):
            self._fire_catapult(self.active_unit)
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
        elif (self.terrain_map[gy][gx] == "FENCE"
                and max(abs(actor.x - gx), abs(actor.y - gy)) <= 1):
            self._attack_fence(actor, gx, gy)
        elif (self.terrain_map[gy][gx] == "GATE"
                and max(abs(actor.x - gx), abs(actor.y - gy)) <= 1):
            self._attack_gate(actor, gx, gy)
        else:
            self.is_skill_targeting = False

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
            damage = other.attack_power - unit.defense
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

            base = max(1, (enemy.attack_power - unit.defense) // 2)
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
        dist = max(abs(attacker.x - defender.x), abs(attacker.y - defender.y))
        actual_target = defender

        guard = None
        if dist > 1 and defender.guarded_by and defender.guarded_by.is_alive():
            guard = defender.guarded_by

        if guard and "guard_transfer_100" not in getattr(guard, "evolution_mechanics", []):
            full_result = calculate_combat_result(attacker, defender, self,
                                                  "NORMAL", preview=False)
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
            self.check_game_over()
            return

        if guard:
            actual_target = guard
            self.add_damage_popup(t("pop_shield_guard"),
                                  defender.x, defender.y, is_crit=True)

        result = calculate_combat_result(attacker, actual_target, self,
                                         "NORMAL", preview=False)
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
        new_unit.is_general = unit.is_general
        new_unit.general_name = unit.general_name
        new_unit.general_bonuses = dict(getattr(unit, "general_bonuses", {}))
        new_unit.general_defense_bonus = getattr(unit, "general_defense_bonus", 0)
        new_unit.max_soldiers = base_max + new_unit.general_bonuses.get("soldier_flat", 0)
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

    def _attack_fence(self, unit, gx, gy):
        if unit.ap < 40:
            self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
            return
        unit.ap -= 40
        hp = self.fence_hp.get((gx, gy), 100)
        hp -= max(100, unit.attack_power)
        self.add_damage_popup(f"柵欄 {hp}", gx, gy, is_crit=True)
        self.trigger_visual_arrow((unit.x, unit.y), (gx, gy))
        if hp <= 0:
            self.fence_hp.pop((gx, gy), None)
            self.terrain_map[gy][gx] = "NORMAL"
        else:
            self.fence_hp[(gx, gy)] = hp

    def _attack_gate(self, unit, gx, gy):
        if unit.ap < 40:
            self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
            return
        unit.ap -= 40
        hp = self.gate_hp.get((gx, gy), 500)
        hp -= max(100, unit.attack_power)
        self.add_damage_popup(f"城門 {max(0, hp)}", gx, gy, is_crit=True)
        self.trigger_visual_arrow((unit.x, unit.y), (gx, gy))
        if hp <= 0:
            self.gate_hp.pop((gx, gy), None)
            self.terrain_map[gy][gx] = "NORMAL"
        else:
            self.gate_hp[(gx, gy)] = hp

    def _fire_catapult(self, unit):
        if unit.ap < 50:
            self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
            return
        if not self.gate_hp:
            self.add_damage_popup("城門已破", unit.x, unit.y, is_miss=True)
            return
        unit.ap -= 50
        target = min(self.gate_hp,
                     key=lambda p: max(abs(p[0] - unit.x), abs(p[1] - unit.y)))
        hp = self.gate_hp[target] - 300
        self.add_damage_popup(f"投石! 城門 {max(0, hp)}", target[0], target[1], is_crit=True)
        self.trigger_visual_arrow((unit.x, unit.y), target)
        if hp <= 0:
            self.gate_hp.pop(target, None)
            self.terrain_map[target[1]][target[0]] = "NORMAL"
        else:
            self.gate_hp[target] = hp

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


    def check_game_over(self):
        if self.game_state not in (GAMEPLAY, AWAITING_DIRECTION):
            return

        player_alive = any(u.team == "player" and u.is_alive() for u in self.units)
        ai_alive = any(u.team == "ai" and u.is_alive() for u in self.units)
        if player_alive and ai_alive:
            return

        self.game_state = GAME_OVER
        self.campaign_win = player_alive and not ai_alive

        total_kills = sum(
            max(0, u.max_soldiers - u.current_soldiers)
            for u in self.units if u.team == "ai")
        self._record_battle_stats(total_kills)

        if self.campaign_win:
            self._recover_general_troops()

        self._award_general_merit()
        self._writeback_roster()
        self._save_to_war_temple()
        self._award_rogue_rewards()

        META.check_achievements()
        META.save()
        self._save_campaign()

    def _record_battle_stats(self, total_kills):
        META.stats["total_kills"] = META.stats.get("total_kills", 0) + total_kills
        META.stats["total_battles"] = META.stats.get("total_battles", 0) + 1

        if self.campaign_win:
            META.stats["total_wins"] = META.stats.get("total_wins", 0) + 1
            META.add_soul(total_kills)
            META.add_soul(5)
        else:
            META.stats["total_losses"] = META.stats.get("total_losses", 0) + 1
            META.add_soul(total_kills // 2)

    def _recover_general_troops(self):
        cs = self.campaign_state
        for unit in self.units:
            if unit.team != "player" or not unit.is_alive():
                continue
            if not unit.is_general:
                continue
            for g in cs.current_generals:
                if g.name != unit.general_name:
                    continue
                heal_ratio = g.get_bonuses().get("heal_ratio", 0)
                lost = unit.max_soldiers - unit.current_soldiers
                recover = int(lost * heal_ratio)
                if recover > 0:
                    unit.current_soldiers = min(unit.max_soldiers,
                                                unit.current_soldiers + recover)
                break

    def _squad_root(self, unit):
        seen = set()
        cur = unit
        while getattr(cur, "is_temporary", False):
            nxt = getattr(cur, "split_sibling", None)
            if nxt is None or nxt is cur or id(nxt) in seen:
                break
            seen.add(id(cur))
            cur = nxt
        return cur

    def _writeback_roster(self):
        if self.game_mode not in ("campaign", "rogue"):
            return
        cs = self.campaign_state
        slots = {}
        order = []
        for u in self.units:
            if u.team != "player":
                continue
            root = self._squad_root(u)
            if root not in slots:
                uid = getattr(root, "roster_uid", None)
                if uid is None:
                    uid = cs.new_roster_uid()
                    root.roster_uid = uid
                slots[root] = [root.name, 0, uid]
                order.append(root)
            slots[root][1] += max(0, u.current_soldiers)
        cs.roster = [{"name": slots[r][0], "current_soldiers": slots[r][1],
                      "uid": slots[r][2]} for r in order]
        cs.remove_dead_unit()

    def _award_general_merit(self):
        if self.general_reward_given:
            return
        if not self.campaign_state.current_generals:
            return

        self.general_reward_given = True
        for g in self.campaign_state.current_generals:
            if g.name not in self.campaign_state.general_assignments:
                continue

            unit = self.campaign_state.general_assignments[g.name]
            merit = 20
            if unit.is_alive():
                merit += 15
            if self.campaign_win:
                merit += 15

            node = getattr(self.campaign_state, "last_node", None)
            if node:
                if node.node_type == NODE_SIEGE:
                    merit += 30
                elif node.node_type == NODE_BOSS:
                    merit += 50

            leveled = g.add_merit(merit)
            if not unit.is_alive():
                g.status = STATUS_DEAD

            msg = f"{g.name}: 戰功 +{merit}"
            if leveled:
                for stat in leveled:
                    msg += f"  {STAT_NAMES.get(stat, stat)} +1"
            self.general_msg = msg

    def _award_rogue_rewards(self):
        if self.game_mode != "rogue":
            return

        cs = self.campaign_state
        node = cs.last_node

        if not self.campaign_win:
            cs.add_exp_all(30)
            cs.complete_current_node()
            return

        if not node:
            return

        data = node.data
        gold_gain = data.get("gold", 50)
        cs.add_gold(gold_gain)
        cs.add_exp_all(data.get("exp", 100))
        META.record_gold(gold_gain)

        if node.node_type in (NODE_SIEGE, NODE_BOSS):
            self.pending_siege_is_boss = node.data.get("is_boss",
                                                       node.node_type == NODE_BOSS)
            self.pending_siege_buffs = pick_rewards(is_boss=self.pending_siege_is_boss)
            self.pending_captive = None
            if random.random() < 0.3 and cs.can_add_general():
                self.pending_captive = General.generate_enemy(cs.act)
            self.game_state = SIEGE_REWARD
            META.check_achievements()
            META.save()
            self._save_campaign()
            return

        cs.complete_current_node()