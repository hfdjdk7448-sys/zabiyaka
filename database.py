import json, os
from datetime import datetime

DB_FILE = "dragon_data.json"
RANK_NAMES = {5: "Вожак", 4: "Совожак", 3: "Старейшина", 2: "Опытный викинг", 1: "Житель Олуха"}

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"users": {}, "permissions": {"варн": 3, "бан": 5, "мут": 4, "кик": 3, "повысить": 5}, "owner_set": False}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_u(db, uid, name="Викинг"):
    uid_str = str(uid)
    if uid_str not in db["users"]:
        db["users"][uid_str] = {"nick": name, "stars": 1, "messages": 0, "warns": [], "desc": "Обычный житель Олуха", "joined": datetime.now().strftime("%d.%m.%Y"), "stats": {"day": 0}}
    return db["users"][uid_str]
  
