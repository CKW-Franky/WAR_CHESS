"""Equipment data layer for Battle_Chess.

This module is the single source of truth for equipment data and the pure
formulas derived from it.  It deliberately has **no imports from game modules**
(``combat``, ``game``, ``units``); everything here is immutable data or a pure
function so it can be used by the battle loop.
migration, UI previews and tests alike.

Source precedence
-----------------
* ``design/equipment_v2.md`` wins for tiers, melee weapons, shields, armor and
  horses.
* ``design/equipment_v3.md`` wins for 短弓 / 長弓 / 弩 / 標槍, free range,
  crossbow reload and fire arrows.

Provenance note
---------------
v2 does not list AP costs for the three melee weapon skills.  The AP values in
v1 (拒馬槍陣 25, 勾盾 35, 陌刀斬 55) are retained here where v2/v3 do not
override them.

IDs are stable ASCII ``snake_case``.  Chinese display names live in ``name``;
never use a name as a save/logic key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Sequence, Tuple

__all__ = [
    # constants
    "FLOOR_RATIO", "FACTOR_CUT", "FACTOR_PIERCE", "FACTOR_BLUNT",
    "CROSSBOW_FACTOR", "FREE_RANGE_ACC_PENALTY", "FREE_RANGE_DMG_PENALTY",
    "DMG_PENALTY_CAP", "SHIELD_BLOCK_CAP", "FOLLOW_UP_AP", "FOLLOW_UP_MULT",
    "SWAP_AP", "MOUNTED_SWAP_AP", "RELOAD_AP", "FIRE_ARROW_PIERCE_MULT",
    "FIRE_RATTAN_MULT", "BASE_MP",
    # hand / kind / facing values
    "HAND_ONE", "HAND_TWO", "SKILL_ACTIVE", "SKILL_PASSIVE", "SKILL_TOGGLE",
    "SKILL_AURA", "FACING_UP", "FACING_RIGHT", "FACING_DOWN", "FACING_LEFT",
    # dataclasses
    "Weapon", "Shield", "Armor", "Horse", "Tier", "Skill", "Quality",
    # tables
    "TIERS", "WEAPONS", "SHIELDS", "ARMORS", "HORSES", "QUALITIES", "SKILLS",
    # indexes
    "TIERS_BY_ID", "TIERS_BY_NAME", "WEAPONS_BY_ID", "WEAPONS_BY_NAME",
    "SHIELDS_BY_ID", "SHIELDS_BY_NAME", "ARMORS_BY_ID", "ARMORS_BY_NAME",
    "HORSES_BY_ID", "HORSES_BY_NAME", "QUALITIES_BY_ID", "QUALITIES_BY_NAME",
    "SKILLS_BY_ID", "SKILLS_BY_NAME",
    # lookups
    "resolve_tier", "get_tier", "resolve_weapon", "get_weapon",
    "resolve_shield", "get_shield", "resolve_armor", "get_armor",
    "resolve_horse", "get_horse", "resolve_quality", "get_quality",
    "resolve_skill", "get_skill", "quality_multiplier",
    # formulas / helpers
    "per_hit_damage", "hit_chance", "damage_multiplier", "shield_melee_armor",
    "shield_ranged_block", "aura_targets", "build_stats", "validate_equipment",
]

# ---------------------------------------------------------------------------
# Constants (v2 core formula + v3 ranged rules)
# ---------------------------------------------------------------------------

FLOOR_RATIO = 0.10
FACTOR_CUT = 1.00
FACTOR_PIERCE = 0.70
FACTOR_BLUNT = 0.30
CROSSBOW_FACTOR = 0.40

FREE_RANGE_ACC_PENALTY = 15
FREE_RANGE_DMG_PENALTY = 0.20
DMG_PENALTY_CAP = 0.80

SHIELD_BLOCK_CAP = 0.60
FOLLOW_UP_AP = 40
FOLLOW_UP_MULT = 0.60
SWAP_AP = 50
MOUNTED_SWAP_AP = 70
RELOAD_AP = 50

FIRE_ARROW_PIERCE_MULT = 0.70
FIRE_RATTAN_MULT = 2.00

#: Base MP before mount / armor / weight penalties (v2 section 7.3 + workbook).
BASE_MP = 4

HAND_ONE = "one_hand"
HAND_TWO = "two_hand"

SKILL_ACTIVE = "active"
SKILL_PASSIVE = "passive"
SKILL_TOGGLE = "toggle"
SKILL_AURA = "aura"

#: Facing values match ``combat.DIR_*`` without importing combat.
FACING_UP = 0
FACING_RIGHT = 1
FACING_DOWN = 2
FACING_LEFT = 3

_FACING_DELTAS = {
    FACING_UP: (0, -1),
    FACING_RIGHT: (1, 0),
    FACING_DOWN: (0, 1),
    FACING_LEFT: (-1, 0),
}

_FACING_ALIASES = {
    "up": FACING_UP, "north": FACING_UP, "上": FACING_UP, "北": FACING_UP,
    "right": FACING_RIGHT, "east": FACING_RIGHT, "右": FACING_RIGHT, "東": FACING_RIGHT,
    "down": FACING_DOWN, "south": FACING_DOWN, "下": FACING_DOWN, "南": FACING_DOWN,
    "left": FACING_LEFT, "west": FACING_LEFT, "左": FACING_LEFT, "西": FACING_LEFT,
}


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Tier:
    """A troop-quality tier (人／五階)."""

    id: str
    name: str
    attack_mult: float
    accuracy: int
    max_active_skills: int
    hp_per_soldier: int
    power_cost: int


@dataclass(frozen=True)
class Weapon:
    """A weapon.

    ``hand`` is :data:`HAND_ONE` or :data:`HAND_TWO`.  ``free_range`` is the
    distance (in tiles) at which no ranged penalty is applied; melee weapons set
    it to their reach so the same formulas stay well-defined at range 1/2.
    """

    id: str
    name: str
    hand: str
    cut: int
    pierce: int
    blunt: int
    range: int
    weight: int
    accuracy: int
    skill_id: str
    power_cost: int
    free_range: int
    pierce_factor: float = FACTOR_PIERCE
    ranged: bool = False
    mounted: bool = False
    fire_arrow: bool = False
    reload_required: bool = False
    ammo: int = 0
    toggle_skill_id: Optional[str] = None
    extra_skill_id: Optional[str] = None

    @property
    def total_attack(self) -> int:
        return self.cut + self.pierce + self.blunt

    @property
    def is_one_handed(self) -> bool:
        return self.hand == HAND_ONE

    @property
    def is_two_handed(self) -> bool:
        return self.hand == HAND_TWO

    @property
    def hand_label(self) -> str:
        """Chinese hand label for UI (單／雙); logic uses :attr:`hand`."""
        return "單" if self.hand == HAND_ONE else "雙"

    @property
    def is_melee(self) -> bool:
        return not self.ranged

    @property
    def is_ranged(self) -> bool:
        return self.ranged

    @property
    def skill(self) -> "Skill":
        return SKILLS_BY_ID[self.skill_id]

    @property
    def toggle_skill(self) -> Optional["Skill"]:
        if self.toggle_skill_id is None:
            return None
        return SKILLS_BY_ID[self.toggle_skill_id]

    @property
    def extra_skill(self) -> Optional["Skill"]:
        if self.extra_skill_id is None:
            return None
        return SKILLS_BY_ID[self.extra_skill_id]


@dataclass(frozen=True)
class Shield:
    """A shield.  Only passive / aura skills exist in v2.1."""

    id: str
    name: str
    melee_armor: int
    ranged_block: float
    accuracy: int
    weight: int
    power_cost: int
    mounted_accuracy: int = 0
    mountable: bool = True
    aura_block: float = 0.0
    skill_id: Optional[str] = None

    @property
    def skill(self) -> Optional["Skill"]:
        if self.skill_id is None:
            return None
        return SKILLS_BY_ID[self.skill_id]


@dataclass(frozen=True)
class Armor:
    """Body armor.  ``ranged_accuracy`` is the penalty applied to *incoming*
    ranged attacks (negative or zero)."""

    id: str
    name: str
    armor: int
    weight: int
    ranged_accuracy: int
    mp: int
    power_cost: int
    min_tier_id: Optional[str] = None
    feature: str = ""
    fire_vulnerable: bool = False


@dataclass(frozen=True)
class Horse:
    """A mount."""

    id: str
    name: str
    mp_bonus: int
    charge_mult: float
    power_cost: int
    min_tier_id: Optional[str] = None


@dataclass(frozen=True)
class Quality:
    """Crafting quality; multiplies only the three attack channels."""

    id: str
    name: str
    multiplier: float
    description: str = ""


@dataclass(frozen=True)
class Skill:
    """A weapon / shield skill (active, passive, toggle or aura).

    Extra numeric fields describe the rules so callers do not need to hard-code
    the v2/v3 text:

    ``damage_mult``  damage multiplier per hit
    ``hits``         number of resolutions (速射 = 2)
    ``range_bonus``  temporary range bonus (遠射 = +1)
    ``accuracy_bonus`` temporary accuracy bonus
    ``panic_turns``  panic duration applied on hit
    ``pierce_mult``  multiplier to the pierce channel (火矢 = 0.70)
    ``armor_ignore`` fraction of armor ignored (陌刀斬 = 0.30)
    """

    id: str
    name: str
    kind: str
    ap_cost: int = 0
    description: str = ""
    damage_mult: float = 1.0
    hits: int = 1
    range_bonus: int = 0
    accuracy_bonus: int = 0
    panic_turns: int = 0
    pierce_mult: float = 1.0
    armor_ignore: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.kind == SKILL_ACTIVE


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

TIERS: Tuple[Tier, ...] = (
    Tier(id="veteran", name="老兵", attack_mult=1.00, accuracy=84,
         max_active_skills=1, hp_per_soldier=18, power_cost=4),
    Tier(id="elite", name="精銳", attack_mult=1.06, accuracy=90,
         max_active_skills=1, hp_per_soldier=21, power_cost=7),
)

# Public-demo palette: 刀、長槍、騎槍、短弓、長弓、弩。
WEAPONS: Tuple[Weapon, ...] = (
    Weapon(id="dao", name="刀", hand=HAND_ONE, cut=11, pierce=3, blunt=1,
           range=1, weight=2, accuracy=0, skill_id="guard", power_cost=3,
           free_range=1),
    Weapon(id="lance", name="騎槍", hand=HAND_ONE, cut=3, pierce=9, blunt=1,
           range=1, weight=3, accuracy=-5, skill_id="break_charge", power_cost=4,
           free_range=1, mounted=True),
    Weapon(id="long_spear", name="長槍", hand=HAND_TWO, cut=3, pierce=13,
           blunt=1, range=2, weight=5, accuracy=-5, skill_id="pike_wall",
           power_cost=5, free_range=2),
    Weapon(id="short_bow", name="短弓", hand=HAND_TWO, cut=1, pierce=9,
           blunt=0, range=4, weight=2, accuracy=0, skill_id="rapid_fire",
           power_cost=4, free_range=4, ranged=True, mounted=True,
           fire_arrow=True, toggle_skill_id="fire_arrow"),
    Weapon(id="long_bow", name="長弓", hand=HAND_TWO, cut=1, pierce=11,
           blunt=0, range=6, weight=3, accuracy=5, skill_id="fire_arrow",
           power_cost=5, free_range=5, ranged=True, fire_arrow=True,
           extra_skill_id="long_shot"),
    Weapon(id="crossbow", name="弩", hand=HAND_TWO, cut=0,
           pierce=14, blunt=0, range=5, weight=5, accuracy=10,
           skill_id="calibration", power_cost=7, free_range=5,
           pierce_factor=CROSSBOW_FACTOR, ranged=True, reload_required=True,
           extra_skill_id="reload"),
)

SHIELDS: Tuple[Shield, ...] = (
    Shield(id="small_shield", name="小盾", melee_armor=1, ranged_block=0.12,
           accuracy=0, weight=1, power_cost=1, mounted_accuracy=0,
           mountable=True, aura_block=0.0, skill_id="cavalry_shield"),
    Shield(id="medium_shield", name="中盾", melee_armor=2, ranged_block=0.25,
           accuracy=-3, weight=2, power_cost=2, mounted_accuracy=-3,
           mountable=True, aura_block=0.0, skill_id="standard_shield"),
    Shield(id="large_shield", name="大盾", melee_armor=3, ranged_block=0.40,
           accuracy=-8, weight=6, power_cost=4, mounted_accuracy=0,
           mountable=False, aura_block=0.40, skill_id="phalanx_aura"),
)

ARMORS: Tuple[Armor, ...] = (
    Armor(id="cloth", name="布衣", armor=1, weight=0, ranged_accuracy=0,
          mp=0, power_cost=1),
    Armor(id="leather", name="皮甲", armor=2, weight=1, ranged_accuracy=0,
          mp=0, power_cost=2),
    Armor(id="lamellar", name="札甲", armor=5, weight=3, ranged_accuracy=-3,
          mp=0, power_cost=5),
    Armor(id="scale", name="魚鱗甲", armor=6, weight=4, ranged_accuracy=-5,
          mp=0, power_cost=6, min_tier_id="veteran"),
)

HORSES: Tuple[Horse, ...] = (
    Horse(id="warhorse", name="戰馬", mp_bonus=2, charge_mult=1.35,
          power_cost=4, min_tier_id="veteran"),
    Horse(id="fine_horse", name="良駒", mp_bonus=3, charge_mult=1.60,
          power_cost=6, min_tier_id="elite"),
)

QUALITIES: Tuple[Quality, ...] = (
    Quality(id="refined", name="精製", multiplier=1.00, description="正規軍"),
)

SKILLS: Tuple[Skill, ...] = (
    Skill(id="guard", name="援護架盾", kind=SKILL_ACTIVE, ap_cost=40,
          description="援護相鄰友軍，替其承受遠程傷害。"),
    Skill(id="break_charge", name="破陣衝撞", kind=SKILL_ACTIVE, ap_cost=60,
          description="擊退相鄰敵人；被阻擋時追加 300 傷害並暈眩。"),
    Skill(id="pike_wall", name="拒馬槍陣", kind=SKILL_ACTIVE, ap_cost=25,
          description="架設；敵騎進入相鄰格被中斷並受雙倍傷害。"),
    Skill(id="rapid_fire", name="神速連射", kind=SKILL_ACTIVE, ap_cost=40,
          description="下一擊 1.5 倍傷害、+20% 命中。"),
    Skill(id="calibration", name="精密校準", kind=SKILL_ACTIVE, ap_cost=40,
          description="下一擊射程 +1、命中 +20%，本回合攻擊不受反擊。"),
    Skill(id="long_shot", name="遠射", kind=SKILL_ACTIVE, ap_cost=25,
          description="本回合射程 +1（6 → 7）；不給命中、不給傷害。",
          range_bonus=1),
    Skill(id="reload", name="裝填", kind=SKILL_ACTIVE, ap_cost=RELOAD_AP,
          description="弩回到已裝填；裝填當回合不能再射。"),
    Skill(id="cavalry_shield", name="騎兵盾", kind=SKILL_PASSIVE,
          description="不影響命中；騎兵默認盾。"),
    Skill(id="standard_shield", name="標準盾", kind=SKILL_PASSIVE,
          description="單兵推進用；精銳以下騎乘額外 −3 命中。"),
    Skill(id="phalanx_aura", name="方陣", kind=SKILL_AURA,
          description="正後方一格友軍獲得 40% 遠程格擋；多面大盾取最高、不疊加。"),
    Skill(id="fire_arrow", name="換矢", kind=SKILL_TOGGLE, ap_cost=10,
          description="切換穿甲箭（無視 40% 防）與火矢（+20% 傷害）。",
          pierce_mult=FIRE_ARROW_PIERCE_MULT, panic_turns=2),
)


# ---------------------------------------------------------------------------
# Indexes and lookups
# ---------------------------------------------------------------------------

def _build_indexes(table: Sequence[object]) -> Tuple[Mapping[str, object],
                                                    Mapping[str, object]]:
    by_id: Dict[str, object] = {}
    by_name: Dict[str, object] = {}
    for item in table:
        item_id = item.id  # type: ignore[attr-defined]
        item_name = item.name  # type: ignore[attr-defined]
        if item_id in by_id:
            raise ValueError(f"duplicate id {item_id!r} in {table!r}")
        if item_name in by_name:
            raise ValueError(f"duplicate name {item_name!r} in {table!r}")
        by_id[item_id] = item
        by_name[item_name] = item
    return MappingProxyType(by_id), MappingProxyType(by_name)


TIERS_BY_ID, TIERS_BY_NAME = _build_indexes(TIERS)
WEAPONS_BY_ID, WEAPONS_BY_NAME = _build_indexes(WEAPONS)
SHIELDS_BY_ID, SHIELDS_BY_NAME = _build_indexes(SHIELDS)
ARMORS_BY_ID, ARMORS_BY_NAME = _build_indexes(ARMORS)
HORSES_BY_ID, HORSES_BY_NAME = _build_indexes(HORSES)
QUALITIES_BY_ID, QUALITIES_BY_NAME = _build_indexes(QUALITIES)
SKILLS_BY_ID, SKILLS_BY_NAME = _build_indexes(SKILLS)

_TIER_RANK: Mapping[str, int] = MappingProxyType(
    {tier.id: rank for rank, tier in enumerate(TIERS)}
)


def _resolve(by_id: Mapping[str, object], by_name: Mapping[str, object],
             key: object, label: str, expected_type: type) -> object:
    if isinstance(key, expected_type):
        return key
    if isinstance(key, str):
        text = key.strip()
        item = by_id.get(text.lower())
        if item is None:
            item = by_name.get(text)
        if item is not None:
            return item
        raise KeyError(f"unknown {label}: {key!r}")
    raise TypeError(
        f"{label} must be a {expected_type.__name__}, id or Chinese name; "
        f"got {type(key).__name__}"
    )


def resolve_tier(key: object) -> Tier:
    """Resolve a :class:`Tier` from an object, ASCII id or Chinese name."""
    return _resolve(TIERS_BY_ID, TIERS_BY_NAME, key, "tier", Tier)  # type: ignore[return-value]


def resolve_weapon(key: object) -> Weapon:
    """Resolve a :class:`Weapon` from an object, ASCII id or Chinese name."""
    return _resolve(WEAPONS_BY_ID, WEAPONS_BY_NAME, key, "weapon", Weapon)  # type: ignore[return-value]


def resolve_shield(key: object) -> Shield:
    """Resolve a :class:`Shield` from an object, ASCII id or Chinese name."""
    return _resolve(SHIELDS_BY_ID, SHIELDS_BY_NAME, key, "shield", Shield)  # type: ignore[return-value]


def resolve_armor(key: object) -> Armor:
    """Resolve an :class:`Armor` from an object, ASCII id or Chinese name."""
    return _resolve(ARMORS_BY_ID, ARMORS_BY_NAME, key, "armor", Armor)  # type: ignore[return-value]


def resolve_horse(key: object) -> Horse:
    """Resolve a :class:`Horse` from an object, ASCII id or Chinese name."""
    return _resolve(HORSES_BY_ID, HORSES_BY_NAME, key, "horse", Horse)  # type: ignore[return-value]


def resolve_quality(key: object) -> Quality:
    """Resolve a :class:`Quality` from an object, ASCII id or Chinese name."""
    return _resolve(QUALITIES_BY_ID, QUALITIES_BY_NAME, key, "quality", Quality)  # type: ignore[return-value]


def resolve_skill(key: object) -> Skill:
    """Resolve a :class:`Skill` from an object, ASCII id or Chinese name."""
    return _resolve(SKILLS_BY_ID, SKILLS_BY_NAME, key, "skill", Skill)  # type: ignore[return-value]


# Friendly aliases used by the game layer.
get_tier = resolve_tier
get_weapon = resolve_weapon
get_shield = resolve_shield
get_armor = resolve_armor
get_horse = resolve_horse
get_quality = resolve_quality
get_skill = resolve_skill


def quality_multiplier(quality: object = 1.0) -> float:
    """Return the attack-channel multiplier for a quality.

    Accepts a :class:`Quality`, an id / Chinese name, a raw float, or ``None``
    (treated as 精製 ×1.00).
    """
    if quality is None:
        return 1.0
    if isinstance(quality, Quality):
        return quality.multiplier
    if isinstance(quality, str):
        try:
            return float(quality)
        except ValueError:
            return resolve_quality(quality).multiplier
    if isinstance(quality, (int, float)):
        return float(quality)
    raise TypeError(f"quality must be Quality/id/name/number; got {type(quality).__name__}")


# ---------------------------------------------------------------------------
# Pure formulas
# ---------------------------------------------------------------------------

def _armor_number(armor_value: object) -> float:
    """Accept an :class:`Armor`, an armor id/name or a raw number."""
    if isinstance(armor_value, Armor):
        return float(armor_value.armor)
    if isinstance(armor_value, str):
        try:
            return float(armor_value)
        except ValueError:
            return float(resolve_armor(armor_value).armor)
    if isinstance(armor_value, (int, float)):
        return float(armor_value)
    raise TypeError(f"armor_value must be Armor/id/name/number; got {type(armor_value).__name__}")


def per_hit_damage(weapon: object, armor_value: object, quality: object = 1.0,
                   fire_arrow: bool = False,
                   target_rattan: bool = False) -> float:
    """Damage of one soldier's hit.

    .. math::

        \\sum_c \\max(atk_c \\times 0.10,\\; atk_c - armor \\times k_c)

    with ``k_cut=1.00``, ``k_pierce=0.70`` (弩 0.40) and ``k_blunt=0.30``.

    ``quality`` multiplies the three white channels only.
    ``fire_arrow`` multiplies the pierce channel by 0.70.
    Against 藤甲 with fire arrows, pierce is multiplied by 2 and ignores armor.
    """
    weapon_obj = resolve_weapon(weapon)
    multiplier = quality_multiplier(quality)
    armor = max(0.0, _armor_number(armor_value))

    cut = weapon_obj.cut * multiplier
    pierce = weapon_obj.pierce * multiplier
    blunt = weapon_obj.blunt * multiplier
    pierce_factor = weapon_obj.pierce_factor

    if fire_arrow:
        pierce *= FIRE_ARROW_PIERCE_MULT
        if target_rattan:
            pierce *= FIRE_RATTAN_MULT
            pierce_factor = 0.0

    cut_damage = max(cut * FLOOR_RATIO, cut - armor * FACTOR_CUT)
    pierce_damage = max(pierce * FLOOR_RATIO, pierce - armor * pierce_factor)
    blunt_damage = max(blunt * FLOOR_RATIO, blunt - armor * FACTOR_BLUNT)

    # Round away binary float noise (e.g. 6.3999999999999995) while keeping
    # the formula's one-decimal precision intact.
    return round(cut_damage + pierce_damage + blunt_damage, 6)


def _normalise_hand(hand: object) -> str:
    if isinstance(hand, Weapon):
        return hand.hand
    if not isinstance(hand, str):
        raise TypeError(f"hand must be str or Weapon; got {type(hand).__name__}")
    key = hand.strip().lower()
    if key in (HAND_ONE, "one", "one-hand", "single", "1", "單", "單手", "单手"):
        return HAND_ONE
    if key in (HAND_TWO, "two", "two-hand", "double", "2", "雙", "雙手", "双手"):
        return HAND_TWO
    raise ValueError(f"unknown hand: {hand!r}")


def _tier_rank(tier: Optional[Tier]) -> int:
    if tier is None:
        return 0
    return _TIER_RANK[tier.id]


def hit_chance(base_accuracy: Optional[int], weapon: object, distance: float,
               shield: object = None, mounted: bool = False,
               tier: object = None) -> int:
    """Final hit chance as a percentage, clamped to 15..95.

    ``base_accuracy`` is the tier/unit accuracy (pass ``None`` to take it from
    ``tier``).  ``tier`` is also needed for the 中盾 mounted penalty: below
    精銳 a mounted user suffers the shield's extra −3.

    Distance uses v3 free range::

        hit -= 15 * max(0, distance - weapon.free_range)

    The shield only contributes when the current weapon is one-handed.
    """
    weapon_obj = resolve_weapon(weapon)
    tier_obj = resolve_tier(tier) if tier is not None else None
    shield_obj = resolve_shield(shield) if shield is not None else None

    if base_accuracy is None:
        base_accuracy = tier_obj.accuracy if tier_obj is not None else 0

    shield_active = (
        shield_obj is not None
        and weapon_obj.is_one_handed
        and (not mounted or shield_obj.mountable)
    )

    hit = base_accuracy + weapon_obj.accuracy
    if shield_active:
        hit += shield_obj.accuracy
        if mounted and _tier_rank(tier_obj) < _TIER_RANK["elite"]:
            hit += shield_obj.mounted_accuracy

    over_range = max(0.0, float(distance) - weapon_obj.free_range)
    hit -= FREE_RANGE_ACC_PENALTY * over_range

    return int(max(15, min(95, round(hit))))


def damage_multiplier(weapon: object, distance: float) -> float:
    """Ranged damage multiplier from v3 free range (clamped by −80%)."""
    weapon_obj = resolve_weapon(weapon)
    over_range = max(0.0, float(distance) - weapon_obj.free_range)
    penalty = min(DMG_PENALTY_CAP, FREE_RANGE_DMG_PENALTY * over_range)
    return round(1.0 - penalty, 6)


def shield_melee_armor(shield: object, hand: object, angle: str) -> int:
    """Shield armor bonus in melee.

    Shields only work in one-hand mode and never protect the rear.  ``angle``
    accepts ``FRONT`` / ``FLANK`` / ``REAR`` (case-insensitive).
    """
    if shield is None:
        return 0
    shield_obj = resolve_shield(shield)
    if _normalise_hand(hand) != HAND_ONE:
        return 0

    key = "FRONT" if angle is None else str(angle).strip().upper()
    if key in ("REAR", "BACK", "後", "後方"):
        return 0
    if key in ("FRONT", "FLANK", "SIDE", "前", "側", "側面"):
        return shield_obj.melee_armor
    raise ValueError(f"unknown angle: {angle!r}")


def shield_ranged_block(shield: object) -> float:
    """Ranged block fraction for a shield, capped by :data:`SHIELD_BLOCK_CAP`."""
    if shield is None:
        return 0.0
    shield_obj = resolve_shield(shield)
    return round(min(SHIELD_BLOCK_CAP, float(shield_obj.ranged_block)), 6)


def _normalise_facing(facing: object) -> Tuple[int, int]:
    if isinstance(facing, (tuple, list)) and len(facing) == 2:
        return int(facing[0]), int(facing[1])
    if isinstance(facing, str):
        key = facing.strip().lower()
        if key in _FACING_ALIASES:
            return _FACING_DELTAS[_FACING_ALIASES[key]]
        raise ValueError(f"unknown facing: {facing!r}")
    if isinstance(facing, int) and facing in _FACING_DELTAS:
        return _FACING_DELTAS[facing]
    raise ValueError(f"unknown facing: {facing!r}")


def _xy(xy: object) -> Tuple[int, int]:
    if hasattr(xy, "x") and hasattr(xy, "y"):
        return int(xy.x), int(xy.y)  # type: ignore[attr-defined]
    if isinstance(xy, (tuple, list)) and len(xy) == 2:
        return int(xy[0]), int(xy[1])
    raise TypeError(f"expected (x, y), got {xy!r}")


def aura_targets(bearer_xy: Tuple[int, int], facing: int) -> Tuple[Tuple[int, int], ...]:
    """Tiles receiving the 大盾 方陣 aura.

    The aura covers exactly the one tile directly behind the bearer (the
    opposite of ``facing``).  ``facing`` uses ``combat.DIR_*`` values
    (0=up, 1=right, 2=down, 3=left) and keeps the same values here without
    importing ``combat``.  Bounds are the caller's responsibility.
    """
    x, y = _xy(bearer_xy)
    dx, dy = _normalise_facing(facing)
    return ((x - dx, y - dy),)


# ---------------------------------------------------------------------------
# Build statistics
# ---------------------------------------------------------------------------

def build_stats(tier: object, weapon: object, shield: object, armor: object,
                mount: object = None, quality: object = 1.0) -> dict:
    """Derive all stats for one active loadout.

    The function handles one active weapon (the game's main/sub slots are a
    UI-level concern).  ``shield`` may be ``None`` and, per v2, only applies
    while a one-handed weapon is active.  The shield still counts toward weight
    when it is stowed.

    Returned keys intentionally include stable ids *and* ready-to-display
    numbers; see the tests for the canonical examples from v2 section 8.
    """
    tier_obj = resolve_tier(tier)
    weapon_obj = resolve_weapon(weapon)
    shield_obj = resolve_shield(shield) if shield is not None else None
    armor_obj = resolve_armor(armor)
    mount_obj = resolve_horse(mount) if mount is not None else None
    multiplier = quality_multiplier(quality)

    tier_rank = _tier_rank(tier_obj)
    issues = []

    shield_active = shield_obj is not None and weapon_obj.is_one_handed
    if shield_active and mount_obj is not None and not shield_obj.mountable:
        shield_active = False
        issues.append(f"shield_not_mountable:{shield_obj.id}")

    if mount_obj is not None and not weapon_obj.mounted:
        issues.append(f"weapon_not_mountable:{weapon_obj.id}")
    if (mount_obj is not None and mount_obj.min_tier_id is not None
            and tier_rank < _TIER_RANK[mount_obj.min_tier_id]):
        issues.append(f"mount_requires_tier:{mount_obj.min_tier_id}")
    if (armor_obj.min_tier_id is not None
            and tier_rank < _TIER_RANK[armor_obj.min_tier_id]):
        issues.append(f"armor_requires_tier:{armor_obj.min_tier_id}")

    cut = weapon_obj.cut * multiplier
    pierce = weapon_obj.pierce * multiplier
    blunt = weapon_obj.blunt * multiplier

    shield_armor_bonus = shield_obj.melee_armor if shield_active else 0
    armor_value = armor_obj.armor + shield_armor_bonus

    shield_accuracy = shield_obj.accuracy if shield_active else 0
    mounted_shield_penalty = 0
    if shield_active and mount_obj is not None:
        if tier_rank < _TIER_RANK["elite"]:
            mounted_shield_penalty = shield_obj.mounted_accuracy

    accuracy = (tier_obj.accuracy + weapon_obj.accuracy
                + shield_accuracy + mounted_shield_penalty)

    weight = (weapon_obj.weight + armor_obj.weight
              + (shield_obj.weight if shield_obj is not None else 0))
    if weight >= 12:
        weight_penalty = 2
    elif weight >= 7:
        weight_penalty = 1
    else:
        weight_penalty = 0

    mp = (BASE_MP + (mount_obj.mp_bonus if mount_obj is not None else 0)
          + armor_obj.mp - weight_penalty)

    # Every weapon owns its active skill.  The tier only gates whether the
    # unit can use an active skill at all.
    active_skill_id: Optional[str] = weapon_obj.skill_id

    active_skill = SKILLS_BY_ID[active_skill_id] if active_skill_id else None
    extra_skill = (weapon_obj.extra_skill if weapon_obj.extra_skill_id else None)
    passive_skill = weapon_obj.skill
    shield_skill = shield_obj.skill if shield_active else None
    aura_block = shield_obj.aura_block if shield_active else 0.0
    aura_skill = shield_skill if aura_block > 0 else None
    ranged_block = shield_ranged_block(shield_obj) if shield_active else 0.0

    power_cost = (tier_obj.power_cost + weapon_obj.power_cost
                  + armor_obj.power_cost
                  + (shield_obj.power_cost if shield_obj is not None else 0)
                  + (mount_obj.power_cost if mount_obj is not None else 0))

    active_skill_allowed = (
        active_skill_id is not None and tier_obj.max_active_skills >= 1
    )

    return {
        # identity
        "tier": tier_obj.id,
        "tier_id": tier_obj.id,
        "tier_name": tier_obj.name,
        "weapon": weapon_obj.id,
        "weapon_id": weapon_obj.id,
        "weapon_name": weapon_obj.name,
        "shield": shield_obj.id if shield_obj is not None else None,
        "shield_id": shield_obj.id if shield_obj is not None else None,
        "shield_name": shield_obj.name if shield_obj is not None else None,
        "armor_id": armor_obj.id,
        "armor_name": armor_obj.name,
        "mount": mount_obj.id if mount_obj is not None else None,
        "mount_id": mount_obj.id if mount_obj is not None else None,
        "mount_name": mount_obj.name if mount_obj is not None else None,
        # loadout geometry
        "hand": weapon_obj.hand,
        "two_handed": weapon_obj.is_two_handed,
        "ranged": weapon_obj.ranged,
        "shield_active": shield_active,
        "shield_armor_bonus": shield_armor_bonus,
        "shield_accuracy": shield_accuracy,
        "mounted_shield_penalty": mounted_shield_penalty,
        "mounted": mount_obj is not None,
        "mount_compatible": (
            mount_obj is None
            or (weapon_obj.mounted
                and (shield_obj is None or shield_obj.mountable))
        ),
        # defense
        "armor": armor_value,
        "armor_value": armor_value,
        "body_armor": armor_obj.armor,
        "ranged_armor": armor_obj.armor,
        "ranged_block": ranged_block,
        "shield_block": ranged_block,
        "aura_block": aura_block,
        "incoming_ranged_accuracy": armor_obj.ranged_accuracy,
        "fire_vulnerable": armor_obj.fire_vulnerable,
        # offense
        "accuracy": accuracy,
        "hit": accuracy,
        "tier_accuracy": tier_obj.accuracy,
        "weapon_accuracy": weapon_obj.accuracy,
        "tier_attack_mult": tier_obj.attack_mult,
        "melee_accuracy": accuracy,
        "ranged_accuracy": tier_obj.accuracy + weapon_obj.accuracy,
        "attack_cut": cut,
        "attack_pierce": pierce,
        "attack_blunt": blunt,
        "attack": cut + pierce + blunt,
        "attack_total": cut + pierce + blunt,
        "total_attack": cut + pierce + blunt,
        "pierce_factor": weapon_obj.pierce_factor,
        "range": weapon_obj.range,
        "attack_range": weapon_obj.range,
        "free_range": weapon_obj.free_range,
        "fire_arrow_capable": weapon_obj.fire_arrow,
        "reload_required": weapon_obj.reload_required,
        "ammo": weapon_obj.ammo,
        # economy
        "weight": weight,
        "weight_penalty": weight_penalty,
        "mp": mp,
        "base_mp": BASE_MP,
        "power_cost": power_cost,
        "quality": multiplier,
        # skills
        "skill": active_skill_id,
        "skill_id": active_skill_id,
        "skill_name": active_skill.name if active_skill is not None else None,
        "skill_obj": active_skill,
        "active_skill_allowed": active_skill_allowed,
        "extra_skill": extra_skill.id if extra_skill is not None else None,
        "extra_skill_id": extra_skill.id if extra_skill is not None else None,
        "extra_skill_name": extra_skill.name if extra_skill is not None else None,
        "extra_skill_obj": extra_skill,
        "passive_skill": passive_skill.id,
        "passive_skill_id": passive_skill.id,
        "passive_skill_obj": passive_skill,
        "shield_skill": shield_skill.id if shield_skill is not None else None,
        "shield_skill_obj": shield_skill,
        "aura_skill": aura_skill.id if aura_skill is not None else None,
        "aura_skill_id": aura_skill.id if aura_skill is not None else None,
        "aura_skill_obj": aura_skill,
        # validation
        "requirements_met": not issues,
        "issues": tuple(issues),
    }


# ---------------------------------------------------------------------------
# Import-time validation
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_equipment() -> bool:
    """Validate table integrity; raises ``ValueError`` on bad data.

    Checks: ASCII ids, globally unique ids, non-empty names, per-table unique
    names, every skill reference exists, sane ranged/free-range data.
    """
    tables: Dict[str, Sequence[object]] = {
        "TIERS": TIERS,
        "WEAPONS": WEAPONS,
        "SHIELDS": SHIELDS,
        "ARMORS": ARMORS,
        "HORSES": HORSES,
        "QUALITIES": QUALITIES,
        "SKILLS": SKILLS,
    }

    seen_ids = set()
    for label, table in tables.items():
        seen_names = set()
        for item in table:
            item_id = item.id  # type: ignore[attr-defined]
            item_name = item.name  # type: ignore[attr-defined]
            if not _ID_RE.match(item_id):
                raise ValueError(f"{label}: id {item_id!r} is not ASCII snake_case")
            if item_id in seen_ids:
                raise ValueError(f"{label}: duplicate id {item_id!r}")
            if not item_name or item_name in seen_names:
                raise ValueError(f"{label}: empty or duplicate name {item_name!r}")
            seen_ids.add(item_id)
            seen_names.add(item_name)

    for weapon in WEAPONS:
        if weapon.skill_id not in SKILLS_BY_ID:
            raise ValueError(f"weapon {weapon.id!r} references missing skill {weapon.skill_id!r}")
        if weapon.toggle_skill_id is not None and weapon.toggle_skill_id not in SKILLS_BY_ID:
            raise ValueError(
                f"weapon {weapon.id!r} references missing toggle skill "
                f"{weapon.toggle_skill_id!r}"
            )
        if (weapon.extra_skill_id is not None
                and weapon.extra_skill_id not in SKILLS_BY_ID):
            raise ValueError(
                f"weapon {weapon.id!r} references missing extra skill "
                f"{weapon.extra_skill_id!r}"
            )
        if weapon.free_range < 0 or weapon.free_range > weapon.range:
            raise ValueError(f"weapon {weapon.id!r} has invalid free_range")
        if weapon.fire_arrow and not weapon.ranged:
            raise ValueError(f"weapon {weapon.id!r} has fire_arrow but is melee")
        if weapon.pierce_factor <= 0:
            raise ValueError(f"weapon {weapon.id!r} has non-positive pierce_factor")

    for shield in SHIELDS:
        if not 0.0 <= shield.ranged_block <= 1.0:
            raise ValueError(f"shield {shield.id!r} has invalid ranged_block")
        if not 0.0 <= shield.aura_block <= 1.0:
            raise ValueError(f"shield {shield.id!r} has invalid aura_block")
        if shield.skill_id is not None and shield.skill_id not in SKILLS_BY_ID:
            raise ValueError(f"shield {shield.id!r} references missing skill {shield.skill_id!r}")
        if shield.mounted_accuracy > 0:
            raise ValueError(f"shield {shield.id!r} has positive mounted penalty")

    for armor in ARMORS:
        if armor.min_tier_id is not None and armor.min_tier_id not in TIERS_BY_ID:
            raise ValueError(f"armor {armor.id!r} references missing tier {armor.min_tier_id!r}")
        if armor.mp > 0:
            raise ValueError(f"armor {armor.id!r} has a positive MP value")

    for horse in HORSES:
        if horse.min_tier_id is not None and horse.min_tier_id not in TIERS_BY_ID:
            raise ValueError(f"horse {horse.id!r} references missing tier {horse.min_tier_id!r}")

    return True


validate_equipment()
