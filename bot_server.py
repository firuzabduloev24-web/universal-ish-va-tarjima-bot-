import hashlib
import json
import os
import random
import re
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ.get("BOT_TOKEN", "9288572880:AAHaa4ea7lKvmSA8A4OMr0OJSMfv6SrZt54")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1021089367"))
ADMIN_USERNAME = "@usman_khasan"
SMS_SECRET = os.environ.get("SMS_SECRET", "khasanov_auto_pay_2026")
CRYPTO_PAY_TOKEN = os.environ.get("CRYPTO_PAY_TOKEN", "")  # @CryptoBot API token (ixtiyoriy)
API_URL = f"https://api.telegram.org/bot{TOKEN}/"
PORT = int(os.environ.get("PORT", 8080))

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(WORK_DIR, "up_ecosystem.db")
JSON_MIRROR_PATH = os.path.join(WORK_DIR, "users_status.json")

# ==============================================================================
# MESSENGER UP ILOVASI BILAN 1:1 SINXRON TARIFLAR (ASOSIY NARX SONDA HAM BERILGAN)
# ==============================================================================
PREMIUM_PACKAGES = {
    "prem_monthly": {
        "months": 1,
        "title_uz": "💎 UP Premium — 1 Oylik (Monthly)",
        "title_ru": "💎 UP Premium — 1 Месяц (Monthly)",
        "title_en": "💎 UP Premium — Monthly (1 Month)",
        "base_uzs": 35990,
        "base_usd": 2.99,
        "uzs": "35 990,00 so'm",
        "usd": "$2.99"
    },
    "prem_annual": {
        "months": 12,
        "title_uz": "💎 UP Premium — 1 Yillik (Annual -37%)",
        "title_ru": "💎 UP Premium — 1 Год (Annual -37%)",
        "title_en": "💎 UP Premium — Annual (-37% | 1 Year)",
        "base_uzs": 269990,
        "base_usd": 21.99,
        "uzs": "269 990,00 so'm",
        "usd": "$21.99"
    }
}

STAR_PACKAGES = {
    "stars_100":    {"stars": 100,    "label": "100 Stars",     "base_uzs": 25399,    "base_usd": 1.99,    "uzs": "25 399,00 so'm",     "usd": "$1.99"},
    "stars_250":    {"stars": 250,    "label": "250 Stars",     "base_uzs": 59999,    "base_usd": 4.79,    "uzs": "59 999,00 so'm",     "usd": "$4.79"},
    "stars_500":    {"stars": 500,    "label": "500 Stars",     "base_uzs": 117999,   "base_usd": 9.49,    "uzs": "117 999,00 so'm",    "usd": "$9.49"},
    "stars_1000":   {"stars": 1000,   "label": "1 000 Stars",   "base_uzs": 233999,   "base_usd": 18.99,   "uzs": "233 999,00 so'm",    "usd": "$18.99"},
    "stars_2500":   {"stars": 2500,   "label": "2 500 Stars",   "base_uzs": 579999,   "base_usd": 45.99,   "uzs": "579 999,00 so'm",    "usd": "$45.99"},
    "stars_10000":  {"stars": 10000,  "label": "10 000 Stars",  "base_uzs": 2299999,  "base_usd": 179.99,  "uzs": "2 299 999,00 so'm",  "usd": "$179.99"},
    "stars_50000":  {"stars": 50000,  "label": "50 000 Stars",  "base_uzs": 11599999, "base_usd": 899.99,  "uzs": "11 599 999,00 so'm", "usd": "$899.99"},
    "stars_150000": {"stars": 150000, "label": "150 000 Stars", "base_uzs": 34999999, "base_usd": 2699.99, "uzs": "34 999 999,00 so'm", "usd": "$2,699.99"}
}

DEFAULT_MOD_CONFIG = {
    "GhostVault": {"enabled": True, "anti_screenshot": True, "decoy_pin": True, "timer": "30s"},
    "AIManager": {"enabled": True, "auto_reply": True, "live_translate": True, "voice_summary": True},
    "MeshNetwork": {"enabled": True, "p2p_bridge": True, "stealth_dpi": True, "mined_stars": 15},
    "MediaPaywall": {"enabled": True, "default_price": 25, "earned_stars": 0, "sales_count": 0}
}

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
db_lock = threading.Lock()

