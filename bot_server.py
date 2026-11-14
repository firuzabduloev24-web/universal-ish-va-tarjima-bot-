import hashlib
import html
import json
import os
import re
import sqlite3
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==============================================================================
# TOKEN VA ADMIN SOZLAMALARI
# ==============================================================================
TOKEN = (os.environ.get("BOT_TOKEN") or "").strip() or "9288572880:AAHaa4ea7lKvmSA8A4OMr0OJSMfv6SrZt54"
try:
    ADMIN_ID = int((os.environ.get("ADMIN_ID") or "").strip() or "1021089367")
except Exception:
    ADMIN_ID = 1021089367

try:
    PORT = int((os.environ.get("PORT") or "").strip() or "8080")
except Exception:
    PORT = 8080

API_URL = f"https://api.telegram.org/bot{TOKEN}/"
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(WORK_DIR, "up_ecosystem.db")
JSON_MIRROR_PATH = os.path.join(WORK_DIR, "users_status.json")
RAW_GITHUB_JSON = "https://raw.githubusercontent.com/firuzabduloev24-web/universal-ish-va-tarjima-bot-/main/users_status.json"

PREMIUM_PACKAGES = {
    "prem_monthly": {
        "months": 1,
        "title": "💎 UP Premium — 1 Oylik (Monthly)",
        "base_uzs": 35990,
        "uzs": "35 990,00 so'm",
        "usd": "$2.99"
    },
    "prem_annual": {
        "months": 12,
        "title": "💎 UP Premium — 1 Yillik (Annual -37%)",
        "base_uzs": 269990,
        "uzs": "269 990,00 so'm",
        "usd": "$21.99"
    }
}

STAR_PACKAGES = {
    "stars_100":    {"stars": 100,    "label": "100 Stars",     "base_uzs": 25399,    "uzs": "25 399,00 so'm",     "usd": "$1.99"},
    "stars_250":    {"stars": 250,    "label": "250 Stars",     "base_uzs": 59999,    "uzs": "59 999,00 so'm",     "usd": "$4.79"},
    "stars_500":    {"stars": 500,    "label": "500 Stars",     "base_uzs": 117999,   "uzs": "117 999,00 so'm",    "usd": "$9.49"},
    "stars_1000":   {"stars": 1000,   "label": "1 000 Stars",   "base_uzs": 233999,   "uzs": "233 999,00 so'm",    "usd": "$18.99"},
    "stars_2500":   {"stars": 2500,   "label": "2 500 Stars",   "base_uzs": 579999,   "uzs": "579 999,00 so'm",    "usd": "$45.99"},
    "stars_10000":  {"stars": 10000,  "label": "10 000 Stars",  "base_uzs": 2299999,  "uzs": "2 299 999,00 so'm",  "usd": "$179.99"},
    "stars_50000":  {"stars": 50000,  "label": "50 000 Stars",  "base_uzs": 11599999, "uzs": "11 599 999,00 so'm", "usd": "$899.99"},
    "stars_150000": {"stars": 150000, "label": "150 000 Stars", "base_uzs": 34999999, "uzs": "34 999 999,00 so'm", "usd": "$2,699.99"}
}

ALL_MODULES = ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
db_lock = threading.Lock()
git_lock = threading.Lock()

