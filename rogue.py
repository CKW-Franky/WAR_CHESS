import random

NODE_COMBAT = "combat"
NODE_ELITE = "elite"
NODE_SHOP = "shop"
NODE_REST = "rest"
NODE_EVENT = "event"
NODE_SIEGE = "siege"
NODE_BOSS = "boss"

NODE_NAMES = {
    NODE_COMBAT: "遭遇戰", NODE_ELITE: "精英戰", NODE_SHOP: "市集",
    NODE_REST: "營地", NODE_EVENT: "未知", NODE_SIEGE: "攻城戰", NODE_BOSS: "決戰",
}

MVP_TEMPLATE = [
    NODE_COMBAT, NODE_EVENT, NODE_SHOP, NODE_REST, NODE_SIEGE,
    NODE_COMBAT, NODE_EVENT, NODE_SHOP, NODE_REST, NODE_BOSS,
]

EVENTS = [
    {"id": "altar", "name": "神秘祭壇", "desc": "一座沾滿鮮血的石祭壇。",
     "options": [
         {"text": "獻血 (-20 士氣, +10% ATK)", "effect": "altar_blood", "value": 10},
         {"text": "祈禱 (+20 士氣)", "effect": "morale", "value": 20},
         {"text": "離開", "effect": "none", "value": 0},
     ]},
    {"id": "knight", "name": "流浪騎士", "desc": "一位騎士請求加入。",
     "options": [
         {"text": "雇用 (-80G, +50 EXP)", "effect": "hire_knight", "value": 50},
         {"text": "拒絕", "effect": "none", "value": 0},
     ]},
    {"id": "plague", "name": "瘟疫村莊", "desc": "村民求助。",
     "options": [
         {"text": "幫助 (-50G, +80 EXP)", "effect": "help_plague", "value": 80},
         {"text": "掠奪 (+100G, -20 士氣)", "effect": "loot_plague", "value": 100},
         {"text": "離開", "effect": "none", "value": 0},
     ]},
    {"id": "caravan", "name": "商隊殘骸", "desc": "被劫掠的馬車。",
     "options": [
         {"text": "搜刮 (30~150G)", "effect": "search_caravan", "value": 0},
         {"text": "離開", "effect": "none", "value": 0},
     ]},
    {"id": "witch", "name": "女巫小屋", "desc": "女巫願意交易。",
     "options": [
         {"text": "買藥水 (-60G, +30% HP)", "effect": "buy_potion", "value": 30},
         {"text": "接受詛咒 (+15% ATK, -20 士氣)", "effect": "witch_curse", "value": 15},
         {"text": "離開", "effect": "none", "value": 0},
     ]},
    {"id": "castle", "name": "古堡寶箱", "desc": "布滿灰塵的寶箱。",
     "options": [
         {"text": "打開（隨機）", "effect": "open_chest", "value": 0},
         {"text": "離開", "effect": "none", "value": 0},
     ]},
    {"id": "crossroad", "name": "十字路口", "desc": "兩條路。",
     "options": [
         {"text": "霧路 (+50 EXP)", "effect": "exp", "value": 50},
         {"text": "燈路 (+80G)", "effect": "gold", "value": 80},
     ]},
    {"id": "stone", "name": "古老石碑", "desc": "刻滿古文。",
     "options": [
         {"text": "閱讀 (+60 EXP)", "effect": "exp", "value": 60},
         {"text": "摧毀 (+60G)", "effect": "gold", "value": 60},
     ]},
]

EVENT_HISTORY_LIMIT = 5


def pick_random_event(exclude_ids=None):
    exclude_ids = exclude_ids or []
    pool = [e for e in EVENTS if e["id"] not in exclude_ids]
    if not pool:
        pool = EVENTS
    return random.choice(pool)


ROGUE_SHOP_ITEMS = {
    "atk_rune":      {"name": "攻擊符文", "desc": "下場 +30% ATK", "cost": 80,  "effect": "atk_buff", "value": 30},
    "def_rune":      {"name": "防禦符文", "desc": "下場 +30% DEF", "cost": 80,  "effect": "def_buff", "value": 30},
    "morale_banner": {"name": "士氣旗幟", "desc": "下場 +30 士氣", "cost": 60,  "effect": "morale_buff", "value": 30},
    "exp_tome":      {"name": "經驗之書", "desc": "全隊 +80 經驗", "cost": 100, "effect": "exp", "value": 80},
    "relic_sword":   {"name": "遠古劍",   "desc": "永久 +5% ATK", "cost": 150, "effect": "permanent_atk", "value": 5},
    "relic_shield":  {"name": "遠古盾",   "desc": "永久 +5% DEF", "cost": 150, "effect": "permanent_def", "value": 5},
}

MINOR_BUFFS = [
    {"id": "p_atk5",   "name": "攻擊 +5%",     "desc": "全隊永久攻擊 +5%", "effect": "permanent_atk", "value": 5},
    {"id": "p_def5",   "name": "防禦 +5%",     "desc": "全隊永久防禦 +5%", "effect": "permanent_def", "value": 5},
    {"id": "p_mor10",  "name": "初始士氣 +10", "desc": "每場 +10 士氣",     "effect": "permanent_morale", "value": 10},
    {"id": "p_ap20",   "name": "初始 AP +20",  "desc": "每場 +20 AP",       "effect": "permanent_ap", "value": 20},
    {"id": "p_shop10", "name": "商店 -10%",    "desc": "商店價格 -10%",     "effect": "permanent_shop_discount", "value": 10},
    {"id": "p_exp20",  "name": "經驗 +20%",    "desc": "所有經驗 +20%",     "effect": "permanent_exp", "value": 20},
]

RARE_BUFFS = [
    {"id": "p_pop2",  "name": "人口 +2",     "desc": "人口上限 +2",       "effect": "permanent_population", "value": 2},
    {"id": "p_atk10", "name": "攻擊 +10%",   "desc": "全隊永久攻擊 +10%", "effect": "permanent_atk", "value": 10},
    {"id": "p_def10", "name": "防禦 +10%",   "desc": "全隊永久防禦 +10%", "effect": "permanent_def", "value": 10},
    {"id": "p_unlock", "name": "解鎖新兵種", "desc": "解鎖一個新兵種",     "effect": "permanent_unlock", "value": 1},
    {"id": "p_ap40",  "name": "初始 AP +40", "desc": "每場 +40 AP",       "effect": "permanent_ap", "value": 40},
]


def pick_rewards(is_boss=False):
    pool = RARE_BUFFS if is_boss else MINOR_BUFFS
    count = min(3, len(pool))
    return random.sample(pool, count)