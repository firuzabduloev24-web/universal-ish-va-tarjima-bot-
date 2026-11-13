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

DEFAULT_MOD_CONFIG = {
    "GhostVault": {"enabled": True, "anti_screenshot": True, "decoy_pin": True, "timer": "30s"},
    "AIManager": {"enabled": True, "auto_reply": True, "live_translate": True, "voice_summary": True},
    "MeshNetwork": {"enabled": True, "p2p_bridge": True, "stealth_dpi": True, "mined_stars": 15},
    "MediaPaywall": {"enabled": True, "default_price": 25, "earned_stars": 0, "sales_count": 0}
}

with db_lock:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        is_premium INTEGER DEFAULT 0,
        upstars INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'en',
        mod_config TEXT DEFAULT '{}'
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        user_id INTEGER,
        module_name TEXT,
        PRIMARY KEY (user_id, module_name)
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
        "ALTER TABLE users ADD COLUMN mod_config TEXT DEFAULT '{}'"
    ]:
        try:
            cursor.execute(col_sql)
        except Exception:
            pass

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, is_premium, upstars, lang, mod_config) VALUES (?, 1, 1000, 'uz', ?)",
        (ADMIN_ID, json.dumps(DEFAULT_MOD_CONFIG))
    )
    cursor.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (ADMIN_ID,))
    for m in ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]:
        cursor.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (ADMIN_ID, m))
    conn.commit()