with db_lock:
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        is_premium INTEGER DEFAULT 0,
        upstars INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'uz',
        mod_config TEXT DEFAULT '{}',
        pending_pkg TEXT DEFAULT 'stars_1000'
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        user_id INTEGER,
        module_name TEXT,
        PRIMARY KEY (user_id, module_name)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payment_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pkg_key TEXT,
        unique_uzs INTEGER,
        status TEXT DEFAULT 'pending',
        created_at INTEGER
    )
    """)
    for sql_col in [
        "ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN upstars INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'uz'",
        "ALTER TABLE users ADD COLUMN mod_config TEXT DEFAULT '{}'",
        "ALTER TABLE users ADD COLUMN pending_pkg TEXT DEFAULT 'stars_1000'"
    ]:
        try:
            cur.execute(sql_col)
        except Exception:
            pass

    cur.execute("INSERT OR IGNORE INTO users (user_id, is_premium, upstars, lang, pending_pkg) VALUES (?, 1, 1000, 'uz', 'prem_annual')", (ADMIN_ID,))
    for m in ALL_MODULES:
        cur.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (ADMIN_ID, m))
    conn.commit()

# Mavjud users_status.json dan balanslarni yo'qotmasdan yuklab olish
def import_existing_json_balances():
    loaded = {}
    if os.path.exists(JSON_MIRROR_PATH):
        try:
            with open(JSON_MIRROR_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except Exception:
            pass
    if not loaded:
        try:
            req = urllib.request.Request(RAW_GITHUB_JSON + f"?t={int(time.time())}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                loaded = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

    if isinstance(loaded, dict):
        with db_lock:
            c = conn.cursor()
            for uid_str, info in loaded.items():
                if not str(uid_str).isdigit():
                    continue
                uid = int(uid_str)
                prem = 1 if info.get("is_premium") else 0
                stars = int(info.get("upstars", 0))
                lang = info.get("lang", "uz")
                c.execute("SELECT is_premium, upstars FROM users WHERE user_id = ?", (uid,))
                row = c.fetchone()
                if not row:
                    c.execute("INSERT INTO users (user_id, is_premium, upstars, lang) VALUES (?, ?, ?, ?)", (uid, prem, stars, lang))
                else:
                    c.execute("UPDATE users SET is_premium = MAX(is_premium, ?), upstars = MAX(upstars, ?) WHERE user_id = ?", (prem, stars, uid))
                if prem:
                    for m in ALL_MODULES:
                        c.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (uid, m))
            conn.commit()

def _safe_git_push():
    """Rebase to'qnashuvisiz toza va tezkor GitHub Push!"""
    with git_lock:
        try:
            if not os.path.exists(os.path.join(WORK_DIR, ".git")):
                return
            subprocess.run(["git", "config", "user.name", "UpPremium Bot"], cwd=WORK_DIR, timeout=5)
            subprocess.run(["git", "config", "user.email", "actions@github.com"], cwd=WORK_DIR, timeout=5)
            subprocess.run(["git", "fetch", "origin", "main"], cwd=WORK_DIR, timeout=15)
            subprocess.run(["git", "add", "users_status.json", "up_ecosystem.db"], cwd=WORK_DIR, timeout=5)
            subprocess.run(["git", "commit", "-m", f"AutoSync {int(time.time())}"], cwd=WORK_DIR, timeout=5)
            subprocess.run(["git", "push", "origin", "HEAD:main", "--force"], cwd=WORK_DIR, timeout=20)
        except Exception:
            pass

