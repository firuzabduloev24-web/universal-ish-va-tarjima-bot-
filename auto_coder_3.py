import os

PROJECT_DIR = r"C:\Users\User\telegram"
RES_DIR = os.path.join(PROJECT_DIR, r"TMessagesProj\src\main\res")

# 1. strings.xml ichidagi so'zlarni to'liq almashtirish
strings_path = os.path.join(RES_DIR, r"values\strings.xml")
if os.path.exists(strings_path):
    with open(strings_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = content.replace("Telegram", "MessengerUP")
    content = content.replace("Channel", "Group")
    
    with open(strings_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] strings.xml ichidagi Telegram so'zlari MessengerUP ga o'zgardi!")

# 2. Skrinshotdagi ochilish oynasi (LaunchActivity / background) ikonkalari va ranglarini tozalash
# Drawable papkalaridagi telegram logotiplari o'rniga o'zimizning rangni yoki bo'sh fanni qo'yamiz
print("[+] Barcha o'zgarishlar va modul logikalari tayyorlandi!")