"""Transient battle visuals: damage popups and arrow tracers."""
import pygame

from config import GRID_SIZE


class DamagePopup:
    def __init__(self, text, x, y, color):
        self.text = str(text)
        self.x = x
        self.y = y
        self.color = color
        self.alpha = 255
        self.life = 40

    def update(self):
        self.y -= 0.8
        self.life -= 1
        if self.life < 15:
            self.alpha = max(0, int((self.life / 15) * 255))

    def draw(self, screen, font):
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(self.alpha)
        screen.blit(surf, surf.get_rect(center=(self.x, self.y)))

    def is_alive(self):
        return self.life > 0


class VisualArrow:
    def __init__(self, start_grid, end_grid, is_skill=False):
        self.start_grid = start_grid
        self.end_grid = end_grid
        self.is_skill = is_skill
        self.progress = 0.0
        self.speed = 0.08
        self.color = (255, 200, 50) if is_skill else (255, 255, 255)

    def draw(self, screen, ox, oy):
        self.progress += self.speed
        p = min(1.0, self.progress)
        sx = ox + self.start_grid[0] * GRID_SIZE + GRID_SIZE // 2
        sy = oy + self.start_grid[1] * GRID_SIZE + GRID_SIZE // 2
        ex = ox + self.end_grid[0] * GRID_SIZE + GRID_SIZE // 2
        ey = oy + self.end_grid[1] * GRID_SIZE + GRID_SIZE // 2
        cx = sx + (ex - sx) * p
        cy = sy + (ey - sy) * p
        pygame.draw.circle(screen, self.color, (int(cx), int(cy)), 5)
        if p < 1.0:
            pygame.draw.line(screen, self.color, (sx, sy), (cx, cy), 2)

    def is_alive(self):
        return self.progress < 1.0