# ==============================================================================
# 270 TA DAVLAT UCHUN TO'LIQ LUG'AT VA GOOGLE GTX AVTO-TARJIMON
# (Modullarning har bitta tugmasi, ichki yozuvi va bildirishnomalari bilan)
# ==============================================================================
CORE_STRINGS = {
    "en": {
        "title": "🚀 *MessengerUP Global Ecosystem*",
        "your_id": "🆔 Your ID:",
        "vip_status": "💎 UpPremium:",
        "active": "Active ✅ (VIP)",
        "inactive": "Inactive ❌",
        "balance": "✨ UpStar Balance:",
        "active_mods": "🧩 Active Modules:",
        "choose": "Select a section below:",
        "btn_uz_pay": "💳 Local Cards (Uzcard / Humo)",
        "btn_int_pay": "🌍 Global Payment (Visa / Mastercard / USDT)",
        "btn_mods": "🧩 4 Special Modules (Live Control Center)",
        "btn_lang": "🌐 Language",
        "btn_sync": "🔄 Sync with App",
        "btn_back": "⬅️ Back",
        "select_lang": "🌐 *Select your interface language (270 Countries Supported):*",
        "mod_hub_title": "🧩 *4 Special Modules Control Center*\nTap any module below to test its live features and configure settings in your language:",
        "mod_btn_1": "🛡️ 1. Ghost Vault (Stealth Safe & Anti-Spy) ⚙️",
        "mod_btn_2": "🤖 2. AI Manager (24/7 AI Secretary) ⚙️",
        "mod_btn_3": "🌐 3. Mesh Network (Offline P2P & Mining) ⚙️",
        "mod_btn_4": "💰 4. Media-Paywall (Content Monetization) ⚙️",
        "status_label": "Status",
        "ghost_title": "🛡️ *Ghost Vault (Stealth Safe & Anti-Spy)*",
        "ghost_info": "Protects private chats with dual-PIN encryption and blocks unauthorized screenshots or screen recording.",
        "ghost_btn_anti": "📵 Anti-Screenshot & Screen Record",
        "ghost_btn_decoy": "🔐 Decoy PIN (Fake Safe Mode)",
        "ghost_btn_timer": "⏱ Auto-Delete Timer",
        "ai_title": "🤖 *AI Manager (24/7 Personal AI Secretary)*",
        "ai_info": "Automatically replies when you are busy, summarizes voice notes, and translates chats across 270 countries in real time.",
        "ai_btn_reply": "💬 24/7 Smart AI Auto-Reply",
        "ai_btn_tr": "🌍 Live Chat Translator (270 Countries)",
        "ai_btn_voice": "🎙 Voice-to-Text Instant Summary",
        "mesh_title": "🌐 *Mesh Network (Offline P2P & Anti-Block)*",
        "mesh_info": "Transmits messages without internet via nearby Bluetooth/Wi-Fi Direct nodes, bypasses firewalls, and rewards you with UpStars.",
        "mesh_btn_p2p": "📡 Offline P2P Bridge (Bluetooth/Wi-Fi)",
        "mesh_btn_dpi": "⚡ Stealth DPI Anti-Block Proxy",
        "mesh_btn_mine": "⛏ Claim Relay Mining Reward (+5 UpStar ✨)",
        "mesh_mined_label": "Mined Relay Bonus",
        "paywall_title": "💰 *Media-Paywall (Content Monetization)*",
        "paywall_info": "Locks your photos, videos, and files behind a blurred UpStar paywall. You receive 80% of all sales directly to your balance.",
        "paywall_btn_price": "🏷 Default Unlock Price",
        "paywall_btn_demo": "🔗 Generate Paid Media Link",
        "paywall_sales_label": "Total Sales",
        "paywall_earned_label": "Total Earned",
        "paywall_demo_msg": "💰 *Paid Media Link Generated!*\n\n🔒 Unlock Price: *{price} UpStar*\n🔗 Shareable Link: `{link}`\n\n_Share this link in any chat or channel. Users must pay {price} UpStars to unlock your content!_",
        "pay_uz_text": "💳 *Local Card Payment (Uzcard / Humo):*\n\n🔹 *Uzcard:* `5614682112210333`\n🔹 *Humo:* `9860170111318102`\n(Khasanov U.)\n\n• UpPremium (1 month): 35,000 UZS\n• 100 UpStar: 15,000 UZS\n\n📌 Send your payment screenshot here after transfer!\n🆔 Your ID: `{uid}`",
        "pay_int_text": "🌍 *Global Payment (Visa / Mastercard / USDT):*\n\n🔹 *Visa USD:* `4023060246442007`\n🔹 *Visa Local:* `4023060506933828`\n(Khasanov U.)\n\n• UpPremium (1 month): $3.00\n• 100 UpStar: $1.50\n\n📌 Send your payment receipt screenshot right here to activate instantly!\n🆔 Your ID: `{uid}`",
        "receipt_sent": "✅ Your payment receipt has been sent to the administrator! Your VIP / UpStars will be activated shortly.",
        "alert_synced": "✅ Synchronized with app!",
        "alert_updated": "✅ Setting updated!",
        "alert_mined": "🎉 +5 UpStars added to your balance!",
        "alert_link_ready": "🔗 Paid Media Link generated!",
        "vip_activated_msg": "🎉 *Congratulations!* Your *UpPremium (VIP)* and all 4/4 special modules are now active!",
        "stars_added_msg": "✨ *+{amount} UpStars* have been added to your balance!"
    },
    "uz": {
        "title": "🚀 *MessengerUP Global Ekotizimi*",
        "your_id": "🆔 Sizning ID:",
        "vip_status": "💎 UpPremium:",
        "active": "Faol ✅ (VIP)",
        "inactive": "Faol emas ❌",
        "balance": "✨ UpStar Balansi:",
        "active_mods": "🧩 Faol Modullar:",
        "choose": "Kerakli bo'limni tanlang:",
        "btn_uz_pay": "🇺🇿 Uzcard / Humo (O'zbekiston)",
        "btn_int_pay": "🌍 Visa / Mastercard / USDT (Xalqaro)",
        "btn_mods": "🧩 4 ta Maxsus Modul (Boshqaruv va Demo)",
        "btn_lang": "🌐 Til / Language",
        "btn_sync": "🔄 Ilova bilan Sinxronlash",
        "btn_back": "⬅️ Orqaga",
        "select_lang": "🌐 *Interfeys tilini tanlang (270 ta davlat qo'llab-quvvatlanadi):*",
        "mod_hub_title": "🧩 *4 ta Maxsus Modul Boshqaruv Markazi*\nHar bir modulning ustiga bosib, uning jonli funksiyalarini o'z tilingizda boshqaring:",
        "mod_btn_1": "🛡️ 1. Ghost Vault (Maxfiy Seyf va Anti-Josus) ⚙️",
        "mod_btn_2": "🤖 2. AI Manager (24/7 Shaxsiy AI Kotib) ⚙️",
        "mod_btn_3": "🌐 3. Mesh Network (Internetsiz P2P va Mining) ⚙️",
        "mod_btn_4": "💰 4. Media-Paywall (Pullik Kontent Sotish) ⚙️",
        "status_label": "Holat",
        "ghost_title": "🛡️ *Ghost Vault (Maxfiy Seyf va Anti-Josus)*",
        "ghost_info": "Shaxsiy yozishmalarni ikki qavatli yashirin parol bilan himoyalaydi hamda skrinshot va ekran yozib olishni bloklaydi.",
        "ghost_btn_anti": "📵 Anti-Skrinshot va Yozib olishni bloklash",
        "ghost_btn_decoy": "🔐 Yolg'on Parol (Decoy PIN)",
        "ghost_btn_timer": "⏱ Avto-O'chirish Taymeri",
        "ai_title": "🤖 *AI Manager (24/7 Shaxsiy AI Kotib)*",
        "ai_info": "Band paytingizda mijozlarga o'zi javob yozadi, ovozli xabarlarni matnga o'giradi va 270 ta davlat tiliga sinxron tarjima qiladi.",
        "ai_btn_reply": "💬 24/7 Aqlli AI Avto-Javob",
        "ai_btn_tr": "🌍 Jonli Chat Tarjimon (270 Davlat)",
        "ai_btn_voice": "🎙 Ovozli Xabarni Matnga Aylantirish",
        "mesh_title": "🌐 *Mesh Network (Internetsiz P2P va Anti-Blok)*",
        "mesh_info": "Internet yo'qligida Bluetooth/Wi-Fi Direct orqali xabar uzatadi, blokirovkalarni aylanib o'tadi va tarmoq ulashganingiz uchun UpStar beradi.",
        "mesh_btn_p2p": "📡 Offline P2P Ko'prik (Bluetooth/Wi-Fi)",
        "mesh_btn_dpi": "⚡ Stealth DPI Anti-Blokirovka",
        "mesh_btn_mine": "⛏ Relay Bonus Olish (+5 UpStar ✨)",
        "mesh_mined_label": "Yig'ilgan Relay Bonusi",
        "paywall_title": "💰 *Media-Paywall (Kontentni Monetizatsiya Qilish)*",
        "paywall_info": "Rasm, video va fayllarni xiralashtirib (Blur), faqat UpStar to'laganlarga ochib beradi. Tushumning 80% ulushi sizning balansingizga tushadi.",
        "paywall_btn_price": "🏷 Standart Ochish Narxi",
        "paywall_btn_demo": "🔗 Pullik Media Ssilka Yaratish",
        "paywall_sales_label": "Sotuvlar soni",
        "paywall_earned_label": "Jami daromad",
        "paywall_demo_msg": "💰 *Pullik Media Ssilka Tayyor!*\n\n🔒 Ochish narxi: *{price} UpStar*\n🔗 Maxfiy ssilka: `{link}`\n\n_Ushbu ssilkani guruh yoki kanalga tashlang — foydalanuvchilar faylni ko'rish uchun sizga {price} UpStar to'laydi!_",
        "pay_uz_text": "💳 *O'zbekiston kartalari orqali to'lov:*\n\n🔹 *Uzcard:* `5614682112210333`\n🔹 *Humo:* `9860170111318102`\n(Khasanov U.)\n\n• UpPremium (1 oy): 35,000 so'm\n• 100 UpStar: 15,000 so'm\n\n📌 To'lovdan so'ng chekni shu botga yuboring!\n🆔 Sizning ID: `{uid}`",
        "pay_int_text": "🌍 *Xalqaro Visa / Mastercard orqali to'lov:*\n\n🔹 *Visa USD:* `4023060246442007`\n🔹 *Visa SUM:* `4023060506933828`\n(Khasanov U.)\n\n• UpPremium (1 oy): $3.00\n• 100 UpStar: $1.50\n\n📌 To'lovdan so'ng chekni shu botga yuboring!\n🆔 Sizning ID: `{uid}`",
        "receipt_sent": "✅ To'lov cheki adminga yuborildi! Tasdiqlanishi bilan sizga avtomatik VIP / UpStar yoqiladi.",
        "alert_synced": "✅ Ilova bilan sinxronlandi!",
        "alert_updated": "✅ Sozlama yangilandi!",
        "alert_mined": "🎉 +5 UpStar balansingizga qo'shildi!",
        "alert_link_ready": "🔗 Pullik ssilka yaratildi!",
        "vip_activated_msg": "🎉 *Tabriklaymiz!* Sizga *UpPremium (VIP)* va barcha 4/4 maxsus modullar faollashtirildi!",
        "stars_added_msg": "✨ Hisobingizga *+{amount} UpStar* qo'shildi!"
    },
    "ru": {
        "title": "🚀 *Глобальная Экосистема MessengerUP*",
        "your_id": "🆔 Ваш ID:",
        "vip_status": "💎 UpPremium:",
        "active": "Активен ✅ (VIP)",
        "inactive": "Не активен ❌",
        "balance": "✨ Баланс UpStar:",
        "active_mods": "🧩 Активные модули:",
        "choose": "Выберите нужный раздел:",
        "btn_uz_pay": "💳 Карты Uzcard / Humo",
        "btn_int_pay": "🌍 Visa / Mastercard / USDT (Мир)",
        "btn_mods": "🧩 4 Спец-Модуля (Управление и Демо)",
        "btn_lang": "🌐 Язык / Language",
        "btn_sync": "🔄 Синхронизация с приложением",
        "btn_back": "⬅️ Назад",
        "select_lang": "🌐 *Выберите язык интерфейса (Поддержка 270 стран):*",
        "mod_hub_title": "🧩 *Центр Управления 4 Спец-Модулями*\nНажмите на любой модуль ниже, чтобы протестировать его функции и настроить параметры:",
        "mod_btn_1": "🛡️ 1. Ghost Vault (Секретный Сейф и Анти-Шпион) ⚙️",
        "mod_btn_2": "🤖 2. AI Manager (24/7 ИИ-Секретарь) ⚙️",
        "mod_btn_3": "🌐 3. Mesh Network (Оффлайн P2P и Майнинг) ⚙️",
        "mod_btn_4": "💰 4. Media-Paywall (Монетизация Контента) ⚙️",
        "status_label": "Статус",
        "ghost_title": "🛡️ *Ghost Vault (Секретный Сейф и Анти-Шпион)*",
        "ghost_info": "Защищает личные чаты двойным PIN-кодом и блокирует создание скриншотов или запись экрана.",
        "ghost_btn_anti": "📵 Защита от скриншотов и записи",
        "ghost_btn_decoy": "🔐 Ложный пароль (Decoy PIN)",
        "ghost_btn_timer": "⏱ Таймер авто-удаления",
        "ai_title": "🤖 *AI Manager (24/7 Персональный ИИ-Секретарь)*",
        "ai_info": "Автоматически отвечает, когда вы заняты, переводит голосовые в текст и синхронно переводит чаты на языки 270 стран.",
        "ai_btn_reply": "💬 24/7 Умный ИИ-Автоответчик",
        "ai_btn_tr": "🌍 Живой перевод чатов (270 стран)",
        "ai_btn_voice": "🎙 Расшифровка голосовых сообщений",
        "mesh_title": "🌐 *Mesh Network (Оффлайн P2P и Анти-Блок)*",
        "mesh_info": "Передает сообщения без интернета через Bluetooth/Wi-Fi Direct, обходит блокировки и начисляет UpStar за раздачу сети.",
        "mesh_btn_p2p": "📡 Оффлайн P2P Мост (Bluetooth/Wi-Fi)",
        "mesh_btn_dpi": "⚡ Stealth DPI Обход блокировок",
        "mesh_btn_mine": "⛏ Забрать бонус раздачи (+5 UpStar ✨)",
        "mesh_mined_label": "Добытый бонус сети",
        "paywall_title": "💰 *Media-Paywall (Монетизация Контента)*",
        "paywall_info": "Закрывает фото, видео и файлы размытием (Blur) с оплатой в UpStar. Вы получаете 80% от каждой продажи на свой баланс.",
        "paywall_btn_price": "🏷 Цена открытия по умолчанию",
        "paywall_btn_demo": "🔗 Создать платную ссылку",
        "paywall_sales_label": "Продаж",
        "paywall_earned_label": "Заработано",
        "paywall_demo_msg": "💰 *Платная ссылка на медиа готова!*\n\n🔒 Цена открытия: *{price} UpStar*\n🔗 Ссылка: `{link}`\n\n_Отправьте эту ссылку в чат или канал — пользователи заплатят вам {price} UpStar за доступ к файлу!_",
        "pay_uz_text": "💳 *Оплата через карты Uzcard / Humo:*\n\n🔹 *Uzcard:* `5614682112210333`\n🔹 *Humo:* `9860170111318102`\n(Khasanov U.)\n\n• UpPremium (1 мес): 35,000 сум\n• 100 UpStar: 15,000 сум\n\n📌 После оплаты отправьте скриншот чека в этот бот!\n🆔 Ваш ID: `{uid}`",
        "pay_int_text": "🌍 *Международная оплата (Visa / Mastercard / USDT):*\n\n🔹 *Visa USD:* `4023060246442007`\n🔹 *Visa UZS:* `4023060506933828`\n(Khasanov U.)\n\n• UpPremium (1 мес): $3.00\n• 100 UpStar: $1.50\n\n📌 Отправьте скриншот чека сюда для мгновенной активации!\n🆔 Ваш ID: `{uid}`",
        "receipt_sent": "✅ Чек отправлен администратору! После проверки вам автоматически активируется VIP / UpStar.",
        "alert_synced": "✅ Синхронизировано с приложением!",
        "alert_updated": "✅ Настройка обновлена!",
        "alert_mined": "🎉 +5 UpStar добавлено на ваш баланс!",
        "alert_link_ready": "🔗 Платная ссылка создана!",
        "vip_activated_msg": "🎉 *Поздравляем!* Вам активирован *UpPremium (VIP)* и все 4/4 спец-модуля!",
        "stars_added_msg": "✨ На ваш баланс зачислено *+{amount} UpStar*!"
    }
}