with db_lock:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        is_premium INTEGER DEFAULT 0,
        upstars INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'en',
        mod_config TEXT DEFAULT '{}',
        pending_pkg TEXT DEFAULT 'prem_monthly'
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        user_id INTEGER,
        module_name TEXT,
        PRIMARY KEY (user_id, module_name)
    )
    """)
    # AVTO-TO'LOV BUYURTMALAR JADVALI (Dinamik noyob summa va navbat uchun)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pkg_key TEXT,
        unique_uzs INTEGER,
        status TEXT DEFAULT 'pending',
        created_at INTEGER
    )
    """)
    # ANTI-DUBLIKAT CHEKLAR JADVALI (Bitta chekni 2 marta tashlashni bloklaydi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS used_receipts (
        file_hash TEXT PRIMARY KEY,
        user_id INTEGER,
        used_at INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS translations (
        lang TEXT,
        src_key TEXT,
        translated_text TEXT,
        PRIMARY KEY (lang, src_key)
    )
    """)
    for col_sql in [
        "ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'en'",
        "ALTER TABLE users ADD COLUMN mod_config TEXT DEFAULT '{}'",
        "ALTER TABLE users ADD COLUMN pending_pkg TEXT DEFAULT 'prem_monthly'"
    ]:
        try:
            cursor.execute(col_sql)
        except Exception:
            pass

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, is_premium, upstars, lang, mod_config, pending_pkg) VALUES (?, 1, 1000, 'uz', ?, 'prem_annual')",
        (ADMIN_ID, json.dumps(DEFAULT_MOD_CONFIG))
    )
    cursor.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (ADMIN_ID,))
    for m in ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]:
        cursor.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (ADMIN_ID, m))
    conn.commit()

CORE_STRINGS = {
    "en": {
        "title": "🚀 *MessengerUP Official Payment & Ecosystem Bot*",
        "your_id": "🆔 Your ID:",
        "vip_status": "💎 UP Premium:",
        "active": "Active ✅ (VIP)",
        "inactive": "Inactive ❌",
        "balance": "✨ UP Stars Balance:",
        "active_mods": "🧩 Active Modules:",
        "choose": "Select a package or section below:",
        "btn_buy_prem": "💎 Buy UP Premium (Monthly / Annual -37%)",
        "btn_buy_stars": "✨ Buy UP Stars (100 — 150,000 Packages)",
        "btn_mods": "🧩 4 Special Modules (Live Control Center)",
        "btn_lang": "🌐 Language",
        "btn_sync": "🔄 Sync with App",
        "btn_back": "⬅️ Back",
        "btn_check_auto": "⚡ Check Payment Automatically",
        "prem_menu_title": "💎 *UP Premium Subscription*\nGo beyond the limits and unlock exclusive features:\n\n• *Annual (-37%):* `269 990,00 so'm/year` (`$21.99`)\n• *Monthly:* `35 990,00 so'm/month` (`$2.99`)\n\nSelect your plan:",
        "stars_menu_title": "✨ *UP Stars — Choose Package*\nSelect the amount of UP Stars you want to purchase:",
        "invoice_title": "🧾 *Order #{order_id}:*",
        "invoice_exact_uzs": "⚡ *EXACT Auto-Pay Amount (UZS):*",
        "invoice_usd": "🌍 *International Price (USD):*",
        "invoice_cards": "💳 *Payment Details (Khasanov U.):*\n🔹 *Uzcard:* `5614682112210333`\n🔹 *Humo:* `9860170111318102`\n🔹 *Visa Local (UZS):* `4023060506933828`\n🔹 *Visa Global (USD):* `4023060246442007`\n\n🤖 *AUTO-VERIFICATION:* Transfer the *exact UZS amount* shown above (`{exact_uzs} so'm`) for instant 1-second activation, OR send your receipt screenshot here!",
        "receipt_sent": "✅ Receipt verified (Unique Check: OK) and queued! Your package will be activated shortly.",
        "dup_receipt": "❌ *Error:* This payment receipt has already been used! Please send a valid new receipt.",
        "vip_activated_msg": "🎉 *Congratulations!* Your *UP Premium (VIP)* and all 4/4 special modules have been activated automatically!",
        "stars_added_msg": "✨ *+{amount} UP Stars* have been added to your balance!",
        "mod_hub_title": "🧩 *4 Special Modules Control Center*\nTap any module below to configure settings:"
    },
    "uz": {
        "title": "🚀 *MessengerUP Rasmiy Avto-To'lov va Ekotizim Boti*",
        "your_id": "🆔 Sizning ID:",
        "vip_status": "💎 UP Premium:",
        "active": "Faol ✅ (VIP)",
        "inactive": "Faol emas ❌",
        "balance": "✨ UP Stars Balansi:",
        "active_mods": "🧩 Faol Modullar:",
        "choose": "Kerakli paket yoki bo'limni tanlang:",
        "btn_buy_prem": "💎 UP Premium Xarid Qilish (Oylik / Yillik -37%)",
        "btn_buy_stars": "✨ UP Stars Paketlari (100 — 150 000 Stars)",
        "btn_mods": "🧩 4 ta Maxsus Modul (Boshqaruv Markazi)",
        "btn_lang": "🌐 Til / Language",
        "btn_sync": "🔄 Ilova bilan Sinxronlash",
        "btn_back": "⬅️ Orqaga",
        "btn_check_auto": "⚡ To'lovni Avto-Tekshirish",
        "prem_menu_title": "💎 *UP Premium Obunasi*\nCheklovlarsiz barcha eksklyuziv funksiyalarni yoqing:\n\n• *Annual (Yillik -37%):* `269 990,00 so'm/yil` (`$21.99`)\n• *Monthly (Oylik):* `35 990,00 so'm/oy` (`$2.99`)\n\nKerakli tarifni tanlang:",
        "stars_menu_title": "✨ *UP Stars — Paketni tanlang*\nXarid qilmoqchi bo'lgan UP Stars paketingizni bosing:",
        "invoice_title": "🧾 *Buyurtma #{order_id}:*",
        "invoice_exact_uzs": "⚡ *AVTO-TASDIQLASH UCHUN ANIQ SUMMA:*",
        "invoice_usd": "🌍 *Xalqaro to'lov (USD):*",
        "invoice_cards": "💳 *To'lov rekvizitlari (Khasanov U.):*\n🔹 *Uzcard:* `5614682112210333`\n🔹 *Humo:* `9860170111318102`\n🔹 *Visa SUM:* `4023060506933828`\n🔹 *Visa USD:* `4023060246442007`\n\n🤖 *1-SONIYADA AVTO-YOQISH:* Kartaga aynan yuqoridagi *noyob summani* (`{exact_uzs} so'm`) o'tkazing (tizim SMS orqali avtomatik taniydi) YOKI to'lov chekini shu yerga tashlang!",
        "receipt_sent": "✅ Chek haqiqiyligi tekshirildi (Dublikat emas: OK) va navbatga qo'shildi! Hozir faollashtiriladi.",
        "dup_receipt": "❌ *Diqqat!* Bu to'lov cheki avval ishlatilgan! Iltimos, haqiqiy yangi to'lov chekini yuboring.",
        "vip_activated_msg": "🎉 *Tabriklaymiz!* Sizga *UP Premium (VIP)* va barcha 4/4 maxsus modullar avtomatik faollashtirildi!",
        "stars_added_msg": "✨ Hisobingizga *+{amount} UP Stars* avtomatik qo'shildi!",
        "mod_hub_title": "🧩 *4 ta Maxsus Modul Boshqaruv Markazi*\nSozlash uchun kerakli modulni tanlang:"
    },
    "ru": {
        "title": "🚀 *Официальный Бот Авто-Оплаты MessengerUP*",
        "your_id": "🆔 Ваш ID:",
        "vip_status": "💎 UP Premium:",
        "active": "Активен ✅ (VIP)",
        "inactive": "Не активен ❌",
        "balance": "✨ Баланс UP Stars:",
        "active_mods": "🧩 Активные модули:",
        "choose": "Выберите нужный пакет или раздел:",
        "btn_buy_prem": "💎 Купить UP Premium (Месяц / Год -37%)",
        "btn_buy_stars": "✨ Пакеты UP Stars (100 — 150 000 Stars)",
        "btn_mods": "🧩 4 Спец-Модуля (Центр Управления)",
        "btn_lang": "🌐 Язык / Language",
        "btn_sync": "🔄 Синхронизация",
        "btn_back": "⬅️ Назад",
        "btn_check_auto": "⚡ Авто-Проверка Оплаты",
        "prem_menu_title": "💎 *Подписка UP Premium*\nОткройте все эксклюзивные возможности:\n\n• *Annual (Годовой -37%):* `269 990,00 сум/год` (`$21.99`)\n• *Monthly (Месячный):* `35 990,00 сум/мес` (`$2.99`)\n\nВыберите тариф:",
        "stars_menu_title": "✨ *UP Stars — Выберите пакет*\nНажмите на нужный пакет UP Stars:",
        "invoice_title": "🧾 *Заказ #{order_id}:*",
        "invoice_exact_uzs": "⚡ *ТОЧНАЯ СУММА ДЛЯ АВТО-ОПЛАТЫ:*",
        "invoice_usd": "🌍 *Цена в долларах (USD):*",
        "invoice_cards": "💳 *Реквизиты для оплаты (Khasanov U.):*\n🔹 *Uzcard:* `5614682112210333`\n🔹 *Humo:* `9860170111318102`\n🔹 *Visa UZS:* `4023060506933828`\n🔹 *Visa USD:* `4023060246442007`\n\n🤖 *АВТО-АКТИВАЦИЯ ЗА 1 СЕКУНДУ:* Переведите ровно указанную сумму (`{exact_uzs} сум`) для автоматического распознавания ИЛИ отправьте скриншот чека сюда!",
        "receipt_sent": "✅ Чек прошел проверку на уникальность и поставлен в очередь! Пакет скоро активируется.",
        "dup_receipt": "❌ *Ошибка!* Этот чек уже был использован ранее! Отправьте новый действительный чек.",
        "vip_activated_msg": "🎉 *Поздравляем!* Вам автоматически активирован *UP Premium (VIP)* и все 4/4 спец-модуля!",
        "stars_added_msg": "✨ На ваш баланс зачислено *+{amount} UP Stars*!",
        "mod_hub_title": "🧩 *Центр Управления 4 Спец-Модулями*\nВыберите модуль для настройки:"
    }
}

def auto_translate_gtx(text, target_lang):
    target_lang = (target_lang or "en").lower().split("-")[0][:2]
    if target_lang in ["uz", "ru", "en"]:
        return text
    cache_key = f"{target_lang}:{text}"
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT translated_text FROM translations WHERE lang = ? AND src_key = ?", (target_lang, cache_key[:180]))
        row = cur.fetchone()
        if row:
            return row[0]
    try:
        q = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target_lang}&dt=t&q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            arr = json.loads(resp.read().decode("utf-8"))
            translated = "".join([part[0] for part in arr[0] if part[0]])
            if translated:
                with db_lock:
                    conn.execute(
                        "INSERT OR REPLACE INTO translations (lang, src_key, translated_text) VALUES (?, ?, ?)",
                        (target_lang, cache_key[:180], translated)
                    )
                    conn.commit()
                return translated
    except Exception:
        pass
    return text

def tr_str(lang, key):
    lang = (lang or "en").lower().split("-")[0][:2]
    if lang in CORE_STRINGS and key in CORE_STRINGS[lang]:
        return CORE_STRINGS[lang][key]
    en_val = CORE_STRINGS["en"].get(key, key)
    return auto_translate_gtx(en_val, lang)

def ensure_user(user_id, detected_lang=None, auto_vip=False):
    lang_code = (detected_lang or "en").lower().split("-")[0][:2]
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT is_premium, lang FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        is_vip = 1 if (user_id == ADMIN_ID or auto_vip) else 0
        if not row:
            cur.execute(
                "INSERT INTO users (user_id, is_premium, upstars, lang, mod_config, pending_pkg) VALUES (?, ?, 0, ?, ?, 'prem_monthly')",
                (user_id, is_vip, lang_code, json.dumps(DEFAULT_MOD_CONFIG))
            )
            conn.commit()
        else:
            if is_vip == 1 and row[0] == 0:
                cur.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
                conn.commit()

def get_user_full(user_id):
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT module_name FROM modules WHERE user_id = ?", (user_id,))
        mods = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT is_premium, upstars, lang, mod_config, pending_pkg FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        prem = bool(row[0]) if row else False
        stars = row[1] if row else 0
        lang = (row[2] if row and row[2] else "en")
        pending_pkg = (row[4] if row and len(row) > 4 and row[4] else "prem_monthly")
        try:
            cfg = json.loads(row[3]) if row and row[3] else {}
        except Exception:
            cfg = {}
        for k, v in DEFAULT_MOD_CONFIG.items():
            if k not in cfg:
                cfg[k] = dict(v)
        if (user_id == ADMIN_ID or len(mods) >= 4) and not prem:
            prem = True
            cur.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        return prem, stars, mods, lang, cfg, pending_pkg

# ==============================================================================
# AVTO-TO'LOV GENERATORI VA FULFILLMENT ENGINE
# ==============================================================================
def create_unique_order(user_id, pkg_key):
    """Har bir mijozga 30 daqiqa davomida takrorlanmas noyob so'm summasini (masalan 35990 -> 35994) yaratadi."""
    now = int(time.time())
    base_uzs = PREMIUM_PACKAGES[pkg_key]["base_uzs"] if pkg_key in PREMIUM_PACKAGES else STAR_PACKAGES.get(pkg_key, STAR_PACKAGES["stars_100"])["base_uzs"]

    with db_lock:
        conn.execute("UPDATE users SET pending_pkg = ? WHERE user_id = ?", (pkg_key, user_id))
        cur = conn.cursor()
        # Oxirgi 30 daqiqadagi band summalarni tekshirish
        cur.execute("SELECT unique_uzs FROM payment_orders WHERE status = 'pending' AND created_at > ?", (now - 1800,))
        used_amounts = {r[0] for r in cur.fetchall()}

        unique_uzs = base_uzs + 1
        for offset in range(1, 99):
            candidate = base_uzs + offset
            if candidate not in used_amounts:
                unique_uzs = candidate
                break

        cur.execute(
            "INSERT INTO payment_orders (user_id, pkg_key, unique_uzs, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (user_id, pkg_key, unique_uzs, now)
        )
        order_id = cur.lastrowid
        conn.commit()
    return order_id, unique_uzs

