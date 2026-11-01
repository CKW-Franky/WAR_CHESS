"""Unit picker and deployment input for quick mode."""
import sys

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE, GRID_WIDTH,
    WHITE, GRID_COLOR, PLAYER_COLOR, DEPLOY_HIGHLIGHT_COLOR,
    SELECTED_COLOR, TEXT_COLOR, BG_COLOR, INFO_PANEL_COLOR,
    BUTTON_COLOR, BUTTON_HOVER_COLOR, BUTTON_DISABLED_COLOR,
    DEPLOYMENT_STAGE, GAMEPLAY,
    t, toggle_language,
)
from units import create_unit, UNIT_CATALOG


class SelectionMixin:
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
                    self.setup_initial_units(self.player_team_composition)
                    self.game_state = DEPLOYMENT_STAGE

    def _try_add_unit(self, name):
        if len(self.player_team_composition) >= self.population_limit:
            return
        self.player_team_composition.append(name)

    def create_selection_ui(self):
        ui = {"pool_cards": [], "team_slots": [], "start_button": None}

        pool = [(n, s) for n, s in UNIT_CATALOG.items() if not s.get("enemy_only")]

        px, py, pw, ph = 50, 110, 400, 85
        for i, (name, stats) in enumerate(pool):
            preview = create_unit(name, "player", 0, 0)
            stats = {
                "soldiers": preview.max_soldiers,
                "hp": preview.max_hp,
                "attack": preview.attack_power,
                "defense": preview.defense,
                "range": preview.attack_range,
                "gear": preview.loadout_summary(),
            }
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

        bg = INFO_PANEL_COLOR
        border = PLAYER_COLOR
        pygame.draw.rect(self.screen, bg, card["rect"], border_radius=8)
        pygame.draw.rect(self.screen, border, card["rect"], 2, border_radius=8)

        name_color = WHITE
        self.screen.blit(
            self.renderer.font.render(t(f"unit_{card['name']}"), True, name_color),
            (card["rect"].x + 15, card["rect"].y + 10))

        stats = card["stats"]
        stat_text = (f"兵力 {stats['soldiers']}   HP {stats['hp']}   "
                     f"ATK {stats['attack']}   DEF {stats['defense']}")
        stat_color = GRID_COLOR
        self.screen.blit(
            self.renderer.small_font.render(stat_text, True, stat_color),
            (card["rect"].x + 15, card["rect"].y + 40))

        gear = stats.get("gear", "")
        if gear:
            self.screen.blit(
                self.renderer.small_font.render(gear, True, (165, 180, 205)),
                (card["rect"].x + 15, card["rect"].y + 61))

        full = len(self.player_team_composition) >= self.population_limit
        if full:
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

            if self.deploy_finish_btn.collidepoint(pos):
                self.game_state = GAMEPLAY
                self.selected_unit = None
                return

            self._handle_deploy_grid_click(pos)

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

        btn = self.deploy_finish_btn
        color = (BUTTON_HOVER_COLOR if btn.collidepoint(pygame.mouse.get_pos())
                 else BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, btn, border_radius=8)
        txt = self.renderer.font.render(t("deploy_finish"), True, WHITE)
        self.screen.blit(txt, txt.get_rect(center=btn.center))
