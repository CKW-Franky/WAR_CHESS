import os
import pygame
from config import *
from combat import DIRECTION_DELTAS, calculate_combat_result, get_zoc_tiles
from general import (STAT_KEYS, STAT_NAMES, STATUS_ACTIVE, STATUS_MOURNING,
                     STATUS_RETIRED, STATUS_DEAD)
from meta import META, META_SKILLS, ACHIEVEMENTS
from save import load_slot_summary


class GameRenderer:
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

    def draw_main_menu(self, game):
        self.screen.fill(BG_COLOR)
        self._text_centered(t("main_menu_title"), self._title_font,
                            (255, 215, 0), (SCREEN_WIDTH // 2, 130))
        self._text_centered(t("main_menu_subtitle"), self.big_font,
                            (180, 180, 200), (SCREEN_WIDTH // 2, 195))
        self._text_centered(f"靈魂點數: {META.soul_points}", self.font,
                            (200, 150, 255), (SCREEN_WIDTH // 2, 232))

        for rect, label in (
                (game.menu_start_btn, t("start_game_btn")),
                (game.menu_temple_btn, t("war_temple_btn")),
                (game.menu_meta_btn, t("meta_btn")),
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

    def draw_slot_select(self, game):
        self.screen.fill(BG_COLOR)
        self._text_centered(t("slot_select_title"), self.big_font,
                            (255, 215, 0), (SCREEN_WIDTH // 2, 85))

        game.slot_cards = []
        card_w, card_h, gap = 320, 280, 40
        total_w = 3 * card_w + 2 * gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        y = 180

        for i in range(3):
            slot_id = i + 1
            x = start_x + i * (card_w + gap)
            card_rect = pygame.Rect(x, y, card_w, card_h)
            enter_btn = pygame.Rect(card_rect.x + 20, card_rect.bottom - 60, 130, 40)
            delete_btn = pygame.Rect(card_rect.right - 150, card_rect.bottom - 60, 130, 40)
            summary = load_slot_summary(slot_id)

            game.slot_cards.append({
                "rect": card_rect, "slot_id": slot_id,
                "enter_btn": enter_btn, "delete_btn": delete_btn,
                "summary": summary,
            })
            self._draw_slot_card(card_rect, slot_id, enter_btn, delete_btn, summary)

        back_rect = game.slot_select_back_btn
        color = self._button_color(back_rect, BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, back_rect, border_radius=8)
        self._text_centered(t("slot_back"), self.font, WHITE, back_rect.center)

        if game.pending_delete_slot is not None:
            self._draw_delete_confirm(game)

    def _draw_slot_card(self, card_rect, slot_id, enter_btn, delete_btn, summary):
        hover = card_rect.collidepoint(pygame.mouse.get_pos())
        bg = (60, 70, 90) if hover else (45, 52, 68)
        pygame.draw.rect(self.screen, bg, card_rect, border_radius=14)
        border = (255, 220, 100) if hover else (120, 140, 180)
        pygame.draw.rect(self.screen, border, card_rect, 3, border_radius=14)

        self._text(t("slot_label", id=slot_id), self.big_font,
                   (255, 240, 180), card_rect.x + 20, card_rect.y + 15)
        pygame.draw.line(self.screen, (90, 100, 120),
                         (card_rect.x + 15, card_rect.y + 60),
                         (card_rect.right - 15, card_rect.y + 60), 1)

        if summary is None:
            self._text_centered(t("slot_empty"), self.font, (180, 180, 200),
                                (card_rect.centerx, card_rect.y + 140))
        else:
            self._draw_slot_summary(card_rect, summary)

        enter_label = t("slot_continue") if summary else t("slot_new")
        enter_color = self._button_color(enter_btn, (70, 140, 70), (100, 180, 100))
        pygame.draw.rect(self.screen, enter_color, enter_btn, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, enter_btn, 2, border_radius=8)
        self._text_centered(enter_label, self.font, WHITE, enter_btn.center)

        if summary:
            delete_color = self._button_color(delete_btn, (150, 60, 60), (200, 90, 90))
            pygame.draw.rect(self.screen, delete_color, delete_btn, border_radius=8)
            pygame.draw.rect(self.screen, WHITE, delete_btn, 2, border_radius=8)
            self._text_centered(t("slot_delete"), self.font, WHITE, delete_btn.center)

    def _draw_slot_summary(self, card_rect, summary):
        lines = [
            t("slot_soul", val=summary["soul_points"]),
            t("slot_act", act=summary["act"]),
            t("slot_gold", val=summary["gold"]),
            t("slot_generals", val=summary["generals_count"]),
            t("slot_unlocked", val=summary["unlocked_count"]),
            t("slot_battles", val=summary["total_battles"]),
        ]
        if summary.get("ascension", 0) > 0:
            lines.append(t("slot_ascension", val=summary["ascension"]))
        ly = card_rect.y + 80
        for line in lines:
            self._text(line, self.small_font, (220, 220, 240),
                       card_rect.x + 25, ly)
            ly += 26

    def _draw_delete_confirm(self, game):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        dialog = pygame.Rect(SCREEN_WIDTH // 2 - 280, SCREEN_HEIGHT // 2 - 130, 560, 260)
        pygame.draw.rect(self.screen, BG_COLOR, dialog, border_radius=14)
        pygame.draw.rect(self.screen, (255, 100, 100), dialog, 3, border_radius=14)

        self._text_centered(t("slot_delete_confirm_title"), self.big_font,
                            (255, 120, 120), (dialog.centerx, dialog.y + 45))
        msg = t("slot_delete_confirm_msg", id=game.pending_delete_slot)
        self._draw_wrapped_centered(msg, self.font, (220, 220, 240),
                                    dialog.centerx, dialog.y + 100,
                                    dialog.width - 60, 30)

        yes_rect = pygame.Rect(dialog.centerx - 220, dialog.bottom - 80, 200, 60)
        game.slot_delete_yes_btn = yes_rect
        color = self._button_color(yes_rect, (150, 60, 60), (200, 80, 80))
        pygame.draw.rect(self.screen, color, yes_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, yes_rect, 2, border_radius=10)
        self._text_centered(t("slot_delete_yes"), self.font, WHITE, yes_rect.center)

        no_rect = pygame.Rect(dialog.centerx + 20, dialog.bottom - 80, 200, 60)
        game.slot_delete_no_btn = no_rect
        color = self._button_color(no_rect, (60, 90, 140), (90, 130, 200))
        pygame.draw.rect(self.screen, color, no_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, no_rect, 2, border_radius=10)
        self._text_centered(t("slot_delete_no"), self.font, WHITE, no_rect.center)

    def _draw_wrapped_centered(self, text, font, color, center_x, top_y,
                               max_width, line_h):
        lines = self._wrap_text(text, font, max_width)
        for i, line in enumerate(lines):
            self._text_centered(line, font, color, (center_x, top_y + i * line_h))
        return top_y + len(lines) * line_h

    def draw_mode_select(self, game):
        self.screen.fill(BG_COLOR)
        self._text_centered(t("mode_select_title"), self.big_font, TEXT_COLOR,
                            (SCREEN_WIDTH // 2, 155))
        for rect, title, desc, accent, is_beta in (
                (game.mode_quick_btn, t("quick_mode_title"),
                 t("quick_mode_desc"), (70, 130, 230), False),
                (game.mode_campaign_btn, t("campaign_mode_title"),
                 t("campaign_mode_desc"), (220, 100, 70), True)):
            hover = rect.collidepoint(pygame.mouse.get_pos())
            bg = tuple(min(c + 30, 255) for c in accent) if hover else accent
            pygame.draw.rect(self.screen, bg, rect, border_radius=14)
            pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=14)
            self._text_centered(title, self.big_font, WHITE, (rect.centerx, rect.y + 70))
            self._text_centered(desc, self.small_font, (240, 240, 240),
                                (rect.centerx, rect.y + 130))
            if is_beta:
                badge = pygame.Rect(rect.right - 96, rect.y + 14, 82, 28)
                pygame.draw.rect(self.screen, (255, 190, 60), badge, border_radius=8)
                self._text_centered(t("mode_beta_badge"), self.small_font,
                                    (40, 30, 10), badge.center)

        self._text_centered(t("mode_beta_note"), self.small_font, (200, 190, 150),
                            (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))

        color = self._button_color(game.mode_back_btn, BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, game.mode_back_btn, border_radius=10)
        self._text_centered(t("back_btn"), self.font, WHITE, game.mode_back_btn.center)

    def draw_war_temple(self, game):
        self.screen.fill(BG_COLOR)
        wt = game.campaign_state.war_temple
        self._text(t("war_temple_title"), self.big_font, (255, 215, 0), 40, 30)

        tabs = [
            ("main", t("war_temple_main"), wt.main_hall),
            ("mourning", t("war_temple_mourning"), wt.mourning),
            ("fame", t("war_temple_fame"), wt.hall_of_fame),
            ("martyr", t("war_temple_martyr"), wt.martyr_shrine),
        ]
        game.war_temple_tabs = []
        x = 40
        for key, label, _ in tabs:
            r = pygame.Rect(x, 90, 200, 45)
            active = game.war_temple_tab == key
            color = ((100, 130, 200) if active
                     else self._button_color(r, (60, 60, 70)))
            pygame.draw.rect(self.screen, color, r, border_radius=8)
            pygame.draw.rect(self.screen, WHITE, r, 2, border_radius=8)
            self._text_centered(label, self.font, WHITE, r.center)
            game.war_temple_tabs.append((r, key))
            x += 220

        generals = next(t[2] for t in tabs if t[0] == game.war_temple_tab)
        y_off = 150
        if game.war_temple_tab == "fame":
            for effect, value in wt.permanent_buffs.items():
                self._text(f"{effect}: +{value}%", self.font, (200, 255, 200),
                           40, y_off)
                y_off += 25
            y_off += 10

        game.war_temple_cards = []
        cw, ch, gap, cols = 280, 180, 20, 3
        for i, g in enumerate(generals):
            row, col = divmod(i, cols)
            r = pygame.Rect(40 + col * (cw + gap), y_off + row * (ch + gap), cw, ch)
            game.war_temple_cards.append((r, g))
            self._draw_general_card(r, g)

        if not generals:
            self._text(t("war_temple_empty"), self.font, (150, 150, 150),
                       40, y_off + 20)

        color = self._button_color(game.war_temple_back_btn, BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, game.war_temple_back_btn, border_radius=8)
        self._text_centered(t("back_btn"), self.font, WHITE,
                            game.war_temple_back_btn.center)

    def _draw_general_card(self, rect, g):
        pygame.draw.rect(self.screen, (50, 55, 70), rect, border_radius=10)
        pygame.draw.rect(self.screen, (200, 180, 100), rect, 2, border_radius=10)
        self._text(g.name, self.font, (255, 240, 180), rect.x + 12, rect.y + 8)
        rank = g.get_rank_name()
        if rank:
            self._text(rank, self.small_font, (255, 200, 100), rect.x + 12, rect.y + 30)

        status_map = {
            STATUS_ACTIVE: ("可出征", (100, 220, 100)),
            STATUS_MOURNING: (f"丁憂({g.mourning_remaining})", (255, 180, 80)),
            STATUS_RETIRED: ("配享", (100, 200, 255)),
            STATUS_DEAD: ("陣亡", (200, 80, 80)),
        }
        label, color = status_map.get(g.status, ("?", (150, 150, 150)))
        self._text(label, self.small_font, color, rect.right - 100, rect.y + 8)

        self._draw_stat_bars(rect, g, top=rect.y + 55, bar_w=150)
        self._text(f"戰功: {g.merit}", self.small_font, (255, 220, 100),
                   rect.x + 12, rect.bottom - 25)

    def _draw_stat_bars(self, rect, g, top, bar_w=150):
        colors = {"wu": (255, 100, 100), "mou": (100, 180, 255),
                  "tong": (100, 220, 120), "zhi": (220, 180, 100),
                  "yun": (200, 120, 255)}
        y = top
        for key in STAT_KEYS:
            value = getattr(g, key)
            color = colors[key]
            self._text(STAT_NAMES[key], self.small_font, color, rect.x + 12, y)
            bx = rect.x + 55
            pygame.draw.rect(self.screen, (35, 35, 45), (bx, y + 4, bar_w, 8), border_radius=2)
            pygame.draw.rect(self.screen, color,
                             (bx, y + 4, int(bar_w * value / 100), 8), border_radius=2)
            self._text(str(value), self.small_font, WHITE, bx + bar_w + 8, y)
            y += 20

    def draw_general_select(self, game):
        self.screen.fill(BG_COLOR)
        self._text_centered(t("general_select_title"), self.big_font,
                            (255, 215, 0), (SCREEN_WIDTH // 2, 80))
        wt = game.campaign_state.war_temple
        available = wt.get_active()

        game.general_select_cards = []
        cw, ch, gap, cols = 260, 220, 20, 4
        sx = (SCREEN_WIDTH - cols * cw - (cols - 1) * gap) // 2
        for i, g in enumerate(available):
            row, col = divmod(i, cols)
            r = pygame.Rect(sx + col * (cw + gap), 150 + row * (ch + gap), cw, ch)
            game.general_select_cards.append((r, g))
            self._draw_selectable_general_card(r, g, selected=game.general_select_pick is g)

        self._draw_general_select_buttons(game, available)

        if game.general_msg:
            self._text_centered(game.general_msg, self.font,
                                (255, 240, 100), (SCREEN_WIDTH // 2, 650))

    def _draw_selectable_general_card(self, rect, g, selected):
        bg = (90, 80, 50) if selected else (50, 55, 70)
        border = (255, 230, 100) if selected else (150, 150, 150)
        pygame.draw.rect(self.screen, bg, rect, border_radius=10)
        pygame.draw.rect(self.screen, border, rect, 3 if selected else 2, border_radius=10)
        self._text(g.name, self.font, (255, 240, 180), rect.x + 12, rect.y + 8)
        rank = g.get_rank_name()
        if rank:
            self._text(rank, self.small_font, (255, 200, 100), rect.x + 12, rect.y + 32)
        self._draw_stat_bars(rect, g, top=rect.y + 60, bar_w=130)
        if g.revive_count > 0:
            self._text(f"起復 x{g.revive_count}", self.small_font, (255, 180, 100),
                       rect.x + 12, rect.bottom - 25)

    def _draw_general_select_buttons(self, game, available):
        recruit_used = getattr(game, "general_recruit_used", False)
        new_btn = game.general_select_new_btn
        if recruit_used:
            color, label = (70, 70, 70), t("general_recruit_used")
        else:
            color = self._button_color(new_btn, BUTTON_COLOR)
            label = t("general_select_new")
        pygame.draw.rect(self.screen, color, new_btn, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, new_btn, 2, border_radius=10)
        self._text_centered(label, self.font, WHITE, new_btn.center)

        confirm_btn = game.general_select_confirm_btn
        can_confirm = game.general_select_pick is not None
        if can_confirm:
            color = self._button_color(confirm_btn, (80, 140, 80), (100, 180, 100))
        else:
            color = (70, 70, 70)
        pygame.draw.rect(self.screen, color, confirm_btn, border_radius=10)
        self._text_centered(t("general_select_confirm"), self.font, WHITE,
                            confirm_btn.center)

    def draw_rogue_map(self, game):
        self.screen.fill(BG_COLOR)
        cs = game.campaign_state
        self._text(t("rogue_map_title"), self.big_font, (255, 215, 0), 40, 30)
        self._text(t("rogue_act", act=cs.act), self.font, (200, 200, 220), 40, 70)
        self._text(t("rogue_gold", gold=cs.gold), self.font, (255, 220, 100),
                   SCREEN_WIDTH - 400, 40)
        self._text(t("rogue_pop", pop=cs.population), self.font, (255, 220, 100),
                   SCREEN_WIDTH - 400, 70)

        game.rogue_node_rects = []
        available = cs.get_available_layer()
        icons = {
            "combat": ("劍", (200, 100, 100)), "elite": ("骷", (180, 60, 180)),
            "shop": ("袋", (220, 200, 80)), "rest": ("火", (100, 200, 100)),
            "event": ("?", (150, 150, 220)), "siege": ("城", (230, 140, 60)),
            "boss": ("王", (255, 80, 80)),
        }
        from rogue import NODE_NAMES

        from campaign import MAP_COLUMNS, MAP_ROWS
        size = 44
        left = 80
        right = SCREEN_WIDTH - 430
        col_step = (right - left) // max(1, MAP_COLUMNS - 1)
        row_y = [180, 300, 420]

        pos = {}
        for node in cs.rogue_map:
            pos[node] = (left + node.column * col_step, row_y[node.row])
        for node in cs.rogue_map:
            for conn_idx in node.connections:
                if 0 <= conn_idx < len(cs.rogue_map):
                    other = cs.rogue_map[conn_idx]
                    pygame.draw.line(self.screen, (80, 80, 90),
                                     pos[node], pos[other], 3)

        for node in cs.rogue_map:
            x, y = pos[node]
            r = pygame.Rect(x - size // 2, y - size // 2, size, size)
            game.rogue_node_rects.append((r, node))
            self._draw_rogue_node(node, x, y, size, available, icons, NODE_NAMES)

        self._text(t("rogue_click"), self.small_font, (180, 180, 200),
                   40, SCREEN_HEIGHT - 40)
        self._text(t("mode_beta_note"), self.small_font, (200, 190, 150),
                   40, SCREEN_HEIGHT - 68)

        btn = game.roster_map_btn
        color = self._button_color(btn, BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, btn, border_radius=8)
        self._text_centered("部隊管理", self.font, WHITE, btn.center)

    def _draw_rogue_node(self, node, x, y, size, available, icons, node_names):
        is_available = (node.layer == available) and not node.completed
        if node.completed:
            color, border = (60, 100, 60), (100, 160, 100)
        elif is_available:
            pulse = int(abs(pygame.time.get_ticks() / 300) % 2)
            color = (100, 130, 200)
            border = (255, 230, 100) if pulse == 0 else (255, 180, 60)
        else:
            color, border = (50, 50, 60), (80, 80, 90)
        pygame.draw.circle(self.screen, color, (x, y), size // 2)
        pygame.draw.circle(self.screen, border, (x, y), size // 2, 3)

        icon, icon_color = icons.get(node.node_type, ("?", (200, 200, 200)))
        if node.completed:
            icon_color = (140, 140, 140)
        self._text_centered(icon, self.font, icon_color, (x, y))
        label = node_names.get(node.node_type, node.node_type)
        self._text_centered(f"{node.layer + 1}·{label}", self.small_font,
                            (220, 220, 220), (x, y + size // 2 + 12))

    def draw_event_screen(self, game):
        self.screen.fill(BG_COLOR)
        ev = game.current_event
        if not ev:
            return
        self._text_centered(t("event_title"), self.big_font, (255, 200, 100),
                            (SCREEN_WIDTH // 2, 80))
        self._text_centered(ev["name"], self.big_font, (255, 215, 0),
                            (SCREEN_WIDTH // 2, 140))
        y = self._draw_wrapped_centered(ev["desc"], self.font, (220, 220, 240),
                                        SCREEN_WIDTH // 2, 210, 800, 32)

        game.rogue_event_option_rects = []
        if game.event_result_msg:
            self._text_centered(t("event_result", msg=game.event_result_msg),
                                self.font, (255, 240, 100),
                                (SCREEN_WIDTH // 2, y + 60))
            self._text_centered(t("event_continue"), self.font, WHITE,
                                (SCREEN_WIDTH // 2, y + 110))
            return

        y = 400
        for opt in ev["options"]:
            r = pygame.Rect(SCREEN_WIDTH // 2 - 300, y, 600, 60)
            color = self._button_color(r, (60, 80, 130), (100, 130, 200))
            pygame.draw.rect(self.screen, color, r, border_radius=10)
            pygame.draw.rect(self.screen, (180, 200, 255), r, 2, border_radius=10)
            self._text_centered(opt["text"], self.font, WHITE, r.center)
            game.rogue_event_option_rects.append((r, opt))
            y += 75

    def draw_rogue_shop(self, game):
        self.screen.fill(BG_COLOR)
        cs = game.campaign_state
        self._text(t("shop_title"), self.big_font, (255, 215, 0), 60, 40)
        self._text(f"金幣: {cs.gold}", self.font, (255, 220, 100),
                   SCREEN_WIDTH - 300, 50)
        if game.quest_result_msg:
            self._text(game.quest_result_msg, self.font, (255, 200, 100), 60, 80)

        from rogue import ROGUE_SHOP_ITEMS
        game.rogue_shop_rects = []
        y = 130
        for key, item in ROGUE_SHOP_ITEMS.items():
            r = pygame.Rect(60, y, SCREEN_WIDTH - 120, 75)
            game.rogue_shop_rects.append((r, key))
            self._draw_shop_item(r, item, cs.get_shop_cost(item["cost"]), cs.gold)
            y += 85

        color = self._button_color(game.shop_back_btn, BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, game.shop_back_btn, border_radius=8)
        self._text_centered("離開", self.small_font, WHITE, game.shop_back_btn.center)

    def _draw_shop_item(self, rect, item, cost, gold):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        can_afford = gold >= cost
        if can_afford:
            bg = (60, 100, 60) if hover else (45, 60, 80)
        else:
            bg = (50, 40, 40)
        pygame.draw.rect(self.screen, bg, rect, border_radius=8)
        pygame.draw.rect(self.screen, (150, 200, 255), rect, 2, border_radius=8)
        self._text(item["name"], self.font, WHITE, rect.x + 20, rect.y + 12)
        self._text(item["desc"], self.small_font, (200, 200, 220),
                   rect.x + 20, rect.y + 42)
        self._text(f"{cost} 金", self.font, (255, 220, 100),
                   rect.right - 150, rect.y + 22)

    def draw_rest_screen(self, game):
        self.screen.fill(BG_COLOR)
        self._text_centered(t("rest_title"), self.big_font, (255, 215, 0),
                            (SCREEN_WIDTH // 2, 100))
        self._text_centered("選擇一項行動：", self.font, (200, 200, 220),
                            (SCREEN_WIDTH // 2, 160))

        game.rogue_rest_rects = []
        options = [
            ("heal", t("rest_heal")), ("train", t("rest_train")),
            ("gold", t("rest_gold")), ("leave", t("rest_leave")),
        ]
        y = 220
        for action, label in options:
            r = pygame.Rect(SCREEN_WIDTH // 2 - 300, y, 600, 60)
            game.rogue_rest_rects.append((r, action))
            color = self._button_color(r, (60, 80, 130), (100, 130, 200))
            pygame.draw.rect(self.screen, color, r, border_radius=10)
            pygame.draw.rect(self.screen, (180, 200, 255), r, 2, border_radius=10)
            self._text_centered(label, self.font, WHITE, r.center)
            y += 75

    def draw_roster_screen(self, game):
        self.screen.fill(BG_COLOR)
        cs = game.campaign_state
        self._text("【部隊管理】", self.big_font, (255, 215, 0), 40, 30)
        self._text(f"金幣: {cs.gold}   人口: {len(cs.roster)}/{cs.population}",
                   self.font, (255, 220, 100), 40, 70)

        game.roster_unit_rects = []
        game.roster_recruit_rects = []

        y = 120
        if not cs.roster:
            self._text("（部隊為空）", self.font, (150, 150, 150), 60, y)
        for i, entry in enumerate(cs.roster):
            name = entry["name"]
            max_soldiers = cs._roster_max_soldiers(name)
            current = entry.get("current_soldiers", max_soldiers)
            r = pygame.Rect(60, y, 700, 60)
            pygame.draw.rect(self.screen, INFO_PANEL_COLOR, r, border_radius=8)
            pygame.draw.rect(self.screen, PLAYER_COLOR, r, 2, border_radius=8)
            self._text(t(f"unit_{name}"), self.font, WHITE, r.x + 15, r.y + 8)
            self._text(f"兵力 {current}/{max_soldiers}", self.small_font,
                       (200, 220, 240), r.x + 15, r.y + 34)
            btn = pygame.Rect(r.right - 150, r.centery - 20, 130, 40)
            game.roster_unit_rects.append((btn, i))
            color = self._button_color(btn, BUTTON_COLOR)
            pygame.draw.rect(self.screen, color, btn, border_radius=6)
            self._text_centered("補充 (50G)", self.small_font, WHITE, btn.center)
            y += 70

        y += 10
        self._text("—— 招募新單位（100G）——", self.font, (255, 200, 100), 60, y)
        y += 40
        unlocked = [n for n in cs.unlocked_units
                    if n not in cs.roster_unit_names()]
        if not unlocked:
            self._text("（無可招募兵種）", self.small_font, (150, 150, 150), 60, y)
        for name in unlocked:
            btn = pygame.Rect(60, y, 300, 45)
            game.roster_recruit_rects.append((btn, name))
            color = self._button_color(btn, (60, 130, 60), (90, 170, 90))
            pygame.draw.rect(self.screen, color, btn, border_radius=6)
            self._text_centered(f"招募 {t(f'unit_{name}')}", self.small_font,
                                WHITE, btn.center)
            y += 55

        if game.quest_result_msg:
            self._text(game.quest_result_msg, self.font, (255, 240, 100),
                       60, SCREEN_HEIGHT - 120)

        color = self._button_color(game.roster_back_btn, BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, game.roster_back_btn, border_radius=8)
        self._text_centered("返回", self.font, WHITE, game.roster_back_btn.center)

    def draw_siege_reward(self, game):
        self.screen.fill(BG_COLOR)
        game.siege_reward_rects = []
        self._text_centered(t("siege_reward_title"), self.big_font,
                            (255, 215, 0), (SCREEN_WIDTH // 2, 80))
        self._text_centered(t("siege_reward_desc"), self.font,
                            (220, 220, 240), (SCREEN_WIDTH // 2, 140))

        buffs = game.pending_siege_buffs
        cw, ch, gap = 280, 320, 30
        total = len(buffs) * cw + max(0, len(buffs) - 1) * gap
        sx = (SCREEN_WIDTH - total) // 2
        for i, buff in enumerate(buffs):
            r = pygame.Rect(sx + i * (cw + gap), 200, cw, ch)
            game.siege_reward_rects.append((r, buff))
            hover = r.collidepoint(pygame.mouse.get_pos())
            bg = (90, 60, 130) if hover else (60, 45, 90)
            border = (255, 220, 100) if hover else (200, 180, 255)
            pygame.draw.rect(self.screen, bg, r, border_radius=14)
            pygame.draw.rect(self.screen, border, r, 3, border_radius=14)
            self._text_centered(buff["name"], self.big_font, (255, 240, 180),
                                (r.centerx, r.y + 80))
            self._text_centered(buff["desc"], self.small_font, (230, 230, 240),
                                (r.centerx, r.y + 180))

    def draw_captive_screen(self, game):
        self.screen.fill(BG_COLOR)
        g = game.captive_general
        if not g:
            return
        self._text_centered(t("captive_title"), self.big_font, (255, 200, 100),
                            (SCREEN_WIDTH // 2, 120))
        self._text_centered(t("captive_desc", name=g.name), self.font,
                            (220, 220, 240), (SCREEN_WIDTH // 2, 200))

        colors = {"wu": (255, 100, 100), "mou": (100, 180, 255),
                  "tong": (100, 220, 120), "zhi": (220, 180, 100),
                  "yun": (200, 120, 255)}
        y = 260
        for key in STAT_KEYS:
            value = getattr(g, key)
            color = colors[key]
            self._text(STAT_NAMES[key], self.font, color, SCREEN_WIDTH // 2 - 200, y)
            bx = SCREEN_WIDTH // 2 - 100
            bw = 200
            pygame.draw.rect(self.screen, (35, 35, 45), (bx, y + 4, bw, 10), border_radius=2)
            pygame.draw.rect(self.screen, color,
                             (bx, y + 4, int(bw * value / 100), 10), border_radius=2)
            self._text(str(value), self.font, WHITE, bx + bw + 10, y)
            y += 30

        cost = 100 + g.loyalty
        chance = max(10, min(90, 70 - g.loyalty))
        self._text_centered(t("captive_cost", cost=cost), self.font,
                            (255, 220, 100), (SCREEN_WIDTH // 2, 440))
        self._text_centered(t("captive_chance", chance=chance), self.font,
                            (200, 255, 200), (SCREEN_WIDTH // 2, 475))

        accept_color = self._button_color(game.captive_accept_btn,
                                          (80, 140, 80), (100, 180, 100))
        pygame.draw.rect(self.screen, accept_color, game.captive_accept_btn,
                         border_radius=10)
        self._text_centered(t("captive_accept"), self.font, WHITE,
                            game.captive_accept_btn.center)

        refuse_color = self._button_color(game.captive_refuse_btn,
                                          (150, 70, 70), (200, 100, 100))
        pygame.draw.rect(self.screen, refuse_color, game.captive_refuse_btn,
                         border_radius=10)
        self._text_centered(t("captive_refuse"), self.font, WHITE,
                            game.captive_refuse_btn.center)

        if game.general_msg:
            self._text_centered(game.general_msg, self.font,
                                (255, 240, 100), (SCREEN_WIDTH // 2, 620))

    def draw_path_select(self, game):
        self.screen.fill(BG_COLOR)
        name = game.path_choice_name
        from campaign import EVOLUTION_PATHS
        paths = EVOLUTION_PATHS.get(name, {})

        self._text_centered(f"{name} - 進化選擇", self.big_font,
                            (255, 215, 0), (SCREEN_WIDTH // 2, 120))
        self._text_centered("達到 3★ 精英，選擇進化路線", self.font,
                            (200, 200, 220), (SCREEN_WIDTH // 2, 180))

        for key, rect in (("A", game.path_select_A_btn),
                          ("B", game.path_select_B_btn)):
            if key not in paths:
                continue
            data = paths[key]
            hover = rect.collidepoint(pygame.mouse.get_pos())
            bg = (90, 60, 130) if hover else (60, 45, 90)
            pygame.draw.rect(self.screen, bg, rect, border_radius=14)
            pygame.draw.rect(self.screen, (200, 180, 255), rect, 2, border_radius=14)
            self._text_centered(data["name"], self.big_font, (255, 240, 180),
                                (rect.centerx, rect.y + 100))
            self._text_centered(data["desc"], self.small_font, (230, 230, 240),
                                (rect.centerx, rect.y + 180))

    def draw_meta_screen(self, game):
        self.screen.fill(BG_COLOR)
        self._text(t("meta_title"), self.big_font, (255, 215, 0), 40, 30)
        self._text(t("meta_soul", points=META.soul_points), self.font,
                   (200, 150, 255), 40, 70)

        game.meta_tab_buttons = []
        tabs = [("skills", t("meta_tab_skills")),
                ("achievements", t("meta_tab_achievements")),
                ("stats", t("meta_tab_stats"))]
        x = 40
        for key, label in tabs:
            r = pygame.Rect(x, 110, 200, 45)
            active = game.meta_tab == key
            color = ((100, 130, 200) if active
                     else self._button_color(r, (60, 60, 70)))
            pygame.draw.rect(self.screen, color, r, border_radius=8)
            pygame.draw.rect(self.screen, WHITE, r, 2, border_radius=8)
            self._text_centered(label, self.font, WHITE, r.center)
            game.meta_tab_buttons.append((r, key))
            x += 220

        if game.meta_tab == "skills":
            self._draw_meta_skills(game)
        elif game.meta_tab == "achievements":
            self._draw_meta_achievements(game)
        else:
            self._draw_meta_stats(game)

        color = self._button_color(game.meta_back_btn, BUTTON_COLOR)
        pygame.draw.rect(self.screen, color, game.meta_back_btn, border_radius=8)
        self._text_centered(t("back_btn"), self.font, WHITE, game.meta_back_btn.center)

    def _draw_meta_skills(self, game):
        game.meta_skill_rects = []
        branches = {}
        for sid, skill in META_SKILLS.items():
            branches.setdefault(skill["branch"], []).append(sid)
        y = 180
        for branch, ids in branches.items():
            self._text(f"【{branch}】", self.font, (255, 220, 120), 40, y)
            y += 28
            for sid in ids:
                self._draw_meta_skill_row(game, sid, y)
                y += 65

    def _draw_meta_skill_row(self, game, sid, y):
        skill = META_SKILLS[sid]
        level = META.get_skill_level(sid)
        r = pygame.Rect(40, y, SCREEN_WIDTH - 80, 55)
        game.meta_skill_rects.append((r, sid))
        hover = r.collidepoint(pygame.mouse.get_pos())
        can_upgrade = META.can_upgrade(sid)
        is_max = level >= skill["max_level"]

        if is_max:
            bg = (70, 70, 80)
        elif hover and can_upgrade:
            bg = (60, 100, 60)
        else:
            bg = (45, 60, 80)
        pygame.draw.rect(self.screen, bg, r, border_radius=6)
        self._text(skill["name"], self.font, WHITE, r.x + 15, r.y + 5)
        self._text(f"Lv {level}/{skill['max_level']}", self.small_font,
                   (200, 200, 100), r.x + 200, r.y + 10)
        self._text(skill["desc"], self.small_font, (200, 200, 220),
                   r.x + 15, r.y + 28)

        if is_max:
            label, color = "已滿", (100, 100, 100)
        else:
            label = f"{META.get_skill_cost(sid)} 點"
            color = (100, 180, 100) if can_upgrade else (100, 80, 80)
        br = pygame.Rect(r.right - 150, r.y + 10, 130, 35)
        pygame.draw.rect(self.screen, color, br, border_radius=6)
        self._text_centered(label, self.small_font, WHITE, br.center)

    def _draw_meta_achievements(self, game):
        y = 180
        for aid, ach in ACHIEVEMENTS.items():
            unlocked = aid in META.unlocked_achievements
            r = pygame.Rect(40, y, SCREEN_WIDTH - 80, 50)
            bg = (60, 100, 60) if unlocked else (50, 50, 60)
            border = (100, 200, 100) if unlocked else (80, 80, 90)
            pygame.draw.rect(self.screen, bg, r, border_radius=6)
            pygame.draw.rect(self.screen, border, r, 2, border_radius=6)

            mark = "✓" if unlocked else "○"
            mark_color = (100, 255, 100) if unlocked else (120, 120, 120)
            self._text(mark, self.font, mark_color, r.x + 15, r.y + 10)
            name_color = WHITE if unlocked else (150, 150, 150)
            self._text(ach["name"], self.font, name_color, r.x + 55, r.y + 5)
            self._text(ach["desc"], self.small_font, (200, 200, 220),
                       r.x + 55, r.y + 28)
            self._text(f"+{ach['reward']} 靈魂", self.small_font,
                       (200, 150, 255), r.right - 150, r.y + 15)
            y += 60

    def _draw_meta_stats(self, game):
        lines = [
            ("總擊殺", META.stats["total_kills"]),
            ("總戰鬥", META.stats["total_battles"]),
            ("勝場", META.stats["total_wins"]),
            ("攻城勝利", META.stats["siege_wins"]),
            ("通關幕數", META.stats["act_clears"]),
            ("通關次數", META.stats["campaign_clears"]),
            ("週目", META.ascension_level),
        ]
        y = 180
        for label, value in lines:
            self._text(label, self.font, (200, 200, 220), 60, y)
            self._text(str(value), self.font, (255, 220, 100), 400, y)
            y += 40

    def draw_general_panel_deploy(self, game):
        cs = game.campaign_state
        if not cs.current_generals:
            return

        panel = pygame.Rect(SCREEN_WIDTH - 290, 380, 280, 300)
        pygame.draw.rect(self.screen, (28, 32, 42), panel, border_radius=10)
        pygame.draw.rect(self.screen, (200, 180, 100), panel, 2, border_radius=10)
        self._text(t("general_list_title"), self.font, (255, 215, 0),
                   panel.x + 15, panel.y + 10)

        y = panel.y + 40
        for g in cs.current_generals:
            assigned = g.name in cs.general_assignments
            label = g.name + (" ★" if assigned else "")
            color = (150, 255, 150) if assigned else (255, 240, 180)
            self._text(label, self.small_font, color, panel.x + 15, y)
            rank = g.get_rank_name()
            if rank:
                self._text(rank, self.small_font, (255, 200, 100), panel.x + 120, y)
            y += 22

        btn = game.general_appoint_btn
        btn.y = panel.y + 240
        can_click = bool(game.selected_unit and game.selected_unit.team == "player")
        color = ((100, 180, 100) if btn.collidepoint(pygame.mouse.get_pos()) and can_click
                 else (80, 140, 80) if can_click else (70, 70, 70))
        pygame.draw.rect(self.screen, color, btn, border_radius=6)
        pygame.draw.rect(self.screen, WHITE, btn, 2, border_radius=6)
        self._text_centered(t("general_appoint_btn"), self.small_font, WHITE, btn.center)

        if game.general_msg:
            self._text(game.general_msg, self.small_font, (255, 240, 100),
                       panel.x + 15, panel.bottom + 5)
        if game.is_choosing_general:
            self._draw_general_choose_overlay(game)

    def _draw_general_choose_overlay(self, game):
        available = game.campaign_state.get_available_generals()
        if not available:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cw, ch, gap = 260, 180, 20
        total = len(available) * cw + max(0, len(available) - 1) * gap
        sx = (SCREEN_WIDTH - total) // 2
        y = SCREEN_HEIGHT // 2 - ch // 2

        game.general_assign_list_rects = []
        for i, g in enumerate(available):
            r = pygame.Rect(sx + i * (cw + gap), y, cw, ch)
            game.general_assign_list_rects.append((r, g))
            hover = r.collidepoint(pygame.mouse.get_pos())
            bg = (90, 80, 50) if hover else (50, 55, 70)
            pygame.draw.rect(self.screen, bg, r, border_radius=10)
            pygame.draw.rect(self.screen, (255, 230, 100), r, 2, border_radius=10)
            self._text(g.name, self.font, (255, 240, 180), r.x + 12, r.y + 8)

            colors = {"wu": (255, 100, 100), "mou": (100, 180, 255),
                      "tong": (100, 220, 120), "zhi": (220, 180, 100),
                      "yun": (200, 120, 255)}
            yy = r.y + 40
            for key in STAT_KEYS:
                value = getattr(g, key)
                self._text(STAT_NAMES[key], self.small_font, colors[key],
                           r.x + 12, yy)
                self._text(str(value), self.small_font, WHITE, r.x + 60, yy)
                yy += 20

    def draw_grid(self, terrain_map, game=None):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                terrain = terrain_map[y][x]
                r = pygame.Rect(self.ox + x * GRID_SIZE, self.oy + y * GRID_SIZE,
                                GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.screen, TERRAIN_COLORS.get(terrain, (60, 70, 80)), r)
                self._draw_terrain_icon(terrain, r, game, x, y)

        for x in range(GRID_WIDTH + 1):
            pygame.draw.line(self.screen, GRID_COLOR,
                             (self.ox + x * GRID_SIZE, self.oy),
                             (self.ox + x * GRID_SIZE,
                              self.oy + GRID_HEIGHT * GRID_SIZE), 1)
        for y in range(GRID_HEIGHT + 1):
            pygame.draw.line(self.screen, GRID_COLOR,
                             (self.ox, self.oy + y * GRID_SIZE),
                             (self.ox + GRID_WIDTH * GRID_SIZE,
                              self.oy + y * GRID_SIZE), 1)

        mid_y = self.oy + 10 * GRID_SIZE
        pygame.draw.line(self.screen, DIVIDER_COLOR, (self.ox, mid_y),
                         (self.ox + GRID_WIDTH * GRID_SIZE, mid_y), 4)

    def _draw_terrain_icon(self, terrain, r, game=None, gx=0, gy=0):
        cx, cy = r.centerx, r.centery
        if terrain == "FOREST":
            pygame.draw.polygon(self.screen, (20, 70, 35),
                                [(cx, r.y + 8), (cx - 10, r.bottom - 8), (cx + 10, r.bottom - 8)])
        elif terrain == "MOUNTAIN":
            pygame.draw.polygon(self.screen, (60, 50, 45),
                                [(cx, r.y + 6), (cx - 12, r.bottom - 6), (cx + 12, r.bottom - 6)])
            pygame.draw.polygon(self.screen, (150, 150, 150),
                                [(cx, r.y + 6), (cx - 4, r.y + 16), (cx + 4, r.y + 16)])
        elif terrain == "RIVER":
            pygame.draw.line(self.screen, (10, 60, 110), (r.x + 5, cy - 5), (r.right - 5, cy - 5), 2)
            pygame.draw.line(self.screen, (10, 60, 110), (r.x + 5, cy + 5), (r.right - 5, cy + 5), 2)
        elif terrain == "ROAD":
            pygame.draw.line(self.screen, (175, 165, 140), (r.x + 4, cy), (r.right - 4, cy), 3)
        elif terrain == "SWAMP":
            pygame.draw.circle(self.screen, (25, 55, 35), (cx - 8, cy - 5), 4)
            pygame.draw.circle(self.screen, (25, 55, 35), (cx + 7, cy + 4), 5)
            pygame.draw.circle(self.screen, (25, 55, 35), (cx + 2, cy - 8), 3)
        elif terrain == "HIGHLAND":
            pygame.draw.polygon(self.screen, (110, 90, 70),
                                [(cx, r.y + 6), (cx - 13, r.bottom - 6), (cx + 13, r.bottom - 6)])
        elif terrain == "VILLAGE":
            pygame.draw.rect(self.screen, (110, 85, 60), (cx - 9, cy - 2, 18, 12))
            pygame.draw.polygon(self.screen, (150, 60, 50),
                                [(cx - 12, cy - 2), (cx, cy - 14), (cx + 12, cy - 2)])
        elif terrain == "RUINS":
            pygame.draw.rect(self.screen, (70, 60, 55), (cx - 13, cy - 12, 10, 10))
            pygame.draw.rect(self.screen, (70, 60, 55), (cx + 3, cy + 1, 10, 10))
            pygame.draw.line(self.screen, (70, 60, 55), (cx - 13, cy + 9), (cx + 13, cy - 9), 2)
        elif terrain == "FENCE":
            pygame.draw.line(self.screen, (60, 40, 25), (r.x + 5, r.y + 8), (r.right - 5, r.bottom - 8), 3)
            pygame.draw.line(self.screen, (60, 40, 25), (r.right - 5, r.y + 8), (r.x + 5, r.bottom - 8), 3)
            if game is not None:
                hp = getattr(game, "fence_hp", {}).get((gx, gy))
                if hp is not None:
                    self._text(str(hp), self.small_font, (255, 220, 100),
                               r.x + 3, r.y + 2)
        elif terrain == "BRIDGE":
            for i in range(3):
                yy = r.y + 12 + i * 12
                pygame.draw.line(self.screen, (110, 80, 45), (r.x + 4, yy), (r.right - 4, yy), 3)
        elif terrain == "WALL":
            for i in range(3):
                yy = r.y + 6 + i * 14
                pygame.draw.line(self.screen, (70, 65, 55), (r.x + 3, yy), (r.right - 3, yy), 2)
            for i in range(2):
                xx = r.x + 12 + i * 20
                pygame.draw.line(self.screen, (70, 65, 55), (xx, r.y + 3), (xx, r.bottom - 3), 2)
        elif terrain == "GATE":
            pygame.draw.rect(self.screen, (120, 85, 45), (cx - 12, cy - 10, 24, 22), 2)
            if game is not None:
                hp = getattr(game, "gate_hp", {}).get((gx, gy))
                if hp is not None:
                    self._text(str(hp), self.small_font, (255, 160, 60), r.x + 3, r.y + 2)
        elif terrain == "BARRACKS":
            pygame.draw.rect(self.screen, (110, 90, 80), (cx - 11, cy - 3, 22, 14))
            pygame.draw.polygon(self.screen, (150, 70, 60),
                                [(cx - 14, cy - 3), (cx, cy - 15), (cx + 14, cy - 3)])
            pygame.draw.line(self.screen, (255, 220, 120), (cx, cy - 15), (cx, cy - 3), 2)
        elif terrain == "HOUSE":
            pygame.draw.rect(self.screen, (90, 70, 45), (cx - 10, cy - 2, 20, 14))
            pygame.draw.polygon(self.screen, (110, 60, 40),
                                [(cx - 13, cy - 2), (cx, cy - 14), (cx + 13, cy - 2)])
        elif terrain == "CATAPULT":
            pygame.draw.polygon(self.screen, (80, 70, 55),
                                [(cx, r.y + 6), (cx - 13, r.bottom - 8), (cx + 13, r.bottom - 8)])
            pygame.draw.line(self.screen, (200, 180, 140), (cx - 10, r.bottom - 8), (cx, r.y + 10), 3)

    def draw_units(self, units, active, selected):
        for unit in units:
            if not unit.is_alive():
                continue
            r = pygame.Rect(self.ox + unit.x * GRID_SIZE,
                            self.oy + unit.y * GRID_SIZE,
                            GRID_SIZE, GRID_SIZE)
            color = PLAYER_COLOR if unit.team == "player" else AI_COLOR
            pygame.draw.rect(self.screen, color, r.inflate(-10, -10), border_radius=8)

            self._text_centered(t(f"unit_{unit.name}"), self.small_font,
                                WHITE, (r.centerx, r.top + 14))
            self._text_centered(str(unit.current_soldiers), self.font,
                                WHITE, (r.centerx, r.centery + 6))

            self._draw_unit_hp_bar(unit, r)
            self._draw_unit_facing(unit, r)
            self._draw_unit_status(unit, r, active, selected)

    def _draw_unit_hp_bar(self, unit, r):
        bw = GRID_SIZE - 16
        bh = 4
        bx = r.left + 8
        by = r.bottom - 10
        ratio = unit.current_soldiers / unit.max_soldiers
        pygame.draw.rect(self.screen, (40, 40, 50), (bx, by, bw, bh), border_radius=2)
        if ratio > 0:
            fw = max(2, int(bw * ratio))
            color = (100, 200, 255) if unit.team == "player" else (255, 120, 120)
            pygame.draw.rect(self.screen, color, (bx, by, fw, bh), border_radius=2)

    def _draw_unit_facing(self, unit, r):
        facing = unit.facing
        color = (255, 230, 80)
        thick = 4
        margin = 12
        if facing == 0:
            pygame.draw.line(self.screen, color, (r.left + margin, r.top + 2),
                             (r.right - margin, r.top + 2), thick)
        elif facing == 1:
            pygame.draw.line(self.screen, color, (r.right - 2, r.top + margin),
                             (r.right - 2, r.bottom - margin), thick)
        elif facing == 2:
            pygame.draw.line(self.screen, color, (r.left + margin, r.bottom - 2),
                             (r.right - margin, r.bottom - 2), thick)
        else:
            pygame.draw.line(self.screen, color, (r.left + 2, r.top + margin),
                             (r.left + 2, r.bottom - margin), thick)

    def _draw_unit_status(self, unit, r, active, selected):
        if unit == active:
            pygame.draw.rect(self.screen, DIVIDER_COLOR, r, 3, border_radius=8)
        elif unit == selected:
            pygame.draw.rect(self.screen, SELECTED_COLOR, r, 2, border_radius=8)
        if unit.pike_wall_active:
            pygame.draw.rect(self.screen, (255, 50, 50), r, 2, border_radius=8)

        mw = int((GRID_SIZE - 20) * (unit.morale / 100.0))
        pygame.draw.rect(self.screen, (60, 50, 0),
                         (r.left + 10, r.top + 4, GRID_SIZE - 20, 4))
        if unit.is_routing or unit.morale <= 0:
            morale_color = MORALE_COLORS["routing"]
        elif unit.morale >= 80:
            morale_color = MORALE_COLORS["high"]
        elif unit.morale >= 50:
            morale_color = MORALE_COLORS["stable"]
        elif unit.morale >= 25:
            morale_color = MORALE_COLORS["shaken"]
        else:
            morale_color = MORALE_COLORS["breaking"]
        pygame.draw.rect(self.screen, morale_color,
                         (r.left + 10, r.top + 4, mw, 4))

        if unit.is_routing:
            self._text("!", self.dmg_font, (255, 40, 40), r.x + 3, r.y + 18)

        aw = int((GRID_SIZE - 20) * (unit.ap / float(unit.max_ap)))
        pygame.draw.rect(self.screen, (40, 40, 60),
                         (r.left + 10, r.bottom - 5, GRID_SIZE - 20, 3))
        pygame.draw.rect(self.screen, AP_COLOR, (r.left + 10, r.bottom - 5, aw, 3))

        if unit.is_general:
            self._text("★", self.font, (255, 215, 0), r.right - 20, r.top + 2)

    def draw_highlights(self, game):
        if game.is_split_facing:
            self._draw_split_facing(game)
            return
        if game.is_split_targeting:
            self._draw_split_targets(game)
            return

        unit = game.selected_unit
        if not unit:
            return

        if game.is_skill_targeting:
            s = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
            s.fill(SKILL_HIGHLIGHT_COLOR)
            for x, y in unit.get_skill_targets(game):
                self.screen.blit(s, (self.ox + x * GRID_SIZE,
                                     self.oy + y * GRID_SIZE))
            return

        move_map, normal, pierce = game.get_possible_actions(unit)
        self._draw_move_highlights(game, unit, move_map)
        self._draw_attack_highlights(normal, pierce)
        self._draw_hover_path(game, unit, move_map)

    def _draw_split_targets(self, game):
        unit = game.split_unit
        if not unit:
            return
        s = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        s.fill(SKILL_HIGHLIGHT_COLOR)
        for x, y in game._get_split_targets(unit):
            self.screen.blit(s, (self.ox + x * GRID_SIZE, self.oy + y * GRID_SIZE))

    def _draw_split_facing(self, game):
        if not game.split_pos:
            return
        sx, sy = game.split_pos
        s = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        s.fill(FACE_HIGHLIGHT_COLOR)
        for dx, dy in DIRECTION_DELTAS.values():
            nx, ny = sx + dx, sy + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                self.screen.blit(s, (self.ox + nx * GRID_SIZE, self.oy + ny * GRID_SIZE))

    def _draw_move_highlights(self, game, unit, move_map):
        s = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        s.fill(MOVE_HIGHLIGHT_COLOR)
        for x, y in move_map:
            self.screen.blit(s, (self.ox + x * GRID_SIZE, self.oy + y * GRID_SIZE))

        zoc = get_zoc_tiles(game.units, unit.team, GRID_WIDTH, GRID_HEIGHT)
        for zx, zy in zoc:
            if (zx, zy) in move_map:
                r = pygame.Rect(self.ox + zx * GRID_SIZE,
                                self.oy + zy * GRID_SIZE,
                                GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.screen, (255, 80, 80), r, 2)

    def _draw_attack_highlights(self, normal, pierce):
        a = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        a.fill(ATTACK_HIGHLIGHT_COLOR)
        for x, y in normal:
            self.screen.blit(a, (self.ox + x * GRID_SIZE, self.oy + y * GRID_SIZE))

        p = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        p.fill(PIERCE_HIGHLIGHT_COLOR)
        for x, y in pierce:
            self.screen.blit(p, (self.ox + x * GRID_SIZE, self.oy + y * GRID_SIZE))

    def _draw_hover_path(self, game, unit, move_map):
        m = pygame.mouse.get_pos()
        gx = (m[0] - self.ox) // GRID_SIZE
        gy = (m[1] - self.oy) // GRID_SIZE
        if (gx, gy) not in move_map:
            return
        path = game.find_path(unit, gx, gy)
        if not path:
            return
        px = self.ox + unit.x * GRID_SIZE + GRID_SIZE // 2
        py = self.oy + unit.y * GRID_SIZE + GRID_SIZE // 2
        for cx, cy in path:
            x = self.ox + cx * GRID_SIZE + GRID_SIZE // 2
            y = self.oy + cy * GRID_SIZE + GRID_SIZE // 2
            pygame.draw.line(self.screen, (255, 255, 100), (px, py), (x, y), 3)
            pygame.draw.circle(self.screen, (255, 255, 200), (x, y), 6)
            px, py = x, y

    def draw_attack_range_outlines(self, game):
        unit = game.selected_unit
        if not unit:
            return
        attack_range = unit.get_actual_range(game)
        min_range = unit.get_minimum_range()
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                dist = max(abs(unit.x - x), abs(unit.y - y))
                if not (min_range <= dist <= attack_range):
                    continue
                if (x, y) == (unit.x, unit.y):
                    continue
                if dist > 1 and not game.check_line_of_sight(
                        unit.x, unit.y, x, y):
                    continue
                r = pygame.Rect(self.ox + x * GRID_SIZE,
                                self.oy + y * GRID_SIZE,
                                GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.screen, (255, 140, 0), r, 2)

    def draw_damage_popups(self, popups):
        for p in popups[:]:
            p.update()
            p.draw(self.screen, self.dmg_font)
            if not p.is_alive():
                popups.remove(p)

    def draw_visual_arrows(self, arrows):
        for a in arrows[:]:
            a.draw(self.screen, self.ox, self.oy)
            if not a.is_alive():
                arrows.remove(a)

    def draw_damage_predictions(self, game):
        unit = game.selected_unit
        if not unit or game.is_skill_targeting:
            return
        m = pygame.mouse.get_pos()
        gx = (m[0] - self.ox) // GRID_SIZE
        gy = (m[1] - self.oy) // GRID_SIZE
        if not (0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT):
            return

        _, normal, pierce = game.get_possible_actions(unit)
        target = game.get_unit_at(gx, gy)
        if not target or target.team == unit.team:
            return

        dist = max(abs(unit.x - target.x), abs(unit.y - target.y))
        if dist > 1 and not game.check_line_of_sight(unit.x, unit.y, target.x, target.y):
            return

        if (gx, gy) in pierce:
            res = calculate_combat_result(unit, target, game, "PIERCE", preview=True)
        elif (gx, gy) in normal:
            res = calculate_combat_result(unit, target, game, "NORMAL", preview=True)
        else:
            return

        angle_key = {"FRONT": "pred_angle_front",
                     "FLANK": "pred_angle_flank",
                     "REAR": "pred_angle_rear"}.get(res["angle"], "pred_angle_front")
        lines = [
            (t("pred_attack", target=t(f"unit_{target.name}")) + " " + t(angle_key),
             (255, 220, 0)),
            (t("pred_kill_count", kills=res["kills"]), (255, 200, 50)),
            (t("pred_hit_pct", hit=res["hit_chance"]), (200, 220, 255)),
            (t("pred_expected_dmg", dmg=res["predicted_damage"]), (180, 240, 180)),
            (t("pred_counter_yes") if res["can_counter"] else t("pred_counter_no"),
             (255, 100, 100) if res["can_counter"] else (160, 160, 160)),
        ]
        self._draw_prediction_box(m, lines)

    def _draw_prediction_box(self, mouse_pos, lines):
        line_h = 20
        padding = 8
        max_w = max(self.small_font.size(text)[0] for text, _ in lines)
        bw = max_w + 20
        bh = len(lines) * line_h + padding * 2
        bx = min(mouse_pos[0] + 18, SCREEN_WIDTH - bw - 10)
        by = min(mouse_pos[1] + 15, SCREEN_HEIGHT - bh - 5)

        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box.fill((0, 0, 0, 210))
        self.screen.blit(box, (bx, by))
        pygame.draw.rect(self.screen, SELECTED_COLOR, (bx, by, bw, bh), 1, border_radius=4)

        for i, (text, color) in enumerate(lines):
            self._text(text, self.small_font, color, bx + 10, by + padding + i * line_h)

    def draw_hint_bar(self, game):
        if game.game_state not in (GAMEPLAY, AWAITING_DIRECTION):
            return
        if not (game.active_unit and game.active_unit.team == "player"):
            return
        s = self.small_font.render(t("hint_bar"), True, (200, 200, 200))
        w, h = s.get_width() + 24, 26
        x = self.ox
        y = self.oy + GRID_HEIGHT * GRID_SIZE + 6
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        self.screen.blit(bg, (x, y))
        pygame.draw.rect(self.screen, GRID_COLOR, (x, y, w, h), 1, border_radius=4)
        self.screen.blit(s, (x + 12, y + 4))

    def draw_info_panel(self, game):
        panel = pygame.Rect(SCREEN_WIDTH - 300, 0, 300, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, INFO_PANEL_COLOR, panel)
        self.draw_language_button(game.lang_btn)
        pad = panel.left + 15
        y = 50

        self._text_centered(t("round_turn", turn=game.turn_number), self.big_font,
                            TEXT_COLOR, (panel.centerx, y + 12))
        y += 44

        unit = self._get_info_panel_unit(game)
        if unit:
            y = self._draw_info_panel_unit(unit, pad, y)

        active = game.active_unit
        if active and active.team == "player" and active.is_cavalry:
            charge_btn = game.charge_toggle_btn
            label = t("pop_charge_off") if active.is_charging else t("pop_charge_on")
            color = self._button_color(charge_btn, CHARGE_BUTTON_COLOR, CHARGE_BUTTON_HOVER)
            pygame.draw.rect(self.screen, color, charge_btn, border_radius=6)
            self._text_centered(label, self.small_font, WHITE, charge_btn.center)

        if (active and active.team == "player" and getattr(game, "_is_siege_node", False)
                and game.terrain_map[active.y][active.x] == "CATAPULT"):
            cb = game.catapult_btn
            color = self._button_color(cb, (150, 100, 60), (180, 130, 80))
            pygame.draw.rect(self.screen, color, cb, border_radius=6)
            self._text_centered(t("terrain_CATAPULT"), self.small_font, WHITE, cb.center)

        if active and active.team == "player":
            skill_btn = game.skill_btn
            skill_label = t(f"skill_{active.skill_name}") if active.skill_name else "技能"
            if active.ap < active.skill_cost:
                color = BUTTON_DISABLED_COLOR
            else:
                color = self._button_color(skill_btn, SKILL_BUTTON_COLOR, SKILL_BUTTON_HOVER)
            pygame.draw.rect(self.screen, color, skill_btn, border_radius=6)
            self._text_centered(skill_label, self.small_font, WHITE, skill_btn.center)

        if (active and active.team == "player"
                and not game.is_split_targeting and not game.is_split_facing):
            split_btn = game.split_btn
            if active.can_split():
                split_color = self._button_color(split_btn, (150, 80, 200), (180, 110, 230))
            else:
                split_color = BUTTON_DISABLED_COLOR
            pygame.draw.rect(self.screen, split_color, split_btn, border_radius=6)
            self._text_centered(t("split_btn"), self.small_font, WHITE, split_btn.center)

            if game._find_merge_target(active):
                merge_btn = game.merge_btn
                merge_color = self._button_color(merge_btn, (80, 140, 80), (100, 180, 100))
                pygame.draw.rect(self.screen, merge_color, merge_btn, border_radius=6)
                self._text_centered(t("merge_btn"), self.small_font, WHITE, merge_btn.center)

        end_btn = game.end_turn_btn
        color = self._button_color(end_btn, BUTTON_DISABLED_COLOR)
        pygame.draw.rect(self.screen, color, end_btn, border_radius=8)
        self._text_centered(t("end_turn_btn"), self.small_font, WHITE, end_btn.center)

    def _get_info_panel_unit(self, game):
        if game.game_state == AWAITING_DIRECTION:
            return game.unit_to_face
        if game.active_unit and game.active_unit.team == "player":
            return game.active_unit
        m = pygame.mouse.get_pos()
        gx = (m[0] - self.ox) // GRID_SIZE
        gy = (m[1] - self.oy) // GRID_SIZE
        if 0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT:
            return game.get_unit_at(gx, gy)
        return None

    def _draw_info_panel_unit(self, unit, pad, y):
        self._text(t(f"unit_{unit.name}"), self.font, TEXT_COLOR, pad, y)
        y += 24
        y = self._stat_bar(pad, y, 260, "兵力", unit.current_soldiers,
                           unit.max_soldiers, MODEL_COLOR)
        y = self._stat_bar(pad, y, 260, "HP", unit.hp, unit.max_hp, HP_COLOR)

        if unit.is_routing:
            morale_key = "routing"
        elif unit.morale >= 80:
            morale_key = "high"
        elif unit.morale >= 50:
            morale_key = "stable"
        elif unit.morale >= 25:
            morale_key = "shaken"
        else:
            morale_key = "breaking"
        y = self._stat_bar(pad, y, 260, "士氣", unit.morale, 100,
                           MORALE_COLORS[morale_key])
        y = self._stat_bar(pad, y, 260, "AP", unit.ap, unit.max_ap, AP_COLOR)

        info = (f"ATK {unit.attack_power} DEF {unit.defense} "
                f"RNG {unit.get_actual_range(None)}")
        self._text(info, self.small_font, TEXT_COLOR, pad, y)
        y += 20
        if unit.is_general:
            self._text(f"★ {unit.general_name}", self.small_font,
                       (255, 215, 0), pad, y)
            y += 18
        return y

    def draw_facing_highlights(self, game):
        unit = game.unit_to_face
        if not unit:
            return
        s = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        s.fill(FACE_HIGHLIGHT_COLOR)
        for dx, dy in DIRECTION_DELTAS.values():
            nx, ny = unit.x + dx, unit.y + dy
            if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                continue
            px = self.ox + nx * GRID_SIZE
            py = self.oy + ny * GRID_SIZE
            self.screen.blit(s, (px, py))
            cx, cy = px + GRID_SIZE // 2, py + GRID_SIZE // 2
            if (dx, dy) == (0, -1):
                pts = [(cx, cy - 18), (cx - 12, cy + 6), (cx + 12, cy + 6)]
            elif (dx, dy) == (0, 1):
                pts = [(cx, cy + 18), (cx - 12, cy - 6), (cx + 12, cy - 6)]
            elif (dx, dy) == (1, 0):
                pts = [(cx + 18, cy), (cx - 6, cy - 12), (cx - 6, cy + 12)]
            else:
                pts = [(cx - 18, cy), (cx + 6, cy - 12), (cx + 6, cy + 12)]
            pygame.draw.polygon(self.screen, (255, 255, 100), pts)

    def draw_game_over_modal(self, game):
        overlay = pygame.Surface((self.ox + GRID_WIDTH * GRID_SIZE, SCREEN_HEIGHT),
                                 pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        d = pygame.Rect(self.ox + 60, SCREEN_HEIGHT // 2 - 140, 440, 280)
        pygame.draw.rect(self.screen, BG_COLOR, d, border_radius=12)
        pygame.draw.rect(self.screen, SELECTED_COLOR, d, 3, border_radius=12)

        if game.game_mode in ("rogue", "campaign"):
            title = "戰役勝利！" if game.campaign_win else "關卡失敗"
        else:
            title = t("game_over_win") if game.campaign_win else t("game_over_lose")
        self._text_centered(title, self.big_font, (255, 215, 0),
                            (d.centerx, d.y + 50))

        if game.general_msg:
            self._text_centered(game.general_msg, self.small_font,
                                (255, 240, 100), (d.centerx, d.y + 100))

        if game.campaign_state.current_generals:
            btn = game.general_save_btn
            btn.y = d.bottom - 60
            btn.x = d.centerx - 120
            btn.width = 240
            hover = btn.collidepoint(pygame.mouse.get_pos())
            if game.general_saved:
                color, label = (80, 130, 80), t("general_saved")
            else:
                color = (100, 180, 220) if hover else (60, 130, 180)
                label = t("general_save_btn")
            pygame.draw.rect(self.screen, color, btn, border_radius=8)
            pygame.draw.rect(self.screen, WHITE, btn, 2, border_radius=8)
            self._text_centered(label, self.font, WHITE, btn.center)

        if game.game_mode not in ("rogue", "campaign"):
            again = game.restart_btn
            again.x = d.centerx - 200
            again.y = d.bottom - 70
            again.width = 180
            again.height = 50
            again_hover = again.collidepoint(pygame.mouse.get_pos())
            again_color = (80, 160, 80) if again_hover else (60, 130, 60)
            pygame.draw.rect(self.screen, again_color, again, border_radius=8)
            pygame.draw.rect(self.screen, WHITE, again, 2, border_radius=8)
            self._text_centered(t("restart_btn"), self.font, WHITE, again.center)

            menu = game.exit_btn
            menu.x = d.centerx + 20
            menu.y = d.bottom - 70
            menu.width = 180
            menu.height = 50
            menu_hover = menu.collidepoint(pygame.mouse.get_pos())
            menu_color = (150, 100, 60) if menu_hover else (120, 80, 50)
            pygame.draw.rect(self.screen, menu_color, menu, border_radius=8)
            pygame.draw.rect(self.screen, WHITE, menu, 2, border_radius=8)
            self._text_centered(t("exit_btn"), self.font, WHITE, menu.center)