"""Main menu and settings. Quick mode is the only mode in this branch."""
import sys

import pygame

from config import (
    SETTINGS, MAIN_MENU, SELECTION_SCREEN, toggle_language,
)


class MenuMixin:
    def handle_main_menu_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.menu_start_btn.collidepoint(event.pos):
                    self._start_quick_mode()
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

    def _start_quick_mode(self):
        self.population_limit = 5
        self.enemy_mult = 100
        self.reset_entire_game()
        self.game_state = SELECTION_SCREEN
