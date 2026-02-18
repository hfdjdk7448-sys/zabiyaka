import json, os
from datetime import datetime

DB_FILE = "dragon_data.json"
OWNER_ID = 7805872198  # Твой ID
RANK_NAMES = {5: "Вожак", 4: "Совожак", 3: "Старейшина", 2: "Опытный викинг", 1: "Житель Олуха", 0: "Изгой"}

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {
        "users": {}, 
        "permissions": {
            "варн": 3, "бан": 5, "мут": 3, "кик": 4, 
            "повысить": 5, "понизить": 5, "кд": 5,
            "кто я": 0, "топ акт": 0, "мои варны": 0, "твои варны": 2
        },
        "owner_set": False
    }

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_u(db, uid, name="Викинг"):
    uid_str = str(uid)
    if uid_str not in db["users"]:
        db["users"][uid_str] = {
            "nick": name, "stars": 0, "messages": 0, "warns": [], 
            "desc": "Обычный житель", "joined": datetime.now().strftime("%d.%m.%Y"),
            "stats": {"day": 0}
        }
    if int(uid) == OWNER_ID:
        db["users"][uid_str]["stars"] = 5
    return db["users"][uid_str]
