import pygame

SCREEN_WIDTH = 1088
SCREEN_HEIGHT = 960
GRID_SIZE = 48
GRID_WIDTH = 16
GRID_HEIGHT = 20
CHARGE_TOGGLE_AP = 20

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRID_COLOR = (120, 120, 120)
DIVIDER_COLOR = (255, 215, 0)
PLAYER_COLOR = (70, 130, 230)
AI_COLOR = (220, 70, 70)
MOVE_HIGHLIGHT_COLOR = (100, 255, 100, 140)
ATTACK_HIGHLIGHT_COLOR = (255, 80, 80, 160)
PIERCE_HIGHLIGHT_COLOR = (220, 80, 220, 190)
SKILL_HIGHLIGHT_COLOR = (255, 200, 50, 180)
DEPLOY_HIGHLIGHT_COLOR = (70, 130, 230, 100)
FACE_HIGHLIGHT_COLOR = (255, 255, 100, 150)
SELECTED_COLOR = (255, 220, 0)
TEXT_COLOR = (240, 240, 240)
BG_COLOR = (40, 44, 52)
INFO_PANEL_COLOR = (25, 28, 34)
LOG_PANEL_COLOR = (18, 20, 26)
BUTTON_COLOR = (50, 150, 255)
BUTTON_HOVER_COLOR = (80, 180, 255)
BUTTON_DISABLED_COLOR = (90, 90, 90)
CHARGE_BUTTON_COLOR = (230, 120, 30)
CHARGE_BUTTON_HOVER = (255, 150, 50)
SKILL_BUTTON_COLOR = (180, 70, 220)
SKILL_BUTTON_HOVER = (210, 100, 255)
HP_COLOR = (80, 200, 80)
MODEL_COLOR = (100, 160, 255)
MORALE_COLORS = {
    "high": (230, 210, 0),
    "stable": (200, 160, 50),
    "shaken": (210, 100, 50),
    "breaking": (220, 30, 30),
    "routing": (120, 120, 120),
}
AP_COLOR = (50, 130, 230)
MP_COLOR = (50, 200, 200)
TERRAIN_COLORS = {
    "NORMAL": (60, 70, 80),
    "FOREST": (34, 110, 56),
    "MOUNTAIN": (115, 95, 85),
    "RIVER": (30, 115, 190),
    "ROAD": (120, 110, 90),
    "SWAMP": (50, 80, 60),
    "HIGHLAND": (140, 120, 100),
    "VILLAGE": (150, 120, 90),
    "RUINS": (90, 80, 75),
    "FENCE": (100, 70, 50),
    "BRIDGE": (140, 100, 60),
    "WALL": (110, 105, 95),
    "GATE": (150, 110, 60),
    "BARRACKS": (90, 110, 90),
    "HOUSE": (120, 90, 60),
    "CATAPULT": (100, 90, 70),
}


