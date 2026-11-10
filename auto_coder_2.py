import os
import re

PROJECT_DIR = r"C:\Users\User\telegram"
BOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. strings.xml ichida Telegram Premium -> UpPremium va Telegram Stars -> UpStar qilish
strings_path = os.path.join(PROJECT_DIR, r"TMessagesProj\src\main\res\values\strings.xml")
if os.path.exists(strings_path):
    with open(strings_path, "r", encoding="utf-8") as f:
        s_content = f.read()
    s_content = s_content.replace("Telegram Premium", "UpPremium").replace("Telegram Stars", "UpStar")
    with open(strings_path, "w", encoding="utf-8") as f:
        f.write(s_content)
    print("[+] strings.xml yangilandi: barcha nomlar UpPremium va UpStar ga o'zgardi!")

# 2. AndroidManifest.xml ga HTTP serverga ulanish ruxsatini qo'shish
for root, dirs, files in os.walk(PROJECT_DIR):
    for file in files:
        if file == "AndroidManifest.xml":
            m_path = os.path.join(root, file)
            with open(m_path, "r", encoding="utf-8") as f:
                m_content = f.read()
            if "<application" in m_content and "usesCleartextTraffic" not in m_content:
                m_content = m_content.replace("<application", '<application android:usesCleartextTraffic="true"', 1)
                with open(m_path, "w", encoding="utf-8") as f:
                    f.write(m_content)
                print(f"[+] Ruxsat qo'shildi: {m_path}")

# 3. StarsIntroActivity.java va StarsController.java ni UpStar botga ulash
for root, dirs, files in os.walk(os.path.join(PROJECT_DIR, "TMessagesProj")):
    for file in files:
        if file == "StarsIntroActivity.java":
            si_path = os.path.join(root, file)
            with open(si_path, "r", encoding="utf-8") as f:
                si_content = f.read()
            # Stars oynasidagi asosiy xarid tugmasini botga yo'naltirish
            old_click = "buttonView.setOnClickListener("
            if old_click in si_content and "UpManager.openPayBot" not in si_content:
                si_content = re.sub(
                    r'buttonView\.setOnClickListener\([^;]+;\s*\}?\);',
                    'buttonView.setOnClickListener(v -> org.telegram.messenger.UpManager.openPayBot(getContext(), "stars"));',
                    si_content
                )
                with open(si_path, "w", encoding="utf-8") as f:
                    f.write(si_content)
                print("[+] StarsIntroActivity.java UpStar botga ulandi!")