def fulfill_package_for_user(target_id, pkg_key, source_label="Auto-System"):
    """Mijoz tanlagan paketni (VIP yoki 100..150000 UP Stars) avtomatik hisobga yozadi."""
    ensure_user(target_id)
    _, _, _, target_lang, _, _ = get_user_full(target_id)

    if pkg_key in PREMIUM_PACKAGES:
        with db_lock:
            conn.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (target_id,))
            for m in ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]:
                conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (target_id, m))
            conn.execute("UPDATE payment_orders SET status = 'completed' WHERE user_id = ? AND status = 'pending'", (target_id,))
            conn.commit()
        sync_json_and_github()
        send_message(target_id, tr_str(target_lang, "vip_activated_msg"))
        send_message(ADMIN_ID, f"⚡ *[{source_label}]* `{target_id}` ga *{pkg_key}* avtomatik yoqildi!")
        return True
    elif pkg_key in STAR_PACKAGES:
        amount = STAR_PACKAGES[pkg_key]["stars"]
        with db_lock:
            conn.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, target_id))
            conn.execute("UPDATE payment_orders SET status = 'completed' WHERE user_id = ? AND status = 'pending'", (target_id,))
            conn.commit()
        sync_json_and_github()
        send_message(target_id, tr_str(target_lang, "stars_added_msg").replace("{amount}", str(amount)))
        send_message(ADMIN_ID, f"⚡ *[{source_label}]* `{target_id}` ga *+{amount} UP Stars* avtomatik qo'shildi!")
        return True
    return False