def auto_translate_gtx(text, target_lang):
    """Istalgan 270 ta davlat tiliga (tr, ar, es, de, fr, zh, ja, ko, hi, pt, id...) avtomatik tarjima qiladi va SQLite keshda saqlaydi."""
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

# ==============================================================================
# FOYDALANUVCHI BAZASI VA GITHUB CLOUD SYNC
# ==============================================================================
def ensure_user(user_id, detected_lang=None, auto_vip=False):
    lang_code = (detected_lang or "en").lower().split("-")[0][:2]
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT is_premium, lang, mod_config FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        is_vip = 1 if (user_id == ADMIN_ID or auto_vip) else 0
        if not row:
            cur.execute(
                "INSERT INTO users (user_id, is_premium, upstars, lang, mod_config) VALUES (?, ?, 0, ?, ?)",
                (user_id, is_vip, lang_code, json.dumps(DEFAULT_MOD_CONFIG))
            )
            conn.commit()
        else:
            if is_vip == 1 and row[0] == 0:
                cur.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
            if detected_lang and not row[1]:
                cur.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang_code, user_id))
            conn.commit()

def get_user_full(user_id):
    with db_lock:
        cur = conn.cursor()
        cur.execute("SELECT module_name FROM modules WHERE user_id = ?", (user_id,))
        mods = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT is_premium, upstars, lang, mod_config FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        prem = bool(row[0]) if row else False
        stars = row[1] if row else 0
        lang = (row[2] if row and row[2] else "en")
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

        return prem, stars, mods, lang, cfg

def save_mod_config(user_id, cfg):
    with db_lock:
        conn.execute("UPDATE users SET mod_config = ? WHERE user_id = ?", (json.dumps(cfg), user_id))
        conn.commit()
    sync_json_and_github()

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
                try:
                    parsed_cfg = json.loads(mcfg) if mcfg else DEFAULT_MOD_CONFIG
                except Exception:
                    parsed_cfg = DEFAULT_MOD_CONFIG
                data[str(uid)] = {
                    "is_premium": bool(prem) or (len(mods) >= 4) or (uid == ADMIN_ID),
                    "upstars": stars,
                    "lang": lang or "en",
                    "modules": mods,
                    "mod_config": parsed_cfg
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

# ==============================================================================
# MENYULAR VA 4 TA MODUL INTERAKTIV VITRINASI (100% HAR QANDAY DAVLAT TILIDA)
# ==============================================================================
def build_main_menu_kb(target_uid, lang):
    return {
        "inline_keyboard": [
            [{"text": tr_str(lang, "btn_mods"), "callback_data": "modules_menu"}],
            [{"text": tr_str(lang, "btn_int_pay"), "callback_data": f"pay_visa_{target_uid}"}],
            [{"text": tr_str(lang, "btn_uz_pay"), "callback_data": f"pay_uz_{target_uid}"}],
            [
                {"text": tr_str(lang, "btn_lang"), "callback_data": "lang_menu"},
                {"text": tr_str(lang, "btn_sync"), "callback_data": f"sync_now_{target_uid}"}
            ]
        ]
    }

def format_status_text(target_uid):
    prem, stars, mods, lang, _ = get_user_full(target_uid)
    st = tr_str(lang, "active") if prem else tr_str(lang, "inactive")
    return (
        f"{tr_str(lang, 'title')}\n\n"
        f"{tr_str(lang, 'your_id')} `{target_uid}`\n"
        f"{tr_str(lang, 'vip_status')} *{st}*\n"
        f"{tr_str(lang, 'balance')} *{stars}*\n"
        f"{tr_str(lang, 'active_mods')} *{len(mods)}/4* (`GhostVault`, `AIManager`, `Mesh`, `Paywall`)\n\n"
        f"{tr_str(lang, 'choose')}"
    )

def render_module_showcase(user_id, mod_key):
    prem, stars, mods, lang, cfg = get_user_full(user_id)
    is_on = (mod_key in mods) or prem
    st_word = tr_str(lang, "active") if is_on else tr_str(lang, "inactive")
    st_icon = "✅ ON" if is_on else "❌ OFF"
    m_cfg = cfg.get(mod_key, {})

    lbl_status = tr_str(lang, "status_label")

    if mod_key == "GhostVault":
        lbl_anti = tr_str(lang, "ghost_btn_anti")
        lbl_decoy = tr_str(lang, "ghost_btn_decoy")
        lbl_timer = tr_str(lang, "ghost_btn_timer")
        anti_st = "✅ ON" if m_cfg.get("anti_screenshot", True) else "❌ OFF"
        decoy_st = "✅ ON" if m_cfg.get("decoy_pin", True) else "❌ OFF"
        tmr = m_cfg.get("timer", "30s")

        text = (
            f"{tr_str(lang, 'ghost_title')}\n\n"
            f"• *{lbl_status}:* {st_word}\n"
            f"• *{lbl_anti}:* `{anti_st}`\n"
            f"• *{lbl_decoy}:* `{decoy_st}`\n"
            f"• *{lbl_timer}:* `{tmr}`\n\n"
            f"_{tr_str(lang, 'ghost_info')}_"
        )
        kb = {
            "inline_keyboard": [
                [{"text": f"🛡️ Ghost Vault: {st_icon}", "callback_data": "toggle_mod_GhostVault"}],
                [{"text": f"{lbl_anti}: {anti_st}", "callback_data": "cfg_GhostVault_anti"}],
                [{"text": f"{lbl_decoy}: {decoy_st}", "callback_data": "cfg_GhostVault_decoy"}],
                [{"text": f"{lbl_timer}: {tmr} (5s / 30s / 1m)", "callback_data": "cfg_GhostVault_timer"}],
                [{"text": tr_str(lang, "btn_back"), "callback_data": "modules_menu"}]
            ]
        }
    elif mod_key == "AIManager":
        lbl_reply = tr_str(lang, "ai_btn_reply")
        lbl_tr = tr_str(lang, "ai_btn_tr")
        lbl_voice = tr_str(lang, "ai_btn_voice")
        rep_st = "✅ ON" if m_cfg.get("auto_reply", True) else "❌ OFF"
        tr_st = "✅ ON" if m_cfg.get("live_translate", True) else "❌ OFF"
        vc_st = "✅ ON" if m_cfg.get("voice_summary", True) else "❌ OFF"

        text = (
            f"{tr_str(lang, 'ai_title')}\n\n"
            f"• *{lbl_status}:* {st_word}\n"
            f"• *{lbl_reply}:* `{rep_st}`\n"
            f"• *{lbl_tr}:* `{tr_st}`\n"
            f"• *{lbl_voice}:* `{vc_st}`\n\n"
            f"_{tr_str(lang, 'ai_info')}_"
        )
        kb = {
            "inline_keyboard": [
                [{"text": f"🤖 AI Manager: {st_icon}", "callback_data": "toggle_mod_AIManager"}],
                [{"text": f"{lbl_reply}: {rep_st}", "callback_data": "cfg_AIManager_reply"}],
                [{"text": f"{lbl_tr}: {tr_st}", "callback_data": "cfg_AIManager_tr"}],
                [{"text": f"{lbl_voice}: {vc_st}", "callback_data": "cfg_AIManager_voice"}],
                [{"text": tr_str(lang, "btn_back"), "callback_data": "modules_menu"}]
            ]
        }
    elif mod_key == "MeshNetwork":
        lbl_p2p = tr_str(lang, "mesh_btn_p2p")
        lbl_dpi = tr_str(lang, "mesh_btn_dpi")
        lbl_mine = tr_str(lang, "mesh_btn_mine")
        lbl_mined = tr_str(lang, "mesh_mined_label")
        p2p_st = "✅ ON" if m_cfg.get("p2p_bridge", True) else "❌ OFF"
        dpi_st = "✅ ON" if m_cfg.get("stealth_dpi", True) else "❌ OFF"
        mined_val = m_cfg.get("mined_stars", 15)

        text = (
            f"{tr_str(lang, 'mesh_title')}\n\n"
            f"• *{lbl_status}:* {st_word}\n"
            f"• *{lbl_p2p}:* `{p2p_st}`\n"
            f"• *{lbl_dpi}:* `{dpi_st}`\n"
            f"• *{lbl_mined}:* `{mined_val} UpStar ✨`\n\n"
            f"_{tr_str(lang, 'mesh_info')}_"
        )
        kb = {
            "inline_keyboard": [
                [{"text": f"🌐 Mesh Network: {st_icon}", "callback_data": "toggle_mod_MeshNetwork"}],
                [{"text": f"{lbl_p2p}: {p2p_st}", "callback_data": "cfg_MeshNetwork_p2p"}],
                [{"text": f"{lbl_dpi}: {dpi_st}", "callback_data": "cfg_MeshNetwork_dpi"}],
                [{"text": lbl_mine, "callback_data": "cfg_MeshNetwork_mine"}],
                [{"text": tr_str(lang, "btn_back"), "callback_data": "modules_menu"}]
            ]
        }
    else:  # MediaPaywall
        lbl_price = tr_str(lang, "paywall_btn_price")
        lbl_demo = tr_str(lang, "paywall_btn_demo")
        lbl_sales = tr_str(lang, "paywall_sales_label")
        lbl_earned = tr_str(lang, "paywall_earned_label")
        price_val = m_cfg.get("default_price", 25)
        sales_val = m_cfg.get("sales_count", 0)
        earned_val = m_cfg.get("earned_stars", 0)

        text = (
            f"{tr_str(lang, 'paywall_title')}\n\n"
            f"• *{lbl_status}:* {st_word}\n"
            f"• *{lbl_price}:* `{price_val} UpStar ✨`\n"
            f"• *{lbl_sales}:* `{sales_val}` | *{lbl_earned}:* `{earned_val} UpStar`\n\n"
            f"_{tr_str(lang, 'paywall_info')}_"
        )
        kb = {
            "inline_keyboard": [
                [{"text": f"💰 Media-Paywall: {st_icon}", "callback_data": "toggle_mod_MediaPaywall"}],
                [{"text": f"{lbl_price}: {price_val} UpStar (10 / 25 / 50 / 100)", "callback_data": "cfg_MediaPaywall_price"}],
                [{"text": lbl_demo, "callback_data": "cfg_MediaPaywall_demo"}],
                [{"text": tr_str(lang, "btn_back"), "callback_data": "modules_menu"}]
            ]
        }
    return text, kb

def handle_update(update):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = msg.get("from", {})
        user_id = user.get("id", chat_id)
        text = msg.get("text", "")

        tg_lang = user.get("language_code", "en")
        tg_is_prem = bool(user.get("is_premium", False))
        ensure_user(user_id, detected_lang=tg_lang, auto_vip=tg_is_prem)

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
            if args.startswith("pay_"):
                for token_part in args.split("_"):
                    if token_part.isdigit() and len(token_part) >= 5:
                        target_uid = int(token_part)

            ensure_user(target_uid, detected_lang=chosen_lang, auto_vip=app_vip)
            _, _, _, lang, _ = get_user_full(target_uid)
            sync_json_and_github()
            send_message(chat_id, format_status_text(target_uid), build_main_menu_kb(target_uid, lang))

        elif "photo" in msg or "document" in msg:
            _, _, _, lang, _ = get_user_full(user_id)
            username = f"@{user.get('username')}" if user.get("username") else "N/A"
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            caption = (
                f"💰 *New Payment Receipt!*\n"
                f"🆔 ID: `{user_id}` | 🌐 Lang: `{lang.upper()}`\n"
                f"👤 {full_name} ({username})"
            )
            admin_kb = {
                "inline_keyboard": [
                    [{"text": "💎 Activate UpPremium (VIP)", "callback_data": f"adm_prem_{user_id}"}],
                    [
                        {"text": "✨ +100 UpStar", "callback_data": f"adm_star_{user_id}_100"},
                        {"text": "✨ +500 UpStar", "callback_data": f"adm_star_{user_id}_500"}
                    ]
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

        prem, stars, mods, lang, cfg = get_user_full(user_id)

        if data.startswith("sync_now_"):
            tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": tr_str(lang, "alert_synced")})
            sync_json_and_github()
            edit_message(chat_id, message_id, format_status_text(user_id), build_main_menu_kb(user_id, lang))

        elif data == "lang_menu":
            tg_request("answerCallbackQuery", {"callback_query_id": call_id})
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
                    [
                        {"text": "🇩🇪 Deutsch", "callback_data": "setlang_de"},
                        {"text": "🇫🇷 Français", "callback_data": "setlang_fr"},
                        {"text": "🇵🇹 Português", "callback_data": "setlang_pt"}
                    ],
                    [
                        {"text": "🇮🇳 हिन्दी", "callback_data": "setlang_hi"},
                        {"text": "🇮🇩 Indonesia", "callback_data": "setlang_id"},
                        {"text": "🇨🇳 中文", "callback_data": "setlang_zh"}
                    ],
                    [
                        {"text": "🇯🇵 日本語", "callback_data": "setlang_ja"},
                        {"text": "🇰🇷 한국어", "callback_data": "setlang_ko"},
                        {"text": "🇮🇹 Italiano", "callback_data": "setlang_it"}
                    ],
                    [{"text": tr_str(lang, "btn_back"), "callback_data": f"sync_now_{user_id}"}]
                ]
            }
            edit_message(chat_id, message_id, tr_str(lang, "select_lang"), kb)

        elif data.startswith("setlang_"):
            new_l = data.split("_")[1]
            with db_lock:
                conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (new_l, user_id))
                conn.commit()
            sync_json_and_github()
            tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": f"🌐 {new_l.upper()}"})
            edit_message(chat_id, message_id, format_status_text(user_id), build_main_menu_kb(user_id, new_l))

        elif data == "modules_menu":
            tg_request("answerCallbackQuery", {"callback_query_id": call_id})
            kb = {
                "inline_keyboard": [
                    [{"text": tr_str(lang, "mod_btn_1"), "callback_data": "open_mod_GhostVault"}],
                    [{"text": tr_str(lang, "mod_btn_2"), "callback_data": "open_mod_AIManager"}],
                    [{"text": tr_str(lang, "mod_btn_3"), "callback_data": "open_mod_MeshNetwork"}],
                    [{"text": tr_str(lang, "mod_btn_4"), "callback_data": "open_mod_MediaPaywall"}],
                    [{"text": tr_str(lang, "btn_back"), "callback_data": f"sync_now_{user_id}"}]
                ]
            }
            edit_message(chat_id, message_id, tr_str(lang, "mod_hub_title"), kb)

        elif data.startswith("open_mod_"):
            mod_key = data.replace("open_mod_", "")
            tg_request("answerCallbackQuery", {"callback_query_id": call_id})
            txt, kb = render_module_showcase(user_id, mod_key)
            edit_message(chat_id, message_id, txt, kb)

        elif data.startswith("toggle_mod_"):
            mod_key = data.replace("toggle_mod_", "")
            with db_lock:
                if mod_key in mods:
                    conn.execute("DELETE FROM modules WHERE user_id = ? AND module_name = ?", (user_id, mod_key))
                else:
                    conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (user_id, mod_key))
                conn.commit()
            sync_json_and_github()
            tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": tr_str(lang, "alert_updated")})
            txt, kb = render_module_showcase(user_id, mod_key)
            edit_message(chat_id, message_id, txt, kb)

        elif data.startswith("cfg_"):
            _, mod_key, param = data.split("_")
            m_cfg = cfg.get(mod_key, {})
            alert_txt = tr_str(lang, "alert_updated")

            if mod_key == "GhostVault":
                if param == "anti":
                    m_cfg["anti_screenshot"] = not m_cfg.get("anti_screenshot", True)
                elif param == "decoy":
                    m_cfg["decoy_pin"] = not m_cfg.get("decoy_pin", True)
                elif param == "timer":
                    timers = ["5s", "30s", "1m", "5m"]
                    cur_t = m_cfg.get("timer", "30s")
                    m_cfg["timer"] = timers[(timers.index(cur_t) + 1) % len(timers)] if cur_t in timers else "30s"
            elif mod_key == "AIManager":
                if param == "reply":
                    m_cfg["auto_reply"] = not m_cfg.get("auto_reply", True)
                elif param == "tr":
                    m_cfg["live_translate"] = not m_cfg.get("live_translate", True)
                elif param == "voice":
                    m_cfg["voice_summary"] = not m_cfg.get("voice_summary", True)
            elif mod_key == "MeshNetwork":
                if param == "p2p":
                    m_cfg["p2p_bridge"] = not m_cfg.get("p2p_bridge", True)
                elif param == "dpi":
                    m_cfg["stealth_dpi"] = not m_cfg.get("stealth_dpi", True)
                elif param == "mine":
                    m_cfg["mined_stars"] = m_cfg.get("mined_stars", 15) + 5
                    with db_lock:
                        conn.execute("UPDATE users SET upstars = upstars + 5 WHERE user_id = ?", (user_id,))
                        conn.commit()
                    alert_txt = tr_str(lang, "alert_mined")
            elif mod_key == "MediaPaywall":
                if param == "price":
                    prices = [10, 25, 50, 100]
                    cur_p = m_cfg.get("default_price", 25)
                    m_cfg["default_price"] = prices[(prices.index(cur_p) + 1) % len(prices)] if cur_p in prices else 25
                elif param == "demo":
                    price = m_cfg.get("default_price", 25)
                    demo_link = f"https://t.me/messengeruppremium_bot?start=unlock_{user_id}_{price}_lang_{lang}"
                    msg_demo = tr_str(lang, "paywall_demo_msg").replace("{price}", str(price)).replace("{link}", demo_link)
                    send_message(chat_id, msg_demo)
                    alert_txt = tr_str(lang, "alert_link_ready")

            cfg[mod_key] = m_cfg
            save_mod_config(user_id, cfg)
            tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": alert_txt})
            txt, kb = render_module_showcase(user_id, mod_key)
            edit_message(chat_id, message_id, txt, kb)

        elif data.startswith("pay_uz"):
            tg_request("answerCallbackQuery", {"callback_query_id": call_id})
            msg_text = tr_str(lang, "pay_uz_text").replace("{uid}", str(user_id))
            kb = {"inline_keyboard": [[{"text": tr_str(lang, "btn_back"), "callback_data": f"sync_now_{user_id}"}]]}
            edit_message(chat_id, message_id, msg_text, kb)

        elif data.startswith("pay_visa"):
            tg_request("answerCallbackQuery", {"callback_query_id": call_id})
            msg_text = tr_str(lang, "pay_int_text").replace("{uid}", str(user_id))
            kb = {"inline_keyboard": [[{"text": tr_str(lang, "btn_back"), "callback_data": f"sync_now_{user_id}"}]]}
            edit_message(chat_id, message_id, msg_text, kb)

        elif data.startswith("adm_prem_") and user_id == ADMIN_ID:
            target_id = int(data.split("_")[2])
            ensure_user(target_id, auto_vip=True)
            with db_lock:
                for m in ["GhostVault", "AIManager", "MeshNetwork", "MediaPaywall"]:
                    conn.execute("INSERT OR IGNORE INTO modules (user_id, module_name) VALUES (?, ?)", (target_id, m))
                conn.commit()
            sync_json_and_github()
            _, _, _, target_lang, _ = get_user_full(target_id)
            tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": "✅ VIP Activated!"})
            send_message(chat_id, f"✅ `{target_id}` -> UpPremium (VIP) Activated!")
            send_message(target_id, tr_str(target_lang, "vip_activated_msg"))

        elif data.startswith("adm_star_") and user_id == ADMIN_ID:
            parts = data.split("_")
            target_id, amount = int(parts[2]), int(parts[3])
            ensure_user(target_id)
            with db_lock:
                conn.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, target_id))
                conn.commit()
            sync_json_and_github()
            _, _, _, target_lang, _ = get_user_full(target_id)
            tg_request("answerCallbackQuery", {"callback_query_id": call_id, "text": f"+{amount} UpStars!"})
            send_message(chat_id, f"✅ `{target_id}` -> +{amount} UpStar!")
            send_message(target_id, tr_str(target_lang, "stars_added_msg").replace("{amount}", str(amount)))

class APIServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        try:
            uid = int(params.get("user_id", ["0"])[0])
        except ValueError:
            uid = 0

        if parsed.path == "/":
            body = json.dumps({"status": "MessengerUP Global 24/7 Server Active", "countries": 270}).encode("utf-8")
        elif parsed.path == "/status":
            prem, stars, mods, lang, cfg = get_user_full(uid)
            body = json.dumps({
                "is_premium": prem,
                "upstars": stars,
                "lang": lang,
                "modules": mods,
                "mod_config": cfg
            }).encode("utf-8")
        elif parsed.path == "/transfer":
            try:
                from_id = int(params.get("from_id", ["0"])[0])
                to_id = int(params.get("to_id", ["0"])[0])
                amount = int(params.get("amount", ["0"])[0])
            except ValueError:
                from_id, to_id, amount = 0, 0, 0
            ensure_user(from_id)
            ensure_user(to_id)
            _, sender_stars, _, _, _ = get_user_full(from_id)
            if amount > 0 and sender_stars >= amount:
                with db_lock:
                    conn.execute("UPDATE users SET upstars = upstars - ? WHERE user_id = ?", (amount, from_id))
                    conn.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, to_id))
                    conn.commit()
                sync_json_and_github()
                _, _, _, to_lang, _ = get_user_full(to_id)
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
    print(f"✅ MessengerUP Global Server (270 Countries) {PORT}-portda ishga tushdi!")
    offset = 0
    while True:
        res = tg_request("getUpdates", {"offset": offset, "timeout": 25})
        if res.get("ok"):
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                handle_update(upd)
        else:
            time.sleep(2)
