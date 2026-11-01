"""Renderer composition: core helpers + menu + battle drawing."""
import os

import pygame

from ui.widgets import CoreMixin
from ui.menus import MenuMixin
from ui.battle import BattleMixin


class GameRenderer(CoreMixin, MenuMixin, BattleMixin):
    def __init__(self, screen, ox, oy):
        self.screen = screen
        self.ox = ox
        self.oy = oy
        self._font_path = None
        (self.font, self.big_font, self.unit_font, self.dmg_font,
         self.small_font, self.log_font, self.is_default) = self.load_fonts()
        if self._font_path:
            try:
                self._title_font = pygame.font.Font(self._font_path, 68)
            except pygame.error:
                self._title_font = self.big_font
        else:
            self._title_font = pygame.font.Font(None, 72)

    def load_fonts(self):
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyh.ttf",
            r"C:\Windows\Fonts\msyhl.ttc", r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\arial.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ]
        for path in candidates:
            if not os.path.exists(path):
                continue
            try:
                self._font_path = path
                return (
                    pygame.font.Font(path, 16),
                    pygame.font.Font(path, 22),
                    pygame.font.Font(path, 14),
                    pygame.font.Font(path, 20),
                    pygame.font.Font(path, 13),
                    pygame.font.Font(path, 12),
                    False,
                )
            except pygame.error:
                continue
        self._font_path = None
        return (
            pygame.font.Font(None, 20),
            pygame.font.Font(None, 28),
            pygame.font.Font(None, 18),
            pygame.font.Font(None, 24),
            pygame.font.Font(None, 15),
            pygame.font.Font(None, 14),
            True,
        )