MAIN_MENU = "MAIN_MENU"
SETTINGS = "SETTINGS"
MODE_SELECT = "MODE_SELECT"
WAR_TEMPLE = "WAR_TEMPLE"
META_SCREEN = "META_SCREEN"
SLOT_SELECT = "SLOT_SELECT"
GENERAL_SELECT = "GENERAL_SELECT"
ROGUE_MAP = "ROGUE_MAP"
EVENT_SCREEN = "EVENT_SCREEN"
ROGUE_SHOP = "ROGUE_SHOP"
ROGUE_REST = "ROGUE_REST"
ROSTER_SCREEN = "ROSTER_SCREEN"
SIEGE_REWARD = "SIEGE_REWARD"
CAPTIVE_SCREEN = "CAPTIVE_SCREEN"
CAMPAIGN_MAP = "CAMPAIGN_MAP"
CAMPAIGN_LEVEL_INTRO = "CAMPAIGN_LEVEL_INTRO"
CAMPAIGN_PATH_SELECT = "CAMPAIGN_PATH_SELECT"
SELECTION_SCREEN = "SELECTION_SCREEN"
DEPLOYMENT_STAGE = "DEPLOYMENT_STAGE"
GAMEPLAY = "GAMEPLAY"
GAME_OVER = "GAME_OVER"
AWAITING_DIRECTION = "AWAITING_DIRECTION"


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
        "morale_high": "高昂", "morale_stable": "穩定", "morale_shaken": "動搖",
        "morale_breaking": "瀕臨崩潰", "morale_routing": "潰散",

        "combat_log": "【戰鬥日誌】",
        "hint_bar": "[C] 衝鋒 [E] 技能 [Space] 待命 [Z] 撤銷 [ESC] 取消",

        "terrain_NORMAL": "平原", "terrain_FOREST": "森林",
        "terrain_MOUNTAIN": "山地", "terrain_RIVER": "河流",
        "terrain_ROAD": "道路", "terrain_SWAMP": "沼澤",
        "terrain_HIGHLAND": "高地", "terrain_VILLAGE": "村莊",
        "terrain_RUINS": "廢墟", "terrain_FENCE": "柵欄",
        "terrain_BRIDGE": "橋樑",
        "terrain_WALL": "城牆", "terrain_GATE": "城門",
        "terrain_BARRACKS": "兵營", "terrain_HOUSE": "民房",
        "terrain_CATAPULT": "投石機",
        "pop_river_cross": "過河 -2MP", "pop_arrow_used": "箭矢已用盡",
        "log_damage": "{a}→{d} -{dmg}",
        "log_damage_kill": "{a}→{d} -{dmg} (殺{kills})",
        "log_miss": "{a}→{d} MISS",
        "log_counter": "{d}→{a} 反擊-{dmg}",
        "log_pierce": "{a}→{d} 貫穿-{dmg}",
        "log_move": "{u} 移動 -{cost}MP",
        "log_charge_on": "{u} 開啟衝鋒", "log_charge_off": "{u} 關閉衝鋒",
        "log_skill": "{u} 使用 {skill}", "log_routing": "{u} 潰散!",

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
        "war_temple_btn": "武廟",
        "meta_btn": "靈魂祭壇",
        "settings_btn": "設置",
        "quit_btn": "退出",
        "back_btn": "返回",
        "settings_title": "設置",
        "mode_select_title": "選擇模式",
        "quick_mode_title": "快速模式",
        "quick_mode_desc": "自由選 5 單位，單場戰鬥",
        "campaign_mode_title": "遠征模式",
        "campaign_mode_desc": "肉鴿地圖，10 層遠征",
        "mode_beta_badge": "測試版",
        "mode_beta_note": "遠征模式仍在開發中，可能出現錯誤或數值失衡",

        "meta_title": "【靈魂祭壇】",
        "meta_soul": "靈魂點數: {points}",
        "meta_tab_skills": "技能樹", "meta_tab_achievements": "成就", "meta_tab_stats": "統計",
        "meta_upgrade": "升級", "meta_max": "已滿",
        "meta_stat_kills": "總擊殺", "meta_stat_battles": "總戰鬥",
        "meta_stat_wins": "勝場", "meta_stat_sieges": "攻城勝利",

        "war_temple_title": "【武廟】",
        "war_temple_main": "正殿", "war_temple_mourning": "丁憂閣",
        "war_temple_fame": "配享殿", "war_temple_martyr": "英烈祠",
        "war_temple_empty": "空無一人",
        "wt_status_active": "可出征", "wt_status_mourning": "丁憂中({count}局)",
        "wt_status_retired": "已配享", "wt_status_dead": "已陣亡",

        "general_title": "【將領】",
        "general_list_title": "【將領列表】",
        "general_appoint_btn": "任命為隊長",
        "general_appointed": "已任命: {name}",
        "general_no_selected": "請先選中我方單位",
        "general_no_available": "無可任命將領",
        "general_saved": "已保存至武廟",
        "general_save_btn": "保存至武廟",
        "general_generated": "新將領: {name}",
        "general_merit_gain": "戰功 +{val}",
        "general_rank": "官職: {rank}",
        "general_select_title": "選擇出征將領",
        "general_select_new": "招募新將領",
        "general_select_confirm": "確認出征",
        "general_recruit_used": "招募機會已用完",

        "captive_title": "【俘虜敵將】",
        "captive_desc": "敵將 {name} 願降，是否招降？",
        "captive_cost": "招錄費: {cost} 金",
        "captive_chance": "成功率: {chance}%",
        "captive_accept": "招降", "captive_refuse": "拒絕",
        "captive_success": "{name} 加入我軍！", "captive_fail": "{name} 拒絕投降",
        "captive_gold_lack": "金幣不足，俘虜已釋放",

        "rogue_map_title": "【遠征地圖】測試版",
        "rogue_act": "第 {act} 幕",
        "rogue_gold": "金幣: {gold}",
        "rogue_pop": "人口: {pop}",
        "rogue_click": "點擊金色節點進入",

        "event_title": "【未知事件】",
        "event_result": "結果: {msg}",
        "event_continue": "繼續",

        "rest_title": "【營地】",
        "rest_heal": "恢復士氣 (+30)", "rest_train": "訓練 (+80 EXP)",
        "rest_gold": "搜刮 (+40G)", "rest_leave": "離開",

        "siege_reward_title": "攻城勝利！",
        "siege_reward_desc": "選擇永久增益:",
        "siege_reward_continue": "繼續",

        "shop_title": "【市集】",
        "shop_buy": "購買", "shop_leave": "離開",

        "slot_select_title": "選擇存檔",
        "slot_label": "存檔 {id}",
        "slot_empty": "空的——開始新遊戲",
        "slot_soul": "靈魂: {val}",
        "slot_act": "第 {act} 幕",
        "slot_gold": "金幣: {val}",
        "slot_generals": "將領: {val}",
        "slot_unlocked": "解鎖兵種: {val}",
        "slot_battles": "戰鬥次數: {val}",
        "slot_ascension": "週目: {val}",
        "slot_enter": "進入",
        "slot_continue": "繼續",
        "slot_new": "開新局",
        "slot_delete": "刪除",
        "slot_delete_confirm_title": "確認刪除",
        "slot_delete_confirm_msg": "確定要刪除存檔 {id} 嗎？此操作不可恢復。",
        "slot_delete_yes": "確定刪除",
        "slot_delete_no": "取消",
        "slot_back": "返回",
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
        "morale_high": "High", "morale_stable": "Stable", "morale_shaken": "Shaken",
        "morale_breaking": "Breaking", "morale_routing": "Routing",

        "combat_log": "[Combat Log]",
        "hint_bar": "[C] Charge [E] Skill [Space] End [Z] Undo [ESC] Cancel",

        "terrain_NORMAL": "Plain", "terrain_FOREST": "Forest",
        "terrain_MOUNTAIN": "Mountain", "terrain_RIVER": "River",
        "terrain_ROAD": "Road", "terrain_SWAMP": "Swamp",
        "terrain_HIGHLAND": "Highland", "terrain_VILLAGE": "Village",
        "terrain_RUINS": "Ruins", "terrain_FENCE": "Fence",
        "terrain_BRIDGE": "Bridge",
        "terrain_WALL": "Wall", "terrain_GATE": "Gate",
        "terrain_BARRACKS": "Barracks", "terrain_HOUSE": "House",
        "terrain_CATAPULT": "Catapult",
        "pop_river_cross": "River -2MP", "pop_arrow_used": "Arrow consumed",
        "log_damage": "{a}→{d} -{dmg}",
        "log_damage_kill": "{a}→{d} -{dmg} ({kills}K)",
        "log_miss": "{a}→{d} MISS",
        "log_counter": "{d}→{a} Counter-{dmg}",
        "log_pierce": "{a}→{d} Pierce-{dmg}",
        "log_move": "{u} move -{cost}MP",
        "log_charge_on": "{u} Charge ON", "log_charge_off": "{u} Charge OFF",
        "log_skill": "{u} uses {skill}", "log_routing": "{u} ROUTS!",

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
        "war_temple_btn": "War Temple",
        "meta_btn": "Soul Altar",
        "settings_btn": "Settings",
        "quit_btn": "Quit",
        "back_btn": "Back",
        "settings_title": "Settings",
        "mode_select_title": "Select Mode",
        "quick_mode_title": "Quick Match",
        "quick_mode_desc": "Pick 5 units, single battle",
        "campaign_mode_title": "Expedition",
        "campaign_mode_desc": "Roguelike map, 10 layers",
        "mode_beta_badge": "BETA",
        "mode_beta_note": "Expedition mode is still in development and may contain bugs or unbalanced values",

        "meta_title": "[Soul Altar]",
        "meta_soul": "Soul Points: {points}",
        "meta_tab_skills": "Skills", "meta_tab_achievements": "Achievements", "meta_tab_stats": "Stats",
        "meta_upgrade": "Upgrade", "meta_max": "MAX",
        "meta_stat_kills": "Total Kills", "meta_stat_battles": "Total Battles",
        "meta_stat_wins": "Wins", "meta_stat_sieges": "Sieges Won",

        "war_temple_title": "[War Temple]",
        "war_temple_main": "Main Hall", "war_temple_mourning": "Mourning Hall",
        "war_temple_fame": "Hall of Fame", "war_temple_martyr": "Martyr Shrine",
        "war_temple_empty": "Empty",
        "wt_status_active": "Ready", "wt_status_mourning": "Mourning ({count})",
        "wt_status_retired": "Retired", "wt_status_dead": "KIA",

        "general_title": "[General]",
        "general_list_title": "[General Roster]",
        "general_appoint_btn": "Appoint as Captain",
        "general_appointed": "Appointed: {name}",
        "general_no_selected": "Select an ally unit first",
        "general_no_available": "No available general",
        "general_saved": "Saved to War Temple",
        "general_save_btn": "Save to War Temple",
        "general_generated": "New General: {name}",
        "general_merit_gain": "Merit +{val}",
        "general_rank": "Rank: {rank}",
        "general_select_title": "Select Starting General",
        "general_select_new": "Recruit New General",
        "general_select_confirm": "Confirm",
        "general_recruit_used": "Recruit chance used",

        "captive_title": "[Captive General]",
        "captive_desc": "Enemy general {name} offers to surrender. Recruit?",
        "captive_cost": "Cost: {cost}G",
        "captive_chance": "Success rate: {chance}%",
        "captive_accept": "Recruit", "captive_refuse": "Refuse",
        "captive_success": "{name} joins your army!", "captive_fail": "{name} refuses to surrender",
        "captive_gold_lack": "Not enough gold; captive released",

        "rogue_map_title": "[Expedition Map] BETA",
        "rogue_act": "Act {act}",
        "rogue_gold": "Gold: {gold}",
        "rogue_pop": "Pop: {pop}",
        "rogue_click": "Click a glowing node to enter",

        "event_title": "[Unknown Event]",
        "event_result": "Result: {msg}",
        "event_continue": "Continue",

        "rest_title": "[Camp]",
        "rest_heal": "Recover morale (+30)", "rest_train": "Train (+80 EXP)",
        "rest_gold": "Scavenge (+40G)", "rest_leave": "Leave",

        "siege_reward_title": "Siege Victory!",
        "siege_reward_desc": "Choose a permanent bonus:",
        "siege_reward_continue": "Continue",

        "shop_title": "[Market]",
        "shop_buy": "Buy", "shop_leave": "Leave",

        "slot_select_title": "Select Save Slot",
        "slot_label": "Slot {id}",
        "slot_empty": "Empty — Start a New Game",
        "slot_soul": "Soul: {val}",
        "slot_act": "Act {act}",
        "slot_gold": "Gold: {val}",
        "slot_generals": "Generals: {val}",
        "slot_unlocked": "Units Unlocked: {val}",
        "slot_battles": "Battles: {val}",
        "slot_ascension": "Ascension: {val}",
        "slot_enter": "Enter",
        "slot_continue": "Continue",
        "slot_new": "New Game",
        "slot_delete": "Delete",
        "slot_delete_confirm_title": "Confirm Delete",
        "slot_delete_confirm_msg": "Delete Slot {id}? This cannot be undone.",
        "slot_delete_yes": "Delete",
        "slot_delete_no": "Cancel",
        "slot_back": "Back",
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