def sync_json_and_github(push_now=False):
    try:
        with db_lock:
            c = conn.cursor()
            c.execute("SELECT user_id, is_premium, upstars, lang FROM users")
            rows = c.fetchall()
            data = {}
            for uid, prem, stars, lang in rows:
                c.execute("SELECT module_name FROM modules WHERE user_id = ?", (uid,))
                mods = [r[0] for r in c.fetchall()]
                is_vip = bool(prem) or (len(mods) >= 4) or (uid == ADMIN_ID)
                data[str(uid)] = {
                    "is_premium": is_vip,
                    "upstars": int(stars or 0),
                    "lang": lang or "uz",
                    "modules": ALL_MODULES if is_vip else mods,
                    "updated_at": int(time.time())
                }
        with open(JSON_MIRROR_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if push_now:
            threading.Thread(target=_safe_git_push, daemon=True).start()
    except Exception:
        pass

def tg_request(method, payload=None):
    url = API_URL + method
    try:
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        try:
            err_body = he.read().decode("utf-8")
            return json.loads(err_body)
        except Exception:
            return {"ok": False, "error_code": he.code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# HTML rejimida xabar yuborish — "_" yoki "*" belgilari hech qachon xato bermaydi!
def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_request("sendMessage", payload)
    if not res.get("ok"):
        # Agar HTML tegda xato bo'lsa, oddiy matn sifatida majburiy yuboradi
        payload.pop("parse_mode", None)
        tg_request("sendMessage", payload)

def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_request("editMessageText", payload)
    if not res.get("ok"):
        send_message(chat_id, text, reply_markup)

def ensure_user(user_id, lang="uz", auto_vip=False):
    with db_lock:
        c = conn.cursor()
        c.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        vip = 1 if (user_id == ADMIN_ID or auto_vip) else 0
        if not row:
            c.execute("INSERT INTO users (user_id, is_premium, upstars, lang, pending_pkg) VALUES (?, ?, 0, ?, 'stars_1000')", (user_id, vip, lang))
        elif vip == 1 and row[0] == 0:
            c.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
        conn.commit()

def get_user_full(user_id):
    ensure_user(user_id)
    with db_lock:
        c = conn.cursor()
        c.execute("SELECT is_premium, upstars, lang, pending_pkg FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        prem = bool(row[0]) if row else False
        stars = int(row[1]) if row and row[1] else 0
        lang = row[2] if row and row[2] else "uz"
        pending_pkg = row[3] if row and row[3] else "stars_1000"
        c.execute("SELECT module_name FROM modules WHERE user_id = ?", (user_id,))
        mods = [r[0] for r in c.fetchall()]
        if prem and len(mods) < 4:
            mods = list(ALL_MODULES)
        return prem, stars, mods, lang, pending_pkg

# ==============================================================================
# MIJOZGA STAR VA PREMIUM BERISH FUNKSIYALARI (100% ISHLAYDIGAN)
# ==============================================================================
def give_stars_to_client(target_id, amount, admin_chat_id=ADMIN_ID):
    ensure_user(target_id)
    with db_lock:
        conn.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, target_id))
        conn.execute("UPDATE payment_orders SET status = 'completed' WHERE user_id = ? AND status = 'pending'", (target_id,))
        conn.commit()

    _, new_total, _, _, _ = get_user_full(target_id)
    sync_json_and_github(push_now=True)

    # Mijozga boradigan xabar (Ilova ichidagi MessageObject.java shu matnni o'qib darhol balansni yangilaydi!)
    client_msg = (
        f"✨ <b>+{amount} UP Stars</b> have been added to your balance!\n"
        f"✨ Hisobingizga <b>+{amount} UP Stars</b> qo'shildi!\n\n"
        f"⭐ Total: <b>{new_total}</b>\n"
        f"⭐ Jami balans: <b>{new_total}</b>\n"
        f"⭐ UP Stars Balance: <b>{new_total}</b>"
    )
    send_message(target_id, client_msg)
    send_message(admin_chat_id, f"✅ Mijoz <code>{target_id}</code> ga <b>+{amount} UP Stars</b> berildi!\n⭐ Mijozning yangi balansi: <b>{new_total} UP Stars</b>")

def give_vip_to_client(target_id, admin_chat_id=ADMIN_ID):
    ensure_user(target_id, auto_vip=True)
    with db_lock:
        conn.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (target_id,))
        for m in ALL_MODULES:
            conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (target_id, m))
        conn.execute("UPDATE payment_orders SET status = 'completed' WHERE user_id = ? AND status = 'pending'", (target_id,))
        conn.commit()

    _, stars, _, _, _ = get_user_full(target_id)
    sync_json_and_github(push_now=True)

    # Mijozga boradigan VIP xabar (Ilova buni o'qib shu soniyada UP Premium'ni yoqadi!)
    client_msg = (
        f"🎉 <b>Tabriklaymiz! / Congratulations!</b>\n\n"
        f"💎 <b>UP Premium:</b> Faol ✅ (VIP) / Active ✅ (VIP)\n"
        f"🧩 <b>4/4 special modules</b> (GhostVault, AIManager, MeshNetwork, MediaPaywall) faollashtirildi!\n"
        f"⭐ UP Stars Balance: <b>{stars}</b>"
    )
    send_message(target_id, client_msg)
    send_message(admin_chat_id, f"✅ Mijoz <code>{target_id}</code> ga <b>💎 UP Premium (VIP) + 4/4 Modullar</b> to'liq yoqildi!")

