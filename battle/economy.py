"""AP-spending utility actions (reload, fire arrow, swap, follow-up)."""
import equipment
from config import *  # noqa: F401,F403
from battle.combat import calculate_combat_result
from battle.actions import consume_arrow


class EconomyMixin:
    def reload_crossbow(self, unit):
        weapon = unit.active_weapon
        if weapon is None or not weapon.reload_required:
            self.add_damage_popup("此武器不需裝填", unit.x, unit.y, is_miss=True)
            return False
        if unit.loaded:
            self.add_damage_popup("已裝填", unit.x, unit.y, is_miss=True)
            return False
        if unit.ap < equipment.RELOAD_AP:
            self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
            return False
        unit.ap -= equipment.RELOAD_AP
        unit.loaded = True
        self.add_damage_popup("裝填完成", unit.x, unit.y, is_crit=True)
        return True

    def toggle_fire_arrow(self, unit):
        weapon = unit.active_weapon
        if weapon is None or not weapon.fire_arrow:
            self.add_damage_popup("此武器不能點火", unit.x, unit.y, is_miss=True)
            return False
        if unit.fire_arrow or unit.archer_arrow == "fire":
            unit.archer_arrow = "armor_pierce"
            unit.fire_arrow = False
            self.add_damage_popup("火矢關閉", unit.x, unit.y, is_miss=True)
            return True
        if unit.ap < 10:
            self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
            return False
        unit.ap -= 10
        unit.archer_arrow = "fire"
        unit.fire_arrow = True
        self.add_damage_popup("火矢點燃", unit.x, unit.y, is_crit=True)
        return True

    def follow_up_attack(self, unit):
        if unit.has_moved:
            self.add_damage_popup("移動後不能追擊", unit.x, unit.y, is_miss=True)
            return False
        if getattr(unit, "follow_up_used", False):
            self.add_damage_popup("本回合已追擊", unit.x, unit.y, is_miss=True)
            return False
        weapon = unit.active_weapon
        if weapon is not None and weapon.reload_required:
            self.add_damage_popup("弩不適用追擊", unit.x, unit.y, is_miss=True)
            return False
        if unit.ap < equipment.FOLLOW_UP_AP:
            self.add_damage_popup(t("pop_ap_lack"), unit.x, unit.y, is_miss=True)
            return False
        atk_range = unit.get_actual_range(self)
        targets = [u for u in self.units
                   if u.is_alive() and u.team != unit.team
                   and max(abs(u.x - unit.x), abs(u.y - unit.y)) <= atk_range]
        if not targets:
            self.add_damage_popup("射程內沒有目標", unit.x, unit.y, is_miss=True)
            return False
        target = min(targets, key=lambda u: (
            u.soldier_ratio, max(abs(u.x - unit.x), abs(u.y - unit.y))))
        result = calculate_combat_result(unit, target, self, "NORMAL")
        consume_arrow(unit)
        dmg = max(1, int(result["predicted_damage"] * equipment.FOLLOW_UP_MULT))
        unit.ap -= equipment.FOLLOW_UP_AP
        unit.follow_up_used = True
        target.take_damage(dmg, unit, self)
        self.add_damage_popup(f"追擊! {dmg}", target.x, target.y, is_crit=True)
        self.trigger_visual_arrow((unit.x, unit.y), (target.x, target.y))
        self.check_game_over()
        return True