def match_sms_and_auto_activate(sms_text):
    """Telefondan kelgan Humo/Uzcard/Click/Payme SMS matnidan summani topib, 1 soniyada avto-tasdiqlaydi."""
    clean = sms_text.replace(" ", "").replace(",", ".").replace("'", "")
    numbers = re.findall(r"\d{5,9}", clean)
    now = int(time.time())

    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT order_id, user_id, pkg_key, unique_uzs FROM payment_orders WHERE status = 'pending' AND created_at > ? ORDER BY order_id DESC", (now - 3600,))
        pending_orders = cur.fetchall()

    for num_str in numbers:
        val = int(num_str)
        for oid, uid, pkey, u_uzs in pending_orders:
            if val == u_uzs:
                fulfill_package_for_user(uid, pkey, source_label=f"SMS-Auto #{oid}")
                return True, uid, pkey
    return False, 0, ""

def sync_json_and_github():
    try:
        with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT user_id, is_premium, upstars, lang, mod_config FROM users")
            rows = cur.fetchall()
            data = {}
            for uid, prem, stars, lang, mcfg in rows:
                cur.execute("SELECT module_name FROM modules WHERE user_id = ?", (uid,))
                mods = [r[0] for r in cur.fetchall()]
                data[str(uid)] = {
                    "is_premium": bool(prem) or (len(mods) >= 4) or (uid == ADMIN_ID),
                    "upstars": stars,
                    "lang": lang or "en",
                    "modules": mods
                }
        with open(JSON_MIRROR_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
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

def build_main_menu_kb(target_uid, lang):
    return {
        "inline_keyboard": [
            [{"text": tr_str(lang, "btn_buy_prem"), "callback_data": "menu_premium"}],
            [{"text": tr_str(lang, "btn_buy_stars"), "callback_data": "menu_stars"}],
            [{"text": tr_str(lang, "btn_mods"), "callback_data": "modules_menu"}],
            [
                {"text": tr_str(lang, "btn_lang"), "callback_data": "lang_menu"},
                {"text": tr_str(lang, "btn_sync"), "callback_data": f"sync_now_{target_uid}"}
            ]
        ]
    }

def build_premium_packages_kb(lang):
    return {
        "inline_keyboard": [
            [{"text": "🌟 Annual (-37%) — 269 990,00 so'm / $21.99", "callback_data": "pkg_prem_annual"}],
            [{"text": "💎 Monthly (1 oy) — 35 990,00 so'm / $2.99", "callback_data": "pkg_prem_monthly"}],
            [{"text": tr_str(lang, "btn_back"), "callback_data": "back_home"}]
        ]
    }

def build_stars_packages_kb(lang):
    rows = []
    for key, info in STAR_PACKAGES.items():
        btn_txt = f"✨ {info['label']} — {info['uzs']} ({info['usd']})"
        rows.append([{"text": btn_txt, "callback_data": f"pkg_{key}"}])
    rows.append([{"text": tr_str(lang, "btn_back"), "callback_data": "back_home"}])
    return {"inline_keyboard": rows}

def render_package_invoice(user_id, pkg_key, lang):
    order_id, exact_uzs = create_unique_order(user_id, pkg_key)
    formatted_exact = f"{exact_uzs:,}".replace(",", " ")

    if pkg_key in PREMIUM_PACKAGES:
        p = PREMIUM_PACKAGES[pkg_key]
        t_key = f"title_{lang}" if f"title_{lang}" in p else "title_en"
        pkg_title = p[t_key]
        usd_price = p["usd"]
        back_target = "menu_premium"
    else:
        s = STAR_PACKAGES.get(pkg_key, STAR_PACKAGES["stars_100"])
        pkg_title = f"✨ UP Stars — {s['label']}"
        usd_price = s["usd"]
        back_target = "menu_stars"

    cards_block = tr_str(lang, "invoice_cards").replace("{exact_uzs}", formatted_exact)
    text = (
        f"{tr_str(lang, 'invoice_title').replace('{order_id}', str(order_id))} *{pkg_title}*\n\n"
        f"{tr_str(lang, 'invoice_exact_uzs')} `{formatted_exact} so'm`\n"
        f"{tr_str(lang, 'invoice_usd')} `{usd_price}`\n\n"
        f"{cards_block}\n"
        f"🆔 ID: `{user_id}`"
    )
    kb = {
        "inline_keyboard": [
            [{"text": tr_str(lang, "btn_check_auto"), "callback_data": f"chk_ord_{order_id}"}],
            [{"text": tr_str(lang, "btn_back"), "callback_data": back_target}]
        ]
    }
    return text, kb

def format_status_text(target_uid):
    prem, stars, mods, lang, _, _ = get_user_full(target_uid)
    st = tr_str(lang, "active") if prem else tr_str(lang, "inactive")
    return (
        f"{tr_str(lang, 'title')}\n\n"
        f"{tr_str(lang, 'your_id')} `{target_uid}`\n"
        f"{tr_str(lang, 'vip_status')} *{st}*\n"
        f"{tr_str(lang, 'balance')} *{stars}*\n"
        f"{tr_str(lang, 'active_mods')} *{len(mods)}/4* (`GhostVault`, `AIManager`, `Mesh`, `Paywall`)\n\n"
        f"{tr_str(lang, 'choose')}"
    )

def handle_update(update):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = msg.get("from", {})
        user_id = user.get("id", chat_id)
        text = msg.get("text", "")

        tg_lang = user.get("language_code", "uz")
        tg_is_prem = bool(user.get("is_premium", False))
        ensure_user(user_id, detected_lang=tg_lang, auto_vip=tg_is_prem)

        # ADMIN BANK SMS MATNINI BOTGA FORWARD QILSA HAM AVTOMATIK TOPADI!
        if user_id == ADMIN_ID and any(w in text.upper() for w in ["UZS", "HUMO", "UZCARD", "POPOLNENIE", "KIRIM", "SUM"]):
            ok, matched_uid, matched_pkg = match_sms_and_auto_activate(text)
            if ok:
                return

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""
            target_uid = user_id
            app_vip = tg_is_prem
            chosen_lang = tg_lang

            if "vip1" in args:
                app_vip = True
            if "lang_" in args:
                m_l = args.split("lang_")[-1].split("_")[0][:2]
                if m_l.isalpha():
                    chosen_lang = m_l.lower()
                    with db_lock:
                        conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (chosen_lang, user_id))
                        conn.commit()

            for token_part in args.split("_"):
                if token_part.isdigit() and len(token_part) >= 6:
                    target_uid = int(token_part)

            ensure_user(target_uid, detected_lang=chosen_lang, auto_vip=app_vip)
            _, _, _, lang, _, _ = get_user_full(target_uid)
            sync_json_and_github()

            if "prem_annual" in args:
                inv_txt, inv_kb = render_package_invoice(target_uid, "prem_annual", lang)
                send_message(chat_id, inv_txt, inv_kb)
            elif "prem_monthly" in args:
                inv_txt, inv_kb = render_package_invoice(target_uid, "prem_monthly", lang)
                send_message(chat_id, inv_txt, inv_kb)
            elif "pay_premium" in args:
                send_message(chat_id, tr_str(lang, "prem_menu_title"), build_premium_packages_kb(lang))
            elif any(k in args for k in STAR_PACKAGES.keys()):
                matched_key = next(k for k in STAR_PACKAGES.keys() if k in args)
                inv_txt, inv_kb = render_package_invoice(target_uid, matched_key, lang)
                send_message(chat_id, inv_txt, inv_kb)
            elif "pay_stars" in args:
                send_message(chat_id, tr_str(lang, "stars_menu_title"), build_stars_packages_kb(lang))
            else:
                send_message(chat_id, format_status_text(target_uid), build_main_menu_kb(target_uid, lang))

        # ADMIN UCHUN 1-BUYRUQDA NAVBATDAGI BARCHA CHEKLARNI TASDIQLASH
        elif text.startswith("/approve_all") and user_id == ADMIN_ID:
            with db_lock:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT user_id, pkg_key FROM payment_orders WHERE status = 'pending'")
                rows = cur.fetchall()
            count = 0
            for uid, pkey in rows:
                if fulfill_package_for_user(uid, pkey, source_label="Batch-Admin"):
                    count += 1
            send_message(chat_id, f"✅ Navbatdagi *{count} ta* buyurtma birdaniga tasdiqlandi!")

        elif "photo" in msg or "document" in msg:
            _, _, _, lang, _, pending_pkg = get_user_full(user_id)

            # 1. ANTI-DUBLIKAT TEKSHIRUVI (Bitta skrinshotni ikki marta yuborishni 100% bloklaydi!)
            if "photo" in msg:
                f_uniq = msg["photo"][-1].get("file_unique_id", "")
                f_size = str(msg["photo"][-1].get("file_size", 0))
            else:
                f_uniq = msg["document"].get("file_unique_id", "")
                f_size = str(msg["document"].get("file_size", 0))

            receipt_hash = hashlib.sha256(f"{f_uniq}_{f_size}".encode()).hexdigest()
            with db_lock:
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM used_receipts WHERE file_hash = ?", (receipt_hash,))
                if cur.fetchone():
                    send_message(chat_id, tr_str(lang, "dup_receipt"))
                    return
                conn.execute("INSERT INTO used_receipts (file_hash, user_id, used_at) VALUES (?, ?, ?)", (receipt_hash, user_id, int(time.time())))
                conn.commit()

            username = f"@{user.get('username')}" if user.get("username") else "N/A"
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

            if pending_pkg in PREMIUM_PACKAGES:
                p_info = PREMIUM_PACKAGES[pending_pkg]
                pkg_desc = f"{p_info['title_uz']} ({p_info['uzs']})"
            elif pending_pkg in STAR_PACKAGES:
                s_info = STAR_PACKAGES[pending_pkg]
                pkg_desc = f"UP Stars: {s_info['label']} ({s_info['uzs']})"
            else:
                pkg_desc = pending_pkg

            caption = (
                f"💰 *Toza Chek (Anti-Dublikat: OK ✅)*\n"
                f"🆔 ID: `{user_id}` | 🌐 Til: `{lang.upper()}`\n"
                f"👤 {full_name} ({username})\n"
                f"📦 *Paket:* `{pkg_desc}`"
            )
            # ENG TEZKOR 1-TUGMA: Aynan foydalanuvchi tanlagan paketni 1-bosishda beradi!
            admin_kb = {
                "inline_keyboard": [
                    [{"text": f"⚡ 1-Click Tasdiqlash: {pkg_desc}", "callback_data": f"adm_auto_{user_id}_{pending_pkg}"}],
                    [{"text": "🚀 Barcha Navbatdagilarni Tasdiqlash (/approve_all)", "callback_data": "adm_batch_all"}],
                    [{"text": "❌ Chekni Rad Etish", "callback_data": f"adm_reject_{user_id}"}]
                ]
            }
            if "photo" in msg:
                tg_request("sendPhoto", {"chat_id": ADMIN_ID, "photo": msg["photo"][-1]["file_id"], "caption": caption, "parse_mode": "Markdown", "reply_markup": admin_kb})
            elif "document" in msg:
                tg_request("sendDocument", {"chat_id": ADMIN_ID, "document": msg["document"]["file_id"], "caption": caption, "parse_mode": "Markdown", "reply_markup": admin_kb})
            send_message(chat_id, tr_str(lang, "receipt_sent"))

    elif "callback_query" in update:
        call = update["callback_query"]
        call_id = call["id"]
        data = call.get("data", "")
        user_id = call["from"]["id"]
        chat_id = call["message"]["chat"]["id"]
        message_id = call["message"]["message_id"]

        prem, stars, mods, lang, cfg, _ = get_user_full(user_id)

        if data.startswith("chk_ord_"):
            order_id = int(data.split("_")[2])
            with db_lock:
                cur = conn.cursor()
                cur.execute("SELECT status FROM payment_orders WHERE order_id = ?", (order_id,))
                r = cur.fetchone()
            if r and r[0] == "completed":
                tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": "✅ Payment confirmed! Package active!", "show_alert": True})
                edit_message(chat_id, message_id, format_status_text(user_id), build_main_menu_kb(user_id, lang))
            else:
                tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": "⏳ SMS hali kelmadi yoki chek skrinshotini shu yerga tashlang!", "show_alert": True})
            return

        tg_request("answerCallbackQuery", {"callback_query_id": call_id})

        if data == "back_home" or data.startswith("sync_now_"):
            sync_json_and_github()
            edit_message(chat_id, message_id, format_status_text(user_id), build_main_menu_kb(user_id, lang))

        elif data == "menu_premium":
            edit_message(chat_id, message_id, tr_str(lang, "prem_menu_title"), build_premium_packages_kb(lang))

        elif data == "menu_stars":
            edit_message(chat_id, message_id, tr_str(lang, "stars_menu_title"), build_stars_packages_kb(lang))

        elif data.startswith("pkg_"):
            pkg_key = data.replace("pkg_", "")
            inv_txt, inv_kb = render_package_invoice(user_id, pkg_key, lang)
            edit_message(chat_id, message_id, inv_txt, inv_kb)

        elif data.startswith("adm_auto_") and user_id == ADMIN_ID:
            parts = data.split("_", 3)
            target_id = int(parts[2])
            pkg_key = parts[3]
            fulfill_package_for_user(target_id, pkg_key, source_label="1-Click Admin")

        elif data == "adm_batch_all" and user_id == ADMIN_ID:
            with db_lock:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT user_id, pkg_key FROM payment_orders WHERE status = 'pending'")
                rows = cur.fetchall()
            count = 0
            for uid, pkey in rows:
                if fulfill_package_for_user(uid, pkey, source_label="Batch-Admin"):
                    count += 1
            send_message(chat_id, f"✅ Navbatdagi *{count} ta* buyurtma birdaniga tasdiqlandi!")

        elif data.startswith("adm_reject_") and user_id == ADMIN_ID:
            target_id = int(data.split("_")[2])
            send_message(target_id, "⚠️ To'lov chekingiz tasdiqlanmadi. Qaytadan tekshirib yuboring.")
            send_message(chat_id, f"❌ `{target_id}` cheki rad etildi.")

        elif data == "lang_menu":
            kb = {
                "inline_keyboard": [
                    [
                        {"text": "🇺🇿 O'zbekcha", "callback_data": "setlang_uz"},
                        {"text": "🇷🇺 Русский", "callback_data": "setlang_ru"},
                        {"text": "🇬🇧 English", "callback_data": "setlang_en"}
                    ],
                    [
                        {"text": "🇹🇷 Türkçe", "callback_data": "setlang_tr"},
                        {"text": "🇸🇦 العربية", "callback_data": "setlang_ar"},
                        {"text": "🇪🇸 Español", "callback_data": "setlang_es"}
                    ],
                    [{"text": tr_str(lang, "btn_back"), "callback_data": "back_home"}]
                ]
            }
            edit_message(chat_id, message_id, "🌐 *Select your interface language (270 Countries):*", kb)

        elif data.startswith("setlang_"):
            new_l = data.split("_")[1]
            with db_lock:
                conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (new_l, user_id))
                conn.commit()
            sync_json_and_github()
            edit_message(chat_id, message_id, format_status_text(user_id), build_main_menu_kb(user_id, new_l))

        elif data == "modules_menu":
            kb = {
                "inline_keyboard": [
                    [{"text": "🛡️ 1. Ghost Vault (" + ("✅" if "GhostVault" in mods or prem else "❌") + ")", "callback_data": "toggle_mod_GhostVault"}],
                    [{"text": "🤖 2. AI Manager (" + ("✅" if "AIManager" in mods or prem else "❌") + ")", "callback_data": "toggle_mod_AIManager"}],
                    [{"text": "🌐 3. Mesh Network (" + ("✅" if "MeshNetwork" in mods or prem else "❌") + ")", "callback_data": "toggle_mod_MeshNetwork"}],
                    [{"text": "💰 4. Media-Paywall (" + ("✅" if "MediaPaywall" in mods or prem else "❌") + ")", "callback_data": "toggle_mod_MediaPaywall"}],
                    [{"text": tr_str(lang, "btn_back"), "callback_data": "back_home"}]
                ]
            }
            edit_message(chat_id, message_id, tr_str(lang, "mod_hub_title"), kb)

        elif data.startswith("toggle_mod_"):
            mod_key = data.replace("toggle_mod_", "")
            with db_lock:
                if mod_key in mods:
                    conn.execute("DELETE FROM modules WHERE user_id = ? AND module_name = ?", (user_id, mod_key))
                else:
                    conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (user_id, mod_key))
                conn.commit()
            sync_json_and_github()
            edit_message(chat_id, message_id, format_status_text(user_id), build_main_menu_kb(user_id, lang))

class APIServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        try:
            uid = int(params.get("user_id", ["0"])[0])
        except ValueError:
            uid = 0

        if parsed.path == "/":
            body = json.dumps({"status": "MessengerUP Auto-Pay Server Active"}).encode("utf-8")
        elif parsed.path == "/status":
            prem, stars, mods, lang, cfg, _ = get_user_full(uid)
            body = json.dumps({"is_premium": prem, "upstars": stars, "lang": lang, "modules": mods, "mod_config": cfg}).encode("utf-8")
        elif parsed.path == "/sms_webhook":
            # Android SMS Forwarder ilovasidan kelgan bank SMS xabarini 1 soniyada avto-tasdiqlash!
            sms_text = params.get("text", [""])[0]
            ok, matched_uid, matched_pkg = match_sms_and_auto_activate(sms_text)
            body = json.dumps({"ok": ok, "user_id": matched_uid, "package": matched_pkg}).encode("utf-8")
        elif parsed.path == "/transfer":
            try:
                from_id = int(params.get("from_id", ["0"])[0])
                to_id = int(params.get("to_id", ["0"])[0])
                amount = int(params.get("amount", ["0"])[0])
            except ValueError:
                from_id, to_id, amount = 0, 0, 0
            ensure_user(from_id)
            ensure_user(to_id)
            _, sender_stars, _, _, _, _ = get_user_full(from_id)
            if amount > 0 and sender_stars >= amount:
                with db_lock:
                    conn.execute("UPDATE users SET upstars = upstars - ? WHERE user_id = ?", (amount, from_id))
                    conn.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, to_id))
                    conn.commit()
                sync_json_and_github()
                _, _, _, to_lang, _, _ = get_user_full(to_id)
                send_message(to_id, tr_str(to_lang, "stars_added_msg").replace("{amount}", str(amount)))
                body = json.dumps({"ok": True, "new_balance": sender_stars - amount}).encode("utf-8")
            else:
                body = json.dumps({"ok": False, "error": "Insufficient balance"}).encode("utf-8")
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
    print(f"✅ MessengerUP Auto-Pay Server {PORT}-portda ishga tushdi!")
    offset = 0
    while True:
        res = tg_request("getUpdates", {"offset": offset, "timeout": 25})
        if res.get("ok"):
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                handle_update(upd)
        else:
            time.sleep(2)