# ==============================================================================
# MENYU VA TUGMALAR
# ==============================================================================
def format_status_html(uid):
    prem, stars, mods, _, _ = get_user_full(uid)
    vip_txt = "Faol ✅ (VIP)" if prem else "Faol emas ❌"
    return (
        f"🚀 <b>MessengerUP Rasmiy To'lov va Ekotizim Boti</b>\n\n"
        f"🆔 Sizning ID: <code>{uid}</code>\n"
        f"💎 UP Premium: <b>{vip_txt}</b>\n"
        f"✨ UP Stars Balance: <b>{stars}</b>\n"
        f"🧩 Faol Modullar: <b>{len(mods)}/4</b>\n\n"
        f"Kerakli paket yoki bo'limni tanlang:"
    )

def build_main_kb(uid):
    rows = [
        [{"text": "💎 UP Premium Xarid Qilish (Oylik / Yillik -37%)", "callback_data": "menu_premium"}],
        [{"text": "✨ UP Stars Paketlari (100 — 150 000 Stars)", "callback_data": "menu_stars"}],
        [{"text": "🔄 Ilova bilan Sinxronlash (Sync)", "callback_data": f"sync_now_{uid}"}]
    ]
    if uid == ADMIN_ID:
        rows.append([{"text": "👑 ADMIN PANEL (Klientga Star / VIP Berish)", "callback_data": "admin_panel"}])
    return {"inline_keyboard": rows}

def build_admin_quick_kb(target_id, pending_pkg="stars_1000"):
    return {
        "inline_keyboard": [
            [{"text": f"⚡ 1-Bosishda Tasdiqlash ({pending_pkg})", "callback_data": f"adm_auto_{target_id}_{pending_pkg}"}],
            [
                {"text": "💎 VIP Yoqish (1 Oy/Yil)", "callback_data": f"adm_prem_{target_id}"}
            ],
            [
                {"text": "✨ +100", "callback_data": f"adm_star_{target_id}_100"},
                {"text": "✨ +250", "callback_data": f"adm_star_{target_id}_250"},
                {"text": "✨ +500", "callback_data": f"adm_star_{target_id}_500"},
                {"text": "✨ +1 000", "callback_data": f"adm_star_{target_id}_1000"}
            ],
            [
                {"text": "✨ +2 500", "callback_data": f"adm_star_{target_id}_2500"},
                {"text": "✨ +10 000", "callback_data": f"adm_star_{target_id}_10000"},
                {"text": "✨ +50 000", "callback_data": f"adm_star_{target_id}_50000"},
                {"text": "✨ +150 000", "callback_data": f"adm_star_{target_id}_150000"}
            ],
            [{"text": "❌ Chekni Rad Etish", "callback_data": f"adm_reject_{target_id}"}]
        ]
    }

