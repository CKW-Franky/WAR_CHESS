"""Grid, terrain, units, highlights, previews and HUD."""
import pygame
from config import *
from battle.combat import calculate_combat_result, DIRECTION_DELTAS
from battle.movement import get_zoc_tiles, RANGED_CAP
import terrain




class BattleMixin:
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
        elif terrain == "BRIDGE":
            pygame.draw.rect(self.screen, (115, 80, 45),
                             (r.x + 4, cy - 7, r.width - 8, 14))
            for bx in range(r.x + 8, r.right - 4, 8):
                pygame.draw.line(self.screen, (185, 145, 90),
                                 (bx, cy - 7), (bx, cy + 7), 2)
            pygame.draw.line(self.screen, (70, 45, 25),
                             (r.x + 4, cy - 7), (r.right - 4, cy - 7), 2)
            pygame.draw.line(self.screen, (70, 45, 25),
                             (r.x + 4, cy + 7), (r.right - 4, cy + 7), 2)
        elif terrain == "HIGHLAND":
            pygame.draw.polygon(self.screen, (110, 90, 70),
                                [(cx, r.y + 6), (cx - 13, r.bottom - 6), (cx + 13, r.bottom - 6)])
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

        morale_color = (80, 200, 80) if unit.morale >= 50 else (230, 100, 60)
        mw = int((GRID_SIZE - 20) * (unit.morale / float(unit.max_morale)))
        pygame.draw.rect(self.screen, (40, 40, 40),
                         (r.left + 10, r.top + 4, GRID_SIZE - 20, 4))
        pygame.draw.rect(self.screen, morale_color,
                         (r.left + 10, r.top + 4, mw, 4))

        aw = int((GRID_SIZE - 20) * (unit.ap / float(unit.max_ap)))
        pygame.draw.rect(self.screen, (40, 40, 60),
                         (r.left + 10, r.bottom - 5, GRID_SIZE - 20, 3))
        pygame.draw.rect(self.screen, AP_COLOR, (r.left + 10, r.bottom - 5, aw, 3))

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

        dist = max(abs(target.x - unit.x), abs(target.y - unit.y))
        if unit.is_ranged_weapon and dist > 1:
            lines.append((f"接戰 {min(unit.current_soldiers, RANGED_CAP)}"
                          f" / {unit.current_soldiers}", (190, 210, 230)))
            if unit.has_moved:
                lines.append(("移動後射擊 ×0.5", (255, 180, 120)))
            if game.terrain_map[target.y][target.x] == "FOREST":
                lines.append(("森林 ×0.5", (160, 220, 160)))
            block = getattr(target, "ranged_block", 0.0)
            if block:
                lines.append((f"盾牌格擋 ×{1.0 - block:.2f}", (230, 200, 130)))
            weapon = unit.active_weapon
            if weapon is not None and dist > weapon.free_range:
                steps = dist - weapon.free_range
                lines.append((f"距離 {steps} 格外：命中 -{15 * steps}、"
                              f"傷害 ×{max(0.2, 1.0 - 0.2 * steps):.1f}",
                              (230, 190, 150)))

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

    def _draw_tooltip_box(self, mouse_pos, lines, max_width=320):
        line_h = 20
        padding = 8
        wrapped = []
        for text, color in lines:
            if self.small_font.size(text)[0] <= max_width:
                wrapped.append((text, color))
            else:
                for part in self._wrap_text(text, self.small_font, max_width):
                    wrapped.append((part, color))
        bw = min(max(self.small_font.size(text)[0] for text, _ in wrapped) + 20,
                 max_width + 20)
        bh = len(wrapped) * line_h + padding * 2
        bx = max(4, min(mouse_pos[0] + 18, SCREEN_WIDTH - bw - 8))
        by = max(4, min(mouse_pos[1] + 15, SCREEN_HEIGHT - bh - 8))

        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box.fill((0, 0, 0, 225))
        self.screen.blit(box, (bx, by))
        pygame.draw.rect(self.screen, SELECTED_COLOR, (bx, by, bw, bh), 1, border_radius=4)

        for i, (text, color) in enumerate(wrapped):
            self._text(text, self.small_font, color, bx + 10, by + padding + i * line_h)

    def draw_hover_tooltip(self, game):
        if game.game_state not in (GAMEPLAY, AWAITING_DIRECTION):
            return
        m = pygame.mouse.get_pos()
        gx = (m[0] - self.ox) // GRID_SIZE
        gy = (m[1] - self.oy) // GRID_SIZE
        if not (0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT):
            return

        # If the player is pointing at an enemy, the attack-prediction box
        # already occupies the cursor; tile info would overlap it.
        target = game.get_unit_at(gx, gy)
        if target and game.selected_unit and target.team != game.selected_unit.team:
            return

        name = game.terrain_map[gy][gx]
        lines = [(t(f"terrain_{name}"), (255, 220, 100))]
        for key in terrain.effect_keys(name):
            lines.append((t(key), (225, 225, 225)))
        lines.append((t("terrain_frontage", n=terrain.frontage(name)),
                      (180, 200, 220)))
        self._draw_tooltip_box(m, lines)

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
        ctx = None
        follow_up_hover = False
        if active and active.team == "player" and active.is_cavalry:
            charge_btn = game.charge_toggle_btn
            label = t("pop_charge_off") if active.is_charging else t("pop_charge_on")
            color = self._button_color(charge_btn, CHARGE_BUTTON_COLOR, CHARGE_BUTTON_HOVER)
            pygame.draw.rect(self.screen, color, charge_btn, border_radius=6)
            self._text_centered(label, self.small_font, WHITE, charge_btn.center)
        elif active and active.team == "player" and active.name == "弓箭手":
            follow_btn = game.follow_up_btn
            enabled = game.context_enabled(active, "follow_up")
            follow_label, _ = game.context_info(active, "follow_up")
            if enabled:
                color = self._button_color(follow_btn, (70, 130, 90), (95, 170, 115))
            else:
                color = BUTTON_DISABLED_COLOR
            pygame.draw.rect(self.screen, color, follow_btn, border_radius=6)
            self._text_centered(follow_label, self.small_font, WHITE, follow_btn.center)
            follow_up_hover = follow_btn.collidepoint(pygame.mouse.get_pos())

        if active and active.team == "player":
            ctx = game.context_action(active)
            if ctx:
                ctx_btn = game.context_btn
                ctx_label, _ = game.context_info(active, ctx)
                enabled = game.context_enabled(active, ctx)
                if enabled:
                    color = self._button_color(ctx_btn, (70, 120, 165), (95, 160, 210))
                else:
                    color = BUTTON_DISABLED_COLOR
                pygame.draw.rect(self.screen, color, ctx_btn, border_radius=6)
                self._text_centered(ctx_label, self.small_font, WHITE, ctx_btn.center)

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

        # Draw the skill description last so it sits above the other buttons.
        if (active and active.team == "player"
                and game.skill_btn.collidepoint(pygame.mouse.get_pos())):
            skill_label = t(f"skill_{active.skill_name}") if active.skill_name else "技能"
            desc = getattr(active, "skill_desc", "") or t("skill_no_desc")
            lines = [(skill_label, (255, 220, 100))]
            for part in self._wrap_text(desc, self.small_font, 300):
                lines.append((part, (225, 225, 225)))
            if getattr(active, "skill_cost", 0):
                lines.append((t("skill_ap_cost", cost=active.skill_cost),
                              (180, 200, 220)))
            self._draw_tooltip_box(pygame.mouse.get_pos(), lines)

        if (active and active.team == "player" and ctx
                and game.context_btn.collidepoint(pygame.mouse.get_pos())):
            ctx_label, ctx_tip = game.context_info(active, ctx)
            lines = [(ctx_label, (255, 220, 100))]
            for part in self._wrap_text(ctx_tip, self.small_font, 300):
                lines.append((part, (225, 225, 225)))
            self._draw_tooltip_box(pygame.mouse.get_pos(), lines)

        if active and active.team == "player" and follow_up_hover:
            follow_label, follow_tip = game.context_info(active, "follow_up")
            lines = [(follow_label, (255, 220, 100))]
            for part in self._wrap_text(follow_tip, self.small_font, 300):
                lines.append((part, (225, 225, 225)))
            self._draw_tooltip_box(pygame.mouse.get_pos(), lines)

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
        morale_color = (80, 200, 80) if unit.morale >= 50 else (230, 100, 60)
        y = self._stat_bar(pad, y, 260, t("morale_label"), unit.morale,
                           unit.max_morale, morale_color)
        if unit.morale > 50:
            pct = round((unit.morale - 50) * 0.4)
            morale_text = t("morale_damage_bonus", pct=pct)
        elif unit.morale < 50:
            pct = round((50 - unit.morale) * 1.0)
            morale_text = t("morale_damage_taken", pct=pct)
        else:
            morale_text = t("morale_neutral")
        self._text(morale_text, self.small_font, morale_color, pad, y)
        y += 18
        y = self._stat_bar(pad, y, 260, "AP", unit.ap, unit.max_ap, AP_COLOR)

        info = (f"ATK {unit.attack_power} DEF {unit.defense} "
                f"RNG {unit.get_actual_range(None)}")
        self._text(info, self.small_font, TEXT_COLOR, pad, y)
        y += 20

        gear = unit.loadout_summary() if hasattr(unit, "loadout_summary") else ""
        if gear:
            for part in self._wrap_text(gear, self.small_font, 275):
                self._text(part, self.small_font, (170, 185, 210), pad, y)
                y += 18

        weapon = unit.active_weapon
        if weapon is not None and weapon.reload_required:
            state = t("crossbow_loaded") if unit.loaded else t("crossbow_unloaded")
            self._text(state, self.small_font,
                       (200, 230, 200) if unit.loaded else (255, 190, 120), pad, y)
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

        title = t("game_over_win") if game.player_won else t("game_over_lose")
        self._text_centered(title, self.big_font, (255, 215, 0),
                            (d.centerx, d.y + 50))

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
