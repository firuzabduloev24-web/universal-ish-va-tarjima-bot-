import json
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = "9288572880:AAHaa4ea7lKvmSA8A4OMr0OJSMfv6SrZt54"
ADMIN_ID = 1021089367
ADMIN_USERNAME = "@usman_khasan"
API_URL = f"https://api.telegram.org/bot{TOKEN}/"

# --- 1. MA'LUMOTLAR BAZASI ---
conn = sqlite3.connect("up_ecosystem.db", check_same_thread=False)
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
    conn.commit()

def ensure_user(user_id):
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (user_id, is_premium, upstars) VALUES (?, 0, 0)", (user_id,))
            conn.commit()

def get_user_data(user_id):
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT is_premium, upstars FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        prem = bool(row[0]) if row else False
        stars = row[1] if row else 0
        
        cur.execute("SELECT module_name FROM modules WHERE user_id = ?", (user_id,))
        mods = [r[0] for r in cur.fetchall()]
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

def edit_message(chat_id, message_id, text):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    tg_request("editMessageText", payload)

def handle_update(update):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = msg.get("from", {})
        user_id = user.get("id", chat_id)
        text = msg.get("text", "")

        ensure_user(user_id)

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""

            kb = {
                "inline_keyboard": [
                    [{"text": "🇺🇿 Uzcard / Humo (O'zbekiston)", "callback_data": f"pay_uz_{args}"}],
                    [{"text": "🌍 Visa (SUM / USD) (Xalqaro)", "callback_data": f"pay_visa_{args}"}],
                    [{"text": "🚀 4 ta Maxsus Modulni Yoqish", "callback_data": "modules_menu"}]
                ]
            }

            prem, stars, mods = get_user_data(user_id)
            status_text = "Faol ✅" if prem else "Faol emas ❌"
            reply = (
                f"🚀 *MessengerUP Rasmiy Boti*\n\n"
                f"🆔 Sizning ID: `{user_id}`\n"
                f"💎 UpPremium: *{status_text}*\n"
                f"✨ UpStar Balansi: *{stars}*\n"
                f"🧩 Faol Modullar: {len(mods)}/4 ta\n\n"
                f"Kerakli bo'limni tanlang:"
            )
            send_message(chat_id, reply, kb)

        elif text.startswith("/give_prem") and user_id == ADMIN_ID:
            try:
                target_id = int(text.split()[1])
                ensure_user(target_id)
                with db_lock:
                    conn.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (target_id,))
                    conn.commit()
                send_message(chat_id, f"✅ `{target_id}` ga UpPremium yoqildi!")
                send_message(target_id, "🎉 Tabriklaymiz! Sizga *UpPremium* faollashtirildi. Ilovani qaytadan oching!")
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
                send_message(chat_id, f"✅ `{target_id}` ga {amount} UpStar qo'shildi!")
                send_message(target_id, f"✨ Hisobingizga *{amount} UpStar* qo'shildi!")
            except Exception as e:
                send_message(chat_id, f"Xato: ({e})")

        elif "photo" in msg or "document" in msg:
            username = f"@{user.get('username')}" if user.get("username") else "Mavjud emas"
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            caption = f"💰 *Yangi to'lov cheki!*\n🆔 ID: `{user_id}`\n👤 {full_name} ({username})\n\nPremium berish: `/give_prem {user_id}`"
            if "photo" in msg:
                tg_request("sendPhoto", {"chat_id": ADMIN_ID, "photo": msg["photo"][-1]["file_id"], "caption": caption, "parse_mode": "Markdown"})
            send_message(chat_id, "✅ Chek adminga yuborildi! Tez orada tasdiqlanadi.")

    elif "callback_query" in update:
        call = update["callback_query"]
        call_id = call["id"]
        data = call.get("data", "")
        user_id = call["from"]["id"]
        chat_id = call["message"]["chat"]["id"]
        message_id = call["message"]["message_id"]

        tg_request("answerCallbackQuery", {"callback_query_id": call_id})

        if data.startswith("pay_uz"):
            msg_text = (
                f"💳 *O'zbekiston kartalari orqali to'lov:*\n\n"
                f"🔹 **Uzcard:** `5614682112210333`\n"
                f"🔹 **Humo:** `9860170111318102`\n"
                f"(Khasanov U.)\n\n"
                f"Narxlar:\n"
                f"• UpPremium (1 oy): 35,000 so'm\n"
                f"• 100 UpStar: 15,000 so'm\n\n"
                f"To'lovdan so'ng chekni shu botga yuboring! 📌"
            )
            edit_message(chat_id, message_id, msg_text)

        elif data.startswith("pay_visa"):
            msg_text = (
                f"🌍 *Xalqaro Visa kartalari orqali to'lov:*\n\n"
                f"🔹 **Visa SUM:** `4023060506933828`\n"
                f"🔹 **Visa USD:** `4023060246442007`\n"
                f"(Khasanov U.)\n\n"
                f"Narxlar:\n"
                f"• UpPremium (1 oy): $3.00\n"
                f"• 100 UpStar: $1.50\n\n"
                f"To'lovdan so'ng chekni yuboring! 📌"
            )
            edit_message(chat_id, message_id, msg_text)

        elif data == "modules_menu":
            prem, stars, mods = get_user_data(user_id)
            kb = {
                "inline_keyboard": [
                    [{"text": "🛡️ Ghost Vault (" + ("Faol ✅" if "GhostVault" in mods else "Faol emas ❌") + ")", "callback_data": "activ_GhostVault"}],
                    [{"text": "🤖 AI Manager (" + ("Faol ✅" if "AIManager" in mods else "Faol emas ❌") + ")", "callback_data": "activ_AIManager"}],
                    [{"text": "🌐 Mesh Network (" + ("Faol ✅" if "MeshNetwork" in mods else "Faol emas ❌") + ")", "callback_data": "activ_MeshNetwork"}],
                    [{"text": "💰 Media-Paywall (" + ("Faol ✅" if "MediaPaywall" in mods else "Faol emas ❌") + ")", "callback_data": "activ_MediaPaywall"}],
                    [{"text": "🔙 Orqaga", "callback_data": "back_start"}]
                ]
            }
            edit_message(chat_id, message_id, "🧩 *Sizning 4 ta maxsus modulingiz*\nUlarni ishga tushirish uchun tanlang:", kb)

        elif data.startswith("activ_"):
            mod_name = data.split("_")[1]
            with db_lock:
                try:
                    conn.execute("INSERT INTO modules (user_id, module_name) VALUES (?, ?)", (user_id, mod_name))
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass
            edit_message(chat_id, message_id, f"✅ *{mod_name}* moduli muvaffaqiyatli faollashtirildi!")

        elif data == "back_start":
            prem, stars, mods = get_user_data(user_id)
            status_text = "Faol ✅" if prem else "Faol emas ❌"
            kb = {
                "inline_keyboard": [
                    [{"text": "🇺🇿 Uzcard / Humo", "callback_data": "pay_uz"}],
                    [{"text": "🌍 Visa (SUM / USD)", "callback_data": "pay_visa"}],
                    [{"text": "🚀 4 ta Maxsus Modulni Yoqish", "callback_data": "modules_menu"}]
                ]
            }
            edit_message(chat_id, message_id, f"🚀 *MessengerUP Rasmiy Boti*\n\n🆔 ID: `{user_id}`\n💎 UpPremium: *{status_text}*\n✨ Balans: *{stars}*", kb)

class APIServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        try:
            uid = int(params.get("user_id", ["0"])[0])
        except ValueError:
            uid = 0

        # 1. Foydalanuvchi VIP statusi va balansini tekshirish
        if parsed.path == "/status":
            prem, stars, _ = get_user_data(uid)
            body = json.dumps({"is_premium": prem, "upstars": stars}).encode("utf-8")

        # 2. A foydalanuvchidan B foydalanuvchiga UP Stars o'tkazish
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
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass
if __name__ == "__main__":
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", 8080), APIServer).serve_forever(), daemon=True).start()
    print("✅ Bot va API server ishga tushdi!")
    offset = 0
    while True:
        res = tg_request("getUpdates", {"offset": offset, "timeout": 25})
        if res.get("ok"):
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                handle_update(upd)
        else:
            time.sleep(2)