def render_invoice_html(user_id, pkg_key):
    with db_lock:
        conn.execute("UPDATE users SET pending_pkg = ? WHERE user_id = ?", (pkg_key, user_id))
        conn.commit()

    if pkg_key in PREMIUM_PACKAGES:
        p = PREMIUM_PACKAGES[pkg_key]
        title, uzs, usd = p["title"], p["uzs"], p["usd"]
    else:
        s = STAR_PACKAGES.get(pkg_key, STAR_PACKAGES["stars_1000"])
        title, uzs, usd = f"✨ UP Stars — {s['label']}", s["uzs"], s["usd"]

    txt = (
        f"🧾 <b>Tanlangan paket:</b> {title}\n\n"
        f"🇺🇿 <b>O'zbekiston so'mida:</b> <code>{uzs}</code>\n"
        f"🌍 <b>Xalqaro (USD):</b> <code>{usd}</code>\n\n"
        f"💳 <b>To'lov rekvizitlari (Khasanov U.):</b>\n"
        f"🔹 <b>Uzcard:</b> <code>5614682112210333</code>\n"
        f"🔹 <b>Humo:</b> <code>9860170111318102</code>\n"
        f"🔹 <b>Visa SUM:</b> <code>4023060506933828</code>\n"
        f"🔹 <b>Visa USD:</b> <code>4023060246442007</code>\n\n"
        f"📌 <b>To'lov qilgach, chek (skrinshot)ni shu yerga tashlang — darhol faollashtiriladi!</b>\n"
        f"🆔 Sizning ID: <code>{user_id}</code>"
    )
    kb = {"inline_keyboard": [[{"text": "⬅️ Orqaga", "callback_data": "back_home"}]]}
    return txt, kb

