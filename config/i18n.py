"""Localisation table and helpers."""

_current_lang = "zh"

_locales = {
    "zh": {
        "app_title": "WAR CHESS",
        "lang_btn": "Language: 繁體中文",
        "select_title": "--- 選擇你的小隊 ---",
        "deploy_title": "--- 部署階段 ---",
        "deploy_finish": "完成部署",
        "deploy_tip1": "1. 點擊右側我方單位選中",
        "deploy_tip2": "2. 點擊下方藍色區域放置",
        "deploy_tip3": "3. 點擊完成部署開始戰鬥",
        "add_btn": "加入",
        "empty_slot": "槽位 {idx} (空)",
        "ready_start": "準備就緒",
        "round_turn": "回合 {turn}",
        "player_turn": "▶ 玩家行動",
        "ai_turn": "▶ AI 行動",
        "choose_facing": "選擇朝向：點相鄰格 / ESC",
        "turn_order": "【行動順序】",
        "end_turn_btn": "回合待命 [Space]",
        "game_over_win": "恭喜勝利！",
        "game_over_lose": "遺憾失敗",
        "restart_btn": "再來一局",
        "exit_btn": "退出到主介面",

        "unit_槍騎兵": "槍騎兵", "unit_弓騎兵": "弓騎兵", "unit_長槍兵": "長槍兵",
        "unit_盾兵": "盾兵", "unit_弩手": "弩手", "unit_弓箭手": "弓箭手",

        "skill_破陣衝撞": "破陣衝撞", "skill_神速連射": "神速連射",
        "skill_拒馬槍陣": "拒馬槍陣", "skill_援護架盾": "援護架盾",
        "skill_精密校準": "精密校準", "skill_火箭壓制": "火箭壓制",
        "skill_換矢": "換矢",
        "skill_no_desc": "此單位沒有主動技能",
        "skill_ap_cost": "AP 消耗 {cost}",

        "pop_charge_on": "開啟衝鋒!", "pop_charge_off": "關閉衝鋒",
        "pop_charge_locked": "衝鋒已鎖定!", "pop_ap_lack": "AP 不足!",
        "pop_water_break": "河流阻斷動能!", "pop_momentum": "動能 +{val}",
        "pop_shield_guard": "盾牌守護!", "pop_counter": "反擊! -{dmg}",
        "pop_strike": "迎擊! -{dmg}", "pop_pike_intercept": "槍陣攔截! -{dmg}",
        "pop_pushed": "擊退!", "pop_stun_pushed": "暈眩擊退!",
        "pop_calib_ready": "校準完畢!", "pop_rapid_ready": "連射準備!",
        "pop_pike_ready": "槍陣已架設!", "pop_guarded_ready": "盾牆已架設!",
        "pop_pierce": "貫穿! -{dmg}", "pop_burn": "火矢! -{dmg}", "pop_rocket": "火箭! -{dmg}",
        "pop_model_loss": "擊殺 {count} 兵!",

        "split_btn": "分裂", "merge_btn": "合併",
        "pop_split": "分裂！兵力 -{half}", "pop_merge": "合併！兵力 +{count}",
        "split_no_space": "九宮格內沒有空格", "split_ap_lack": "AP 不足",
        "split_soldier_lack": "兵力不足 200，無法分裂",
        "merge_invalid": "無法合併（非同兵種或兵力超過上限）",

        "combat_log": "【戰鬥日誌】",
        "hint_bar": "[C] 衝鋒 [E] 技能 [T] 遠射 [R] 裝填 [F] 火矢 [Q] 追擊 [Space] 待命 [Z] 撤銷 [ESC] 取消",
        "ctx_reload": "裝填 (R)",
        "ctx_reload_tip": "花費 50 AP 裝填弩矢；裝填當回合不能再射。",
        "ctx_longshot": "遠射 (T)",
        "ctx_longshot_on": "遠射 ON",
        "ctx_longshot_tip": "花費 25 AP：本回合射程 +1（不給命中、不給傷害）。",
        "ctx_follow_up": "追擊 (Q)",
        "ctx_follow_up_tip": "花費 40 AP：對射程內目標追擊，60% 傷害；移動後或弩不適用。",
        "crossbow_loaded": "弩：已裝填",
        "crossbow_unloaded": "弩：未裝填（按 R 或裝填）",

        "terrain_NORMAL": "平原", "terrain_FOREST": "森林",
        "terrain_MOUNTAIN": "山地", "terrain_RIVER": "河流",
        "terrain_BRIDGE": "橋樑", "terrain_HIGHLAND": "高地",
        "terrain_fx_forest": "遠程傷害 -50%（距離 >1）",
        "terrain_fx_highland": "防禦 +10%（護甲 ×1.1）",
        "terrain_fx_river": "移動消耗 +2（騎兵 +1）",
        "terrain_fx_bridge": "跨河不減速",
        "terrain_fx_mountain": "騎兵不可進入；移動消耗 +2",
        "terrain_frontage": "展開正面 {n}",
        "pop_river_cross": "過河 -2MP", "pop_arrow_used": "箭矢已用盡",
        "log_damage": "{a}→{d} -{dmg}",
        "log_damage_kill": "{a}→{d} -{dmg} (殺{kills})",
        "log_miss": "{a}→{d} MISS",
        "log_counter": "{d}→{a} 反擊-{dmg}",
        "log_pierce": "{a}→{d} 貫穿-{dmg}",
        "log_move": "{u} 移動 -{cost}MP",
        "log_charge_on": "{u} 開啟衝鋒", "log_charge_off": "{u} 關閉衝鋒",
        "log_skill": "{u} 使用 {skill}",
        "morale_label": "士氣",
        "morale_damage_bonus": "傷害 +{pct}%",
        "morale_damage_taken": "受到傷害 +{pct}%",
        "morale_neutral": "無加成",

        "pred_title": "攻擊 {target}",
        "pred_angle_front": "[正面]",
        "pred_angle_flank": "[側面]",
        "pred_angle_rear": "[背刺]",
        "pred_hit": "命中 {hit}%",
        "pred_counter_yes": "反擊: 有",
        "pred_counter_no": "反擊: 無",
        "pred_attack": "攻擊 {target}",
        "pred_kill_count": "擊殺 {kills} 人",
        "pred_hit_pct": "命中 {hit}%",
        "pred_expected_dmg": "期望傷害: {dmg}",
        "pred_blocked_by_melee": "被貼身！無法射擊",

        "main_menu_title": "戰棋模擬器",
        "main_menu_subtitle": "War Chess",
        "start_game_btn": "開始遊戲",
        "settings_btn": "設置",
        "quit_btn": "退出",
        "back_btn": "返回",
        "settings_title": "設置",


        "wt_status_active": "可出征", "wt_status_mourning": "丁憂中({count}局)",
        "wt_status_retired": "已配享", "wt_status_dead": "已陣亡",








    },

    "en": {
        "app_title": "Battle Chess - Massive Armies",
        "lang_btn": "Language: English",
        "select_title": "--- Select Your Squad ---",
        "deploy_title": "--- Deployment Phase ---",
        "deploy_finish": "Finish Deployment",
        "deploy_tip1": "1. Click an ally unit on the right to select.",
        "deploy_tip2": "2. Click the blue zone at the bottom to place.",
        "deploy_tip3": "3. Click Finish to start the battle.",
        "add_btn": "Add",
        "empty_slot": "Slot {idx} (empty)",
        "ready_start": "Ready",
        "round_turn": "Round {turn}",
        "player_turn": "▶ Player Turn",
        "ai_turn": "▶ AI Turn",
        "choose_facing": "Choose facing: click an adjacent tile / ESC",
        "turn_order": "[Turn Order]",
        "end_turn_btn": "End Turn [Space]",
        "game_over_win": "Victory!",
        "game_over_lose": "Defeat",
        "restart_btn": "Play Again",
        "exit_btn": "Back to Menu",

        "unit_槍騎兵": "Cavalry", "unit_弓騎兵": "Horse Archer", "unit_長槍兵": "Lancer",
        "unit_盾兵": "Shieldman", "unit_弩手": "Crossbowman", "unit_弓箭手": "Archer",

        "skill_破陣衝撞": "Breaker Charge", "skill_神速連射": "Rapid Salvo",
        "skill_拒馬槍陣": "Pike Wall", "skill_援護架盾": "Shield Guard",
        "skill_精密校準": "Precision Calibration", "skill_火箭壓制": "Rocket Suppression",
        "skill_換矢": "Switch Arrow",
        "skill_no_desc": "No active skill.",
        "skill_ap_cost": "AP cost {cost}",

        "pop_charge_on": "Charge ON!", "pop_charge_off": "Charge OFF",
        "pop_charge_locked": "Charge locked!", "pop_ap_lack": "Not enough AP!",
        "pop_water_break": "River broke momentum!", "pop_momentum": "Momentum +{val}",
        "pop_shield_guard": "Shield Guard!", "pop_counter": "Counter! -{dmg}",
        "pop_strike": "Intercept! -{dmg}", "pop_pike_intercept": "Pike Intercept! -{dmg}",
        "pop_pushed": "Pushed!", "pop_stun_pushed": "Stun-Pushed!",
        "pop_calib_ready": "Calibrated!", "pop_rapid_ready": "Rapid Salvo Ready!",
        "pop_pike_ready": "Pike Wall Ready!", "pop_guarded_ready": "Shield Wall Ready!",
        "pop_pierce": "Pierce! -{dmg}", "pop_burn": "Burn! -{dmg}", "pop_rocket": "Rocket! -{dmg}",
        "pop_model_loss": "Killed {count}!",

        "split_btn": "Split", "merge_btn": "Merge",
        "pop_split": "Split! -{half}", "pop_merge": "Merge! +{count}",
        "split_no_space": "No empty tile nearby", "split_ap_lack": "Not enough AP",
        "split_soldier_lack": "Need 200+ soldiers to split",
        "merge_invalid": "Cannot merge (different type or over max)",

        "combat_log": "[Combat Log]",
        "hint_bar": "[C] Charge [E] Skill [T] Long shot [R] Reload [F] Fire arrow [Q] Follow-up [Space] End [Z] Undo [ESC] Cancel",
        "ctx_reload": "Reload (R)",
        "ctx_reload_tip": "Spend 50 AP to reload the crossbow; it cannot shoot again this turn.",
        "ctx_longshot": "Long shot (T)",
        "ctx_longshot_on": "Long shot ON",
        "ctx_longshot_tip": "Spend 25 AP: +1 range this turn (no accuracy/damage bonus).",
        "ctx_follow_up": "Follow-up (Q)",
        "ctx_follow_up_tip": "Spend 40 AP: follow-up at 60% damage; not after moving or with a crossbow.",
        "crossbow_loaded": "Crossbow: loaded",
        "crossbow_unloaded": "Crossbow: unloaded (R / Reload)",

        "terrain_NORMAL": "Plain", "terrain_FOREST": "Forest",
        "terrain_MOUNTAIN": "Mountain", "terrain_RIVER": "River",
        "terrain_BRIDGE": "Bridge", "terrain_HIGHLAND": "Highland",
        "terrain_fx_forest": "Ranged damage -50% (dist >1)",
        "terrain_fx_highland": "Defense +10% (armor x1.1)",
        "terrain_fx_river": "Move cost +2 (cavalry +1)",
        "terrain_fx_bridge": "Cross the river at no penalty",
        "terrain_fx_mountain": "Cavalry blocked; move cost +2",
        "terrain_frontage": "Frontage {n}",
        "pop_river_cross": "River -2MP", "pop_arrow_used": "Arrow consumed",
        "log_damage": "{a}→{d} -{dmg}",
        "log_damage_kill": "{a}→{d} -{dmg} ({kills}K)",
        "log_miss": "{a}→{d} MISS",
        "log_counter": "{d}→{a} Counter-{dmg}",
        "log_pierce": "{a}→{d} Pierce-{dmg}",
        "log_move": "{u} move -{cost}MP",
        "log_charge_on": "{u} Charge ON", "log_charge_off": "{u} Charge OFF",
        "log_skill": "{u} uses {skill}",
        "morale_label": "Morale",
        "morale_damage_bonus": "Damage +{pct}%",
        "morale_damage_taken": "Damage taken +{pct}%",
        "morale_neutral": "No bonus",

        "pred_title": "Attack {target}",
        "pred_angle_front": "[FRONT]",
        "pred_angle_flank": "[FLANK]",
        "pred_angle_rear": "[REAR]",
        "pred_hit": "Hit {hit}%",
        "pred_counter_yes": "Counter: Yes",
        "pred_counter_no": "Counter: No",
        "pred_attack": "Attack {target}",
        "pred_kill_count": "Kills {kills}",
        "pred_hit_pct": "Hit {hit}%",
        "pred_expected_dmg": "Expected DMG: {dmg}",
        "pred_blocked_by_melee": "Pinned in melee! Cannot shoot",

        "main_menu_title": "Battle Chess",
        "main_menu_subtitle": "Chinese War Chess",
        "start_game_btn": "Start Game",
        "settings_btn": "Settings",
        "quit_btn": "Quit",
        "back_btn": "Back",
        "settings_title": "Settings",


        "wt_status_active": "Ready", "wt_status_mourning": "Mourning ({count})",
        "wt_status_retired": "Retired", "wt_status_dead": "KIA",








    }
}


def t(key, **kwargs):
    text = _locales[_current_lang].get(key, key)
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text


def toggle_language():
    global _current_lang
    _current_lang = "en" if _current_lang == "zh" else "zh"
