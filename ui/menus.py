"""Main menu and settings screens."""
import pygame
from config import *  # noqa: F401,F403


class MenuMixin:
    def draw_main_menu(self, game):
        self.screen.fill(BG_COLOR)
        self._text_centered(t("main_menu_title"), self._title_font,
                            (255, 215, 0), (SCREEN_WIDTH // 2, 130))
        self._text_centered(t("main_menu_subtitle"), self.big_font,
                            (180, 180, 200), (SCREEN_WIDTH // 2, 195))

        for rect, label in (
                (game.menu_start_btn, t("start_game_btn")),
                (game.menu_settings_btn, t("settings_btn")),
                (game.menu_quit_btn, t("quit_btn"))):
            color = self._button_color(rect, BUTTON_COLOR)
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=12)
            self._text_centered(label, self.font, WHITE, rect.center)

    def draw_settings(self, game):
        self.screen.fill(BG_COLOR)
        self._text_centered(t("settings_title"), self.big_font, TEXT_COLOR,
                            (SCREEN_WIDTH // 2, 140))
        for rect, label in (
                (game.settings_lang_btn, t("lang_btn")),
                (game.settings_back_btn, t("back_btn"))):
            color = self._button_color(rect, BUTTON_COLOR)
            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            self._text_centered(label, self.font, WHITE, rect.center)