def handle_update(update):
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id:
            return
        user = msg.get("from", {})
        user_id = user.get("id", chat_id)
        text = (msg.get("text") or "").strip()

        ensure_user(user_id)

        # ADMIN TEZKOR BUYRUQLARI:
        # 1) Faqat mijoz ID raqamini yuborsangiz (masalan: 654321987), shu zahoti unga Star va VIP berish tugmalarini chiqaradi!
        if user_id == ADMIN_ID and text.isdigit() and len(text) >= 5:
            target_id = int(text)
            prem, stars, _, _, p_pkg = get_user_full(target_id)
            adm_txt = (
                f"👑 <b>Mijoz Boshqaruv Paneli</b>\n\n"
                f"🆔 Mijoz ID: <code>{target_id}</code>\n"
                f"💎 Hozirgi VIP holati: <b>{'Faol ✅' if prem else 'Yoqilmagan ❌'}</b>\n"
                f"⭐ Hozirgi UP Stars balansi: <b>{stars}</b>\n\n"
                f"👇 Quyidagi tugmalardan birini bosib darhol bering:"
            )
            send_message(chat_id, adm_txt, build_admin_quick_kb(target_id, p_pkg))
            return

        # 2) /star ID MIQDOR yoki /vip ID buyruqlari
        if user_id == ADMIN_ID and (text.startswith("/star") or text.startswith("/give_stars")):
            parts = text.split()
            if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
                give_stars_to_client(int(parts[1]), int(parts[2]), chat_id)
            else:
                send_message(chat_id, "💡 Format: <code>/star MIJOZ_ID MIQDOR</code> (Masalan: <code>/star 1021089367 1000</code>)")
            return

        if user_id == ADMIN_ID and (text.startswith("/vip") or text.startswith("/give_prem")):
            parts = text.split()
            if len(parts) >= 2 and parts[1].isdigit():
                give_vip_to_client(int(parts[1]), chat_id)
            else:
                send_message(chat_id, "💡 Format: <code>/vip MIJOZ_ID</code> (Masalan: <code>/vip 1021089367</code>)")
            return

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""
            target_uid = user_id
            for tok in args.split("_"):
                if tok.isdigit() and len(tok) >= 6:
                    target_uid = int(tok)

            ensure_user(target_uid)
            sync_json_and_github(push_now=False)

            if "prem_annual" in args:
                t, k = render_invoice_html(target_uid, "prem_annual")
                send_message(chat_id, t, k)
            elif "prem_monthly" in args:
                t, k = render_invoice_html(target_uid, "prem_monthly")
                send_message(chat_id, t, k)
            elif any(sk in args for sk in STAR_PACKAGES.keys()):
                m_key = next(sk for sk in STAR_PACKAGES.keys() if sk in args)
                t, k = render_invoice_html(target_uid, m_key)
                send_message(chat_id, t, k)
            else:
                send_message(chat_id, format_status_html(target_uid), build_main_kb(target_uid))
            return

        # CHEK RASM YOKI FAYL KELGANDA
        if "photo" in msg or "document" in msg:
            _, _, _, _, pending_pkg = get_user_full(user_id)
            uname = f"@{html.escape(user.get('username'))}" if user.get("username") else "Username yo'q"
            fname = html.escape(f"{user.get('first_name', '')} {user.get('last_name', '')}".strip())

            caption = (
                f"💰 <b>Yangi To'lov Cheki Keldi!</b>\n"
                f"🆔 Mijoz ID: <code>{user_id}</code>\n"
                f"👤 Ism: {fname} ({uname})\n"
                f"📦 Tanlagan paketi: <b>{pending_pkg}</b>\n\n"
                f"👇 1-bosishda tasdiqlash uchun pastdagi tugmani bosing:"
            )
            kb = build_admin_quick_kb(user_id, pending_pkg)
            if "photo" in msg:
                tg_request("sendPhoto", {"chat_id": ADMIN_ID, "photo": msg["photo"][-1]["file_id"], "caption": caption, "parse_mode": "HTML", "reply_markup": kb})
            else:
                tg_request("sendDocument", {"chat_id": ADMIN_ID, "document": msg["document"]["file_id"], "caption": caption, "parse_mode": "HTML", "reply_markup": kb})

            send_message(chat_id, "✅ <b>To'lov chekingiz adminga yuborildi!</b> Hozir 1 daqiqa ichida faollashtiriladi.")

    elif "callback_query" in update:
        call = update["callback_query"]
        call_id = call.get("id")
        data = call.get("data", "") or ""
        user_id = call.get("from", {}).get("id", ADMIN_ID)
        msg_obj = call.get("message", {}) or {}
        chat_id = msg_obj.get("chat", {}).get("id", user_id)
        message_id = msg_obj.get("message_id", 0)

        tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": "⚡ Bajarilmoqda..."})

        if data == "back_home" or data.startswith("sync_now_"):
            sync_json_and_github(push_now=True)
            edit_message(chat_id, message_id, format_status_html(user_id), build_main_kb(user_id))

        elif data == "admin_panel" and user_id == ADMIN_ID:
            with db_lock:
                c = conn.cursor()
                c.execute("SELECT user_id, is_premium, upstars FROM users ORDER BY user_id DESC LIMIT 10")
                users_list = c.fetchall()
            u_lines = "\n".join([f"• ID: <code>{u[0]}</code> | VIP: {'✅' if u[1] else '❌'} | ⭐ {u[2]}" for u in users_list])
            adm_help = (
                f"👑 <b>ADMIN BOSHQARUV PANELI</b>\n\n"
                f"Klientga Star yoki VIP berishning <b>3 ta oson yo'li</b>:\n"
                f"1️⃣ Botga shunchaki klientning <b>ID raqamini</b> yozib yuboring (masalan: <code>1021089367</code>) — tayyor tugmalar chiqadi!\n"
                f"2️⃣ Buyruq bilan: <code>/star ID MIQDOR</code> yoki <code>/vip ID</code>\n"
                f"3️⃣ Chek tagidagi tayyor tugmani bosing.\n\n"
                f"📋 <b>Oxirgi foydalanuvchilar:</b>\n{u_lines}"
            )
            edit_message(chat_id, message_id, adm_help, {"inline_keyboard": [[{"text": "⬅️ Orqaga", "callback_data": "back_home"}]]})

        elif data == "menu_premium":
            kb = {
                "inline_keyboard": [
                    [{"text": "🌟 Annual (-37%) — 269 990,00 so'm / $21.99", "callback_data": "pkg_prem_annual"}],
                    [{"text": "💎 Monthly (1 oy) — 35 990,00 so'm / $2.99", "callback_data": "pkg_prem_monthly"}],
                    [{"text": "⬅️ Orqaga", "callback_data": "back_home"}]
                ]
            }
            edit_message(chat_id, message_id, "💎 <b>UP Premium Tarifini Tanlang:</b>", kb)

        elif data == "menu_stars":
            rows = []
            for k, inf in STAR_PACKAGES.items():
                rows.append([{"text": f"✨ {inf['label']} — {inf['uzs']} ({inf['usd']})", "callback_data": f"pkg_{k}"}])
            rows.append([{"text": "⬅️ Orqaga", "callback_data": "back_home"}])
            edit_message(chat_id, message_id, "✨ <b>UP Stars Paketini Tanlang:</b>", {"inline_keyboard": rows})

        elif data.startswith("pkg_"):
            pkg_key = data.replace("pkg_", "")
            t, k = render_invoice_html(user_id, pkg_key)
            edit_message(chat_id, message_id, t, k)

        elif data.startswith("adm_auto_") and user_id == ADMIN_ID:
            parts = data.split("_", 3)
            if len(parts) >= 4:
                t_id = int(parts[2])
                p_key = parts[3]
                if p_key in PREMIUM_PACKAGES:
                    give_vip_to_client(t_id, chat_id)
                elif p_key in STAR_PACKAGES:
                    give_stars_to_client(t_id, STAR_PACKAGES[p_key]["stars"], chat_id)
                else:
                    give_stars_to_client(t_id, 1000, chat_id)

        elif data.startswith("adm_star_") and user_id == ADMIN_ID:
            parts = data.split("_")
            if len(parts) >= 4:
                give_stars_to_client(int(parts[2]), int(parts[3]), chat_id)

        elif data.startswith("adm_prem_") and user_id == ADMIN_ID:
            parts = data.split("_")
            if len(parts) >= 3:
                give_vip_to_client(int(parts[2]), chat_id)

        elif data.startswith("adm_reject_") and user_id == ADMIN_ID:
            parts = data.split("_")
            if len(parts) >= 3:
                t_id = int(parts[2])
                send_message(t_id, "⚠️ To'lov chekingiz tasdiqlanmadi. Iltimos, qaytadan tekshirib yuboring.")
                send_message(chat_id, f"❌ Mijoz <code>{t_id}</code> cheki rad etildi.")

