import json
import os
import sqlite3
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ.get("BOT_TOKEN", "9288572880:AAHaa4ea7lKvmSA8A4OMr0OJSMfv6SrZt54")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1021089367"))
ADMIN_USERNAME = "@usman_khasan"
API_URL = f"https://api.telegram.org/bot{TOKEN}/"
PORT = int(os.environ.get("PORT", 8080))

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(WORK_DIR, "up_ecosystem.db")
JSON_MIRROR_PATH = os.path.join(WORK_DIR, "users_status.json")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
db_lock = threading.Lock()

with db_lock:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        is_premium INTEGER DEFAULT 0,
        upstars INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        user_id INTEGER,
        module_name TEXT,
        PRIMARY KEY (user_id, module_name)
    )
    """)
    # Admin (1021089367) har doim VIP va 1000 UpStar balansda bo'lishini kafolatlash
    cursor.execute("INSERT OR IGNORE INTO users (user_id, is_premium, upstars) VALUES (?, 1, 1000)", (ADMIN_ID,))
    cursor.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (ADMIN_ID,))
    for m in ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]:
        cursor.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (ADMIN_ID, m))
    conn.commit()

def sync_json_and_github():
    """Android ilova 24/7 o'qiy olishi uchun bazani users_status.json ga eksport qiladi va GitHub'ga saqlaydi."""
    try:
        with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT user_id, is_premium, upstars FROM users")
            rows = cur.fetchall()
            data = {}
            for uid, prem, stars in rows:
                cur.execute("SELECT module_name FROM modules WHERE user_id = ?", (uid,))
                mods = [r[0] for r in cur.fetchall()]
                data[str(uid)] = {
                    "is_premium": bool(prem) or (len(mods) >= 4) or (uid == ADMIN_ID),
                    "upstars": stars,
                    "modules": mods
                }
        with open(JSON_MIRROR_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # GitHub Actions ichida bo'lsa avtomatik commit & push qilish
        if os.environ.get("GITHUB_ACTIONS") == "true":
            threading.Thread(target=_bg_git_push, daemon=True).start()
    except Exception:
        pass

def _bg_git_push():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "UpPremium AutoSync"], cwd=WORK_DIR)
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], cwd=WORK_DIR)
        subprocess.run(["git", "add", "up_ecosystem.db", "users_status.json"], cwd=WORK_DIR)
        subprocess.run(["git", "commit", "-m", "Auto-sync VIP status"], cwd=WORK_DIR)
        subprocess.run(["git", "push", "origin", "main"], cwd=WORK_DIR)
    except Exception:
        pass

def ensure_user(user_id, auto_vip=False):
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        is_vip = 1 if (user_id == ADMIN_ID or auto_vip) else 0
        if not row:
            cur.execute("INSERT INTO users (user_id, is_premium, upstars) VALUES (?, ?, 0)", (user_id, is_vip))
            conn.commit()
        elif is_vip == 1 and row[0] == 0:
            cur.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

def get_user_data(user_id):
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT module_name FROM modules WHERE user_id = ?", (user_id,))
        mods = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT is_premium, upstars FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        prem = bool(row[0]) if row else False
        stars = row[1] if row else 0

        # Agar Admin bo'lsa yoki 4/4 modul faol bo'lsa -> avtomatik UpPremium Faol!
        if (user_id == ADMIN_ID or len(mods) >= 4) and not prem:
            prem = True
            cur.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

        return (prem, stars, mods)

def tg_request(method, payload=None):
    url = API_URL + method
    try:
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    tg_request("sendMessage", payload)

def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    tg_request("editMessageText", payload)

def build_main_menu_kb(target_uid):
    return {
        "inline_keyboard": [
            [{"text": "🇺🇿 Uzcard / Humo (O'zbekiston)", "callback_data": f"pay_uz_{target_uid}"}],
            [{"text": "🌍 Visa (SUM / USD) (Xalqaro)", "callback_data": f"pay_visa_{target_uid}"}],
            [{"text": "🚀 4 ta Maxsus Modulni Yoqish", "callback_data": "modules_menu"}],
            [{"text": "🔄 Ilova bilan Sinxronlash (VIP Tekshirish)", "callback_data": f"sync_now_{target_uid}"}]
        ]
    }

def format_status_text(target_uid):
    prem, stars, mods = get_user_data(target_uid)
    status_text = "Faol ✅ (VIP)" if prem else "Faol emas ❌"
    return (
        f"🚀 *MessengerUP Rasmiy Boti*\n\n"
        f"🆔 Sizning ID: `{target_uid}`\n"
        f"💎 UpPremium: *{status_text}*\n"
        f"✨ UpStar Balansi: *{stars}*\n"
        f"🧩 Faol Modullar: *{len(mods)}/4 ta*\n\n"
        f"Kerakli bo'limni tanlang:"
    )

def handle_update(update):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = msg.get("from", {})
        user_id = user.get("id", chat_id)
        text = msg.get("text", "")

        # Telegramning o'zida Premium bo'lsa yoki Admin bo'lsa avto-aniqlash
        tg_is_prem = bool(user.get("is_premium", False))
        ensure_user(user_id, auto_vip=tg_is_prem)

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""
            target_uid = user_id
            app_vip = tg_is_prem

            # Ilovadan ?start=pay_premium_1021089367_vip1 bo'lib kelganda avtomatik VIP yoqish
            if "vip1" in args:
                app_vip = True
            if args.startswith("pay_"):
                for token_part in args.split("_"):
                    if token_part.isdigit() and len(token_part) >= 5:
                        target_uid = int(token_part)

            ensure_user(target_uid, auto_vip=app_vip)
            sync_json_and_github()
            send_message(chat_id, format_status_text(target_uid), build_main_menu_kb(target_uid))

        elif text.startswith("/give_prem") and user_id == ADMIN_ID:
            try:
                target_id = int(text.split()[1])
                ensure_user(target_id, auto_vip=True)
                with db_lock:
                    for m in ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]:
                        conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (target_id, m))
                    conn.commit()
                sync_json_and_github()
                send_message(chat_id, f"✅ `{target_id}` ga UpPremium va 4/4 modullar yoqildi!")
                send_message(target_id, "🎉 Tabriklaymiz! Sizga *UpPremium (VIP)* va barcha 4 ta modul faollashtirildi!")
            except Exception as e:
                send_message(chat_id, f"Xato: ({e})")

        elif text.startswith("/give_stars") and user_id == ADMIN_ID:
            try:
                parts = text.split()
                target_id, amount = int(parts[1]), int(parts[2])
                ensure_user(target_id)
                with db_lock:
                    conn.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, target_id))
                    conn.commit()
                sync_json_and_github()
                send_message(chat_id, f"✅ `{target_id}` ga {amount} UpStar qo'shildi!")
                send_message(target_id, f"✨ Hisobingizga *{amount} UpStar* qo'shildi!")
            except Exception as e:
                send_message(chat_id, f"Xato: ({e})")

        elif "photo" in msg or "document" in msg:
            username = f"@{user.get('username')}" if user.get("username") else "Mavjud emas"
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            caption = (
                f"💰 *Yangi to'lov cheki keldi!*\n"
                f"🆔 ID: `{user_id}`\n"
                f"👤 Ism: {full_name} ({username})\n\n"
                f"👇 *1-tugma bilan tasdiqlash:*"
            )
            admin_kb = {
                "inline_keyboard": [
                    [{"text": "💎 UpPremium (VIP) Yoqish", "callback_data": f"adm_prem_{user_id}"}],
                    [
                        {"text": "✨ +100 UpStar", "callback_data": f"adm_star_{user_id}_100"},
                        {"text": "✨ +500 UpStar", "callback_data": f"adm_star_{user_id}_500"}
                    ],
                    [{"text": "❌ Chekni Rad Etish", "callback_data": f"adm_reject_{user_id}"}]
                ]
            }
            if "photo" in msg:
                tg_request("sendPhoto", {"chat_id": ADMIN_ID, "photo": msg["photo"][-1]["file_id"], "caption": caption, "parse_mode": "Markdown", "reply_markup": admin_kb})
            elif "document" in msg:
                tg_request("sendDocument", {"chat_id": ADMIN_ID, "document": msg["document"]["file_id"], "caption": caption, "parse_mode": "Markdown", "reply_markup": admin_kb})
            send_message(chat_id, "✅ Chek adminga yuborildi! Tasdiqlanishi bilan sizga avtomatik VIP yonadi.")

    elif "callback_query" in update:
        call = update["callback_query"]
        call_id = call["id"]
        data = call.get("data", "")
        user_id = call["from"]["id"]
        chat_id = call["message"]["chat"]["id"]
        message_id = call["message"]["message_id"]

        tg_request("answerCallbackQuery", {"callback_query_id": call_id})

        if data.startswith("sync_now_"):
            sync_json_and_github()
            edit_message(chat_id, message_id, format_status_text(user_id), build_main_menu_kb(user_id))

        elif data.startswith("pay_uz"):
            msg_text = (
                f"💳 *O'zbekiston kartalari orqali to'lov:*\n\n"
                f"🔹 *Uzcard:* `5614682112210333`\n"
                f"🔹 *Humo:* `9860170111318102`\n"
                f"(Khasanov U.)\n\n"
                f"• UpPremium (1 oy): 35,000 so'm\n"
                f"• 100 UpStar: 15,000 so'm\n\n"
                f"To'lovdan so'ng chekni shu botga yuboring! 📌\n"
                f"🆔 Sizning ID: `{user_id}`"
            )
            kb = {"inline_keyboard": [[{"text": "⬅️ Orqaga", "callback_data": f"sync_now_{user_id}"}]]}
            edit_message(chat_id, message_id, msg_text, kb)

        elif data.startswith("pay_visa"):
            msg_text = (
                f"🌍 *Xalqaro Visa kartalari orqali to'lov:*\n\n"
                f"🔹 *Visa SUM:* `4023060506933828`\n"
                f"🔹 *Visa USD:* `4023060246442007`\n"
                f"(Khasanov U.)\n\n"
                f"• UpPremium (1 oy): $3.00\n"
                f"• 100 UpStar: $1.50\n\n"
                f"To'lovdan so'ng chekni shu botga yuboring! 📌\n"
                f"🆔 Sizning ID: `{user_id}`"
            )
            kb = {"inline_keyboard": [[{"text": "⬅️ Orqaga", "callback_data": f"sync_now_{user_id}"}]]}
            edit_message(chat_id, message_id, msg_text, kb)

        elif data == "modules_menu":
            prem, stars, mods = get_user_data(user_id)
            kb = {
                "inline_keyboard": [
                    [{"text": "🛡️ Ghost Vault (" + ("Faol ✅" if "GhostVault" in mods else "Yoqish") + ")", "callback_data": "activ_GhostVault"}],
                    [{"text": "🤖 AI Manager (" + ("Faol ✅" if "AIManager" in mods else "Yoqish") + ")", "callback_data": "activ_AIManager"}],
                    [{"text": "🌐 Mesh Network (" + ("Faol ✅" if "MeshNetwork" in mods else "Yoqish") + ")", "callback_data": "activ_MeshNetwork"}],
                    [{"text": "💰 Media-Paywall (" + ("Faol ✅" if "MediaPaywall" in mods else "Yoqish") + ")", "callback_data": "activ_MediaPaywall"}],
                    [{"text": "⚡ Hammasini Yoqish (VIP Faollashtirish)", "callback_data": "activ_ALL"}],
                    [{"text": "⬅️ Asosiy Menyu", "callback_data": f"sync_now_{user_id}"}]
                ]
            }
            edit_message(chat_id, message_id, "🧩 *Sizning 4 ta maxsus modulingiz:*", kb)

        elif data.startswith("activ_"):
            mod_name = data.split("_")[1]
            with db_lock:
                if mod_name == "ALL":
                    for m in ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]:
                        conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (user_id, m))
                    conn.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
                else:
                    conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (user_id, mod_name))
                conn.commit()
            sync_json_and_github()
            edit_message(chat_id, message_id, format_status_text(user_id), build_main_menu_kb(user_id))

        # ADMIN 1-CLICK TASDIQLASH TUGMALARI
        elif data.startswith("adm_prem_") and user_id == ADMIN_ID:
            target_id = int(data.split("_")[2])
            ensure_user(target_id, auto_vip=True)
            with db_lock:
                for m in ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]:
                    conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (target_id, m))
                conn.commit()
            sync_json_and_github()
            send_message(chat_id, f"✅ `{target_id}` foydalanuvchiga *UpPremium (VIP)* yoqildi!")
            send_message(target_id, "🎉 *To'lovingiz tasdiqlandi!*\n💎 Sizga *UpPremium (VIP)* va barcha 4/4 modullar faollashtirildi!")

        elif data.startswith("adm_star_") and user_id == ADMIN_ID:
            parts = data.split("_")
            target_id, amount = int(parts[2]), int(parts[3])
            ensure_user(target_id)
            with db_lock:
                conn.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, target_id))
                conn.commit()
            sync_json_and_github()
            send_message(chat_id, f"✅ `{target_id}` ga *{amount} UpStar* qo'shildi!")
            send_message(target_id, f"🎉 *To'lovingiz tasdiqlandi!*\n✨ Hisobingizga *{amount} UpStar* qo'shildi!")

        elif data.startswith("adm_reject_") and user_id == ADMIN_ID:
            target_id = int(data.split("_")[2])
            send_message(chat_id, f"❌ `{target_id}` cheki rad etildi.")
            send_message(target_id, "⚠️ Yuborgan to'lov chekingiz tasdiqlanmadi. Qaytadan tekshirib yuboring yoki adminga murojaat qiling.")

class APIServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        try:
            uid = int(params.get("user_id", ["0"])[0])
        except ValueError:
            uid = 0

        if parsed.path == "/":
            body = json.dumps({"status": "MessengerUP 24/7 Server Active"}).encode("utf-8")
        elif parsed.path == "/status":
            prem, stars, mods = get_user_data(uid)
            body = json.dumps({"is_premium": prem, "upstars": stars, "modules": mods}).encode("utf-8")
        elif parsed.path == "/transfer":
            try:
                from_id = int(params.get("from_id", ["0"])[0])
                to_id = int(params.get("to_id", ["0"])[0])
                amount = int(params.get("amount", ["0"])[0])
            except ValueError:
                from_id, to_id, amount = 0, 0, 0
            ensure_user(from_id)
            ensure_user(to_id)
            _, sender_stars, _ = get_user_data(from_id)
            if amount > 0 and sender_stars >= amount:
                with db_lock:
                    conn.execute("UPDATE users SET upstars = upstars - ? WHERE user_id = ?", (amount, from_id))
                    conn.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, to_id))
                    conn.commit()
                sync_json_and_github()
                send_message(to_id, f"🎁 Sizga `{from_id}` foydalanuvchidan *{amount} UP Stars* o'tkazildi!")
                body = json.dumps({"ok": True, "new_balance": sender_stars - amount}).encode("utf-8")
            else:
                body = json.dumps({"ok": False, "error": "Balans yetarli emas"}).encode("utf-8")
        elif parsed.path == "/modules":
            _, _, mods = get_user_data(uid)
            body = json.dumps({"modules": mods}).encode("utf-8")
        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    sync_json_and_github()
    tg_request("deleteWebhook")
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", PORT), APIServer).serve_forever(), daemon=True).start()
    print(f"✅ MessengerUP Server {PORT}-portda 24/7 rejimda ishga tushdi!")
    offset = 0
    while True:
        res = tg_request("getUpdates", {"offset": offset, "timeout": 25})
        if res.get("ok"):
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                handle_update(upd)
        else:
            time.sleep(2)
