"""Primitive drawing helpers: text, bars, card buttons."""
import pygame
from config import *  # noqa: F401,F403


class CoreMixin:
    def _text(self, text, font, color, x, y):
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))
        return surf

    def _text_centered(self, text, font, color, center):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=center))
        return surf

    def _button_color(self, rect, base, hover=BUTTON_HOVER_COLOR):
        return hover if rect.collidepoint(pygame.mouse.get_pos()) else base

    def _draw_bar(self, x, y, w, h, ratio, fg, bg=(40, 40, 50)):
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(self.screen, bg, (x, y, w, h), border_radius=2)
        if ratio > 0:
            pygame.draw.rect(self.screen, fg,
                             (x, y, max(1, int(w * ratio)), h), border_radius=2)

    def _stat_bar(self, x, y, w, label, cur, mx, fg):
        pct = int(cur / mx * 100) if mx > 0 else 0
        self._text(f"{label} {cur}/{mx} ({pct}%)", self.small_font, TEXT_COLOR, x, y)
        self._draw_bar(x, y + 15, w, 6, cur / mx if mx > 0 else 0, fg)
        return y + 28

    def _wrap_text(self, text, font, max_width):
        lines, current = [], ""
        for ch in text:
            if font.size(current + ch)[0] > max_width:
                lines.append(current)
                current = ch
            else:
                current += ch
        if current:
            lines.append(current)
        return lines

    def draw_language_button(self, rect):
        color = self._button_color(rect, BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        pygame.draw.rect(self.screen, SELECTED_COLOR, rect, 1, border_radius=6)
        self._text_centered(t("lang_btn"), self.small_font, WHITE, rect.center)
