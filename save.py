import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "save_data")
SAVE_VERSION = 1

_current_slot = 1


def set_slot(slot_id):
    global _current_slot
    if slot_id in (1, 2, 3):
        _current_slot = slot_id


def get_slot():
    return _current_slot


def _slot_dir(slot_id=None):
    slot_id = slot_id or _current_slot
    return os.path.join(SAVE_DIR, f"slot_{slot_id}")


def _slot_file(filename, slot_id=None):
    return os.path.join(_slot_dir(slot_id), filename)


def _ensure_dir(slot_id=None):
    d = _slot_dir(slot_id)
    os.makedirs(d, exist_ok=True)


def slot_exists(slot_id):
    return os.path.exists(_slot_file("meta.json", slot_id))


def delete_slot(slot_id):
    d = _slot_dir(slot_id)
    if not os.path.exists(d):
        return False
    shutil.rmtree(d)
    return True


def load_slot_summary(slot_id):
    if not slot_exists(slot_id):
        return None
    meta = _load_payload(_slot_file("meta.json", slot_id))
    if meta is None:
        return None
    temple = _load_payload(_slot_file("war_temple.json", slot_id)) or {}
    campaign = _load_payload(_slot_file("campaign.json", slot_id)) or {}

    generals_count = sum(
        len(temple.get(k, []))
        for k in ("main_hall", "mourning", "hall_of_fame", "martyr_shrine")
    )
    stats = meta.get("stats", {})
    return {
        "slot_id": slot_id,
        "soul_points": meta.get("soul_points", 0),
        "act": campaign.get("act", 1),
        "gold": campaign.get("gold", 0),
        "generals_count": generals_count,
        "unlocked_count": len(campaign.get("unlocked_units", [])),
        "total_battles": stats.get("total_battles", 0),
        "ascension": meta.get("ascension_level", 0),
    }


def _save_payload(path, payload):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"version": SAVE_VERSION, "payload": payload},
                      f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[Save Error] {path}: {e}")
        return False


def _load_payload(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[Load Error] {path}: {e}")
        return None
    if data.get("version") != SAVE_VERSION:
        return None
    return data.get("payload")


def save_meta(payload):
    _ensure_dir()
    return _save_payload(_slot_file("meta.json"), payload)


def load_meta():
    return _load_payload(_slot_file("meta.json"))


def save_temple(payload):
    _ensure_dir()
    return _save_payload(_slot_file("war_temple.json"), payload)


def load_temple():
    return _load_payload(_slot_file("war_temple.json"))


def save_campaign(payload):
    _ensure_dir()
    return _save_payload(_slot_file("campaign.json"), payload)


def load_campaign():
    return _load_payload(_slot_file("campaign.json"))