# 4. Shu papkaning o'zida tayyor bot_server.py faylini yaratish
bot_code = '''import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiohttp import web

TOKEN = "9288572880:AAHaa4ea7lKvmSA8A4OMr0OJSMfv6SrZt54"
ADMIN_ID = 1021089367
ADMIN_USERNAME = "@usman_khasan"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect('up_ecosystem.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_premium INTEGER DEFAULT 0,
    upstars INTEGER DEFAULT 0
)
""")
conn.commit()

def ensure_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, is_premium, upstars) VALUES (?, 0, 0)", (user_id,))
        conn.commit()

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    args = message.get_args()
    user_id = message.from_user.id
    ensure_user(user_id)

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🇺🇿 Click / Payme / Karta (O'zbekiston)", callback_data=f"method_uz_{args}"),
        InlineKeyboardButton("🌍 Visa / Mastercard / USDT (Xalqaro)", callback_data=f"method_int_{args}")
    )

    if "premium" in args:
        text = "🌟 **UpPremium obunasini rasmiylashtirish**\\n\\nMaxsus funksiyalarni yoqish uchun to'lov usulini tanlang:"
    elif "stars" in args:
        text = "✨ **UpStar xarid qilish**\\n\\nUpStar balansingizni to'ldirish uchun to'lov usulini tanlang:"
    else:
        cursor.execute("SELECT is_premium, upstars FROM users WHERE user_id = ?", (user_id,))
        prem, stars = cursor.fetchone()
        status_text = "Faol ✅" if prem else "Faol emas ❌"
        text = f"🚀 **Messenger Up Rasmiy To'lov Boti**\\n\\n🆔 Sizning ID: `{user_id}`\\n💎 UpPremium: **{status_text}**\\n✨ Balans: **{stars} UpStar**\\n\\nTo'lov usulini tanlang:"

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('method_'))
async def process_payment_method(call: types.CallbackQuery):
    user_id = call.from_user.id
    if "uz" in call.data:
        msg = (
            f"💳 **Karta orqali to'lov (Uzcard / Humo):**\\n"
            f"`8600 0000 0000 0000` (Khasanov U.)\\n\\n"
            f"🔹 **UpPremium (1 oy):** 35,000 so'm\\n"
            f"🔹 **100 UpStar:** 15,000 so'm\\n\\n"
            f"To'lovdan so'ng chek (skrinshot)ni shu botga yuboring.\\n"
            f"👨‍💻 Yordam: {ADMIN_USERNAME}\\n"
            f"🆔 Sizning ID: `{user_id}`"
        )
    else:
        msg = (
            f"🌍 **Xalqaro to'lov (Visa / Mastercard / USDT):**\\n\\n"
            f"🔹 **UpPremium (1 oy):** $3.00\\n"
            f"🔹 **100 UpStar:** $1.50\\n\\n"
            f"To'lov rekvizitlari uchun chek yuboring yoki adminga yozing: {ADMIN_USERNAME}\\n"
            f"🆔 Sizning ID: `{user_id}`"
        )
    await call.message.edit_text(msg, parse_mode="Markdown")

@dp.message_handler(content_types=['photo', 'document'])
async def forward_receipt(message: types.Message):
    user_id = message.from_user.id
    caption = (
        f"💰 **Yangi to'lov cheki!**\\n"
        f"🆔 ID: `{user_id}`\\n\\n"
        f"Premium berish: `/give_prem {user_id}`\\n"
        f"100 UpStar berish: `/give_stars {user_id} 100`"
    )
    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode="Markdown")
    await message.answer("✅ To'lov cheki adminga yuborildi! Tekshiruvdan so'ng darhol faollashtiriladi.")

@dp.message_handler(commands=['give_prem'])
async def give_prem(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    target_id = int(message.get_args().strip())
    ensure_user(target_id)
    cursor.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    await message.answer(f"✅ {target_id} ga UpPremium yoqildi!")
    await bot.send_message(target_id, "🎉 Tabriklaymiz! Sizga **UpPremium** faollashtirildi. Ilovani qaytadan oching!", parse_mode="Markdown")

@dp.message_handler(commands=['give_stars'])
async def give_stars(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.get_args().split()
    target_id, amount = int(args[0]), int(args[1])
    ensure_user(target_id)
    cursor.execute("UPDATE users SET upstars = upstars + ? WHERE user_id = ?", (amount, target_id))
    conn.commit()
    await message.answer(f"✅ {target_id} ga {amount} UpStar qo'shildi!")
    await bot.send_message(target_id, f"✨ Hisobingizga **{amount} UpStar** qo'shildi! Ilovani yangilang.", parse_mode="Markdown")

async def handle_status(request):
    user_id = int(request.query.get('user_id', 0))
    cursor.execute("SELECT is_premium, upstars FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        return web.json_response({"is_premium": bool(row[0]), "upstars": row[1]})
    return web.json_response({"is_premium": False, "upstars": 0})

async def on_startup(dp):
    app = web.Application()
    app.router.add_get('/status', handle_status)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

if __name__ == '__main__':
    print("✅ Messenger Up Bot va API (8080-port) ishga tushdi! Telegramda @messengeruppremium_bot ga /start bosing.")
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
'''

bot_file_path = os.path.join(BOT_DIR, "bot_server.py")
with open(bot_file_path, "w", encoding="utf-8") as f:
    f.write(bot_code)
print(f"[+] Bot fayli yaratildi: {bot_file_path}")
print("\n✅ 2-BOSQICH HAM XATOSIZ YAKUNLANDI!")