class APIServer(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            uid = int(params.get("user_id", ["0"])[0]) if params.get("user_id", ["0"])[0].isdigit() else 0

            if parsed.path == "/status":
                prem, stars, mods, lang, _ = get_user_full(uid)
                body = json.dumps({"is_premium": prem, "upstars": stars, "lang": lang, "modules": mods}).encode("utf-8")
            else:
                body = json.dumps({"status": "MessengerUP Server 24/7 Active"}).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def log_message(self, format, *args):
        pass

def start_http_server():
    for p in [PORT, 8081, 8082, 0]:
        try:
            HTTPServer(("0.0.0.0", p), APIServer).serve_forever()
            break
        except Exception:
            continue

if __name__ == "__main__":
    import_existing_json_balances()
    sync_json_and_github(push_now=False)
    tg_request("deleteWebhook", {"drop_pending_updates": False})
    threading.Thread(target=start_http_server, daemon=True).start()
    print("✅ BOT 100% ISHGA TUSHDI! Endi Telegramda botga /start yoki Mijoz ID raqamini yozing!", flush=True)

    offset = 0
    while True:
        try:
            res = tg_request("getUpdates", {"offset": offset, "timeout": 20})
            if res.get("ok"):
                for upd in res.get("result", []):
                    offset = upd["update_id"] + 1
                    try:
                        handle_update(upd)
                    except Exception as e:
                        print("Update xatosi o'tkazib yuborildi:", e, flush=True)
            else:
                time.sleep(2)
        except Exception:
            time.sleep(2)
