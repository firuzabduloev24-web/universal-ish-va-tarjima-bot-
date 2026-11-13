import os

PROJECT_DIR = r"C:\Users\User\telegram"
UP_MANAGER_PATH = os.path.join(
    PROJECT_DIR, r"TMessagesProj\src\main\java\org\telegram\messenger\UpManager.java"
)

up_manager_code = """package org.telegram.messenger;

import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.text.InputType;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Toast;
import org.json.JSONArray;
import org.json.JSONObject;
import org.telegram.messenger.browser.Browser;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class UpManager {
    public static final String BOT_USERNAME = "messengeruppremium_bot";
    public static String SERVER_IP = "http://87.192.242.81:8080";
    public static final String GITHUB_SYNC_URL = "https://raw.githubusercontent.com/firuzabduloev24-web/universal-ish-va-tarjima-bot-/main/users_status.json";

    public static boolean isUpPremium = true;
    public static int upStarsBalance = 1000;
    public static Set<String> activeModules = new HashSet<>();
    public static Map<Long, Boolean> vipUsersCache = new ConcurrentHashMap<>();
    public static Map<String, String> i18nCache = new ConcurrentHashMap<>();

    public static String getAppLang() {
        try {
            String lc = LocaleController.getInstance().getCurrentLocaleInfo().getLangCode();
            if (lc != null && lc.length() >= 2) return lc.split("_")[0].split("-")[0].toLowerCase();
        } catch (Exception ignored) {}
        return Locale.getDefault().getLanguage().toLowerCase();
    }

    // 270 ta davlat tili uchun avtomatik keshli tarjimon (UZ, RU, EN + Google GTX 270 Countries)
    public static String tr(String uz, String ru, String en) {
        String l = getAppLang();
        if (l.equals("uz")) return uz;
        if (l.equals("ru") || l.equals("be") || l.equals("kk") || l.equals("ky") || l.equals("tg")) return ru;
        if (l.equals("en")) return en;

        String cacheKey = l + ":" + en;
        if (i18nCache.containsKey(cacheKey)) {
            return i18nCache.get(cacheKey);
        }

        try {
            SharedPreferences prefs = ApplicationLoader.applicationContext.getSharedPreferences("up_i18n", Context.MODE_PRIVATE);
            String saved = prefs.getString(cacheKey, null);
            if (saved != null) {
                i18nCache.put(cacheKey, saved);
                return saved;
            }
        } catch (Exception ignored) {}

        // Orqa fonda foydalanuvchining interfeys tiliga avtomatik tarjima qilib keshga saqlaydi
        new Thread(() -> {
            try {
                String q = URLEncoder.encode(en, "UTF-8");
                URL url = new URL("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=" + l + "&dt=t&q=" + q);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestProperty("User-Agent", "Mozilla/5.0");
                conn.setConnectTimeout(4000);
                BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = in.readLine()) != null) sb.append(line);
                in.close();

                JSONArray outer = new JSONArray(sb.toString()).getJSONArray(0);
                StringBuilder trBuilder = new StringBuilder();
                for (int i = 0; i < outer.length(); i++) {
                    JSONArray seg = outer.getJSONArray(i);
                    if (!seg.isNull(0)) trBuilder.append(seg.getString(0));
                }
                String result = trBuilder.toString();
                if (!result.isEmpty()) {
                    i18nCache.put(cacheKey, result);
                    SharedPreferences prefs = ApplicationLoader.applicationContext.getSharedPreferences("up_i18n", Context.MODE_PRIVATE);
                    prefs.edit().putString(cacheKey, result).apply();
                }
            } catch (Exception ignored) {}
        }).start();

        return en;
    }

    public static void preloadInterfaceLanguage() {
        String l = getAppLang();
        if (l.equals("uz") || l.equals("ru") || l.equals("en")) return;
        // Ilova ochilishi bilan foydalanuvchi tiliga barcha modul nomlarini oldindan tayyorlab qo'yadi
        tr("", "", "Active ✅");
        tr("", "", "💎 Manage UpPremium / UpStar (Bot)");
        tr("", "", "🎁 Transfer UP Stars");
        tr("", "", "🛡️ 1. Ghost Vault (Stealth Safe & Anti-Spy)");
        tr("", "", "🤖 2. AI Manager (24/7 AI & Live Translator)");
        tr("", "", "🌐 3. Mesh Network (Offline P2P & Mining)");
        tr("", "", "💰 4. Media-Paywall (Paid Content)");
        tr("", "", "Configure in Bot ⚙️");
        tr("", "", "Close");
    }

    public static void openPayBot(Context context, String type) {
        if (context == null) return;
        preloadInterfaceLanguage();
        long userId = UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId();
        String lang = getAppLang();
        boolean hasVip = isUpPremium || (UserConfig.getInstance(UserConfig.selectedAccount).getCurrentUser() != null && UserConfig.getInstance(UserConfig.selectedAccount).getCurrentUser().premium);
        String url = "https://t.me/" + BOT_USERNAME + "?start=pay_" + type + "_" + userId + (hasVip ? "_vip1" : "_vip0") + "_lang_" + lang;

        String stOn = tr("Faol ✅", "Активен ✅", "Active ✅");
        String[] items = {
            tr("💎 UpPremium / UpStar Boshqaruvi (Bot)", "💎 Управление UpPremium / UpStar (Бот)", "💎 Manage UpPremium / UpStar (Bot)"),
            tr("🎁 Do'stga UP Stars o'tkazish", "🎁 Перевести UP Stars другу", "🎁 Transfer UP Stars") + " (" + upStarsBalance + " ✨)",
            tr("🛡️ 1. Ghost Vault (Maxfiy Seyf & Anti-Josus)", "🛡️ 1. Ghost Vault (Секретный Сейф)", "🛡️ 1. Ghost Vault (Stealth Safe & Anti-Spy)") + " [" + stOn + "]",
            tr("🤖 2. AI Manager (24/7 AI & Tarjimon)", "🤖 2. AI Manager (24/7 ИИ & Переводчик)", "🤖 2. AI Manager (24/7 AI & Live Translator)") + " [" + stOn + "]",
            tr("🌐 3. Mesh Network (Offline P2P & Mining)", "🌐 3. Mesh Network (Оффлайн P2P & Майнинг)", "🌐 3. Mesh Network (Offline P2P & Mining)") + " [" + stOn + "]",
            tr("💰 4. Media-Paywall (Pullik Kontent)", "💰 4. Media-Paywall (Платный Контент)", "💰 4. Media-Paywall (Paid Content)") + " [" + stOn + "]"
        };

        new AlertDialog.Builder(context)
            .setTitle("🚀 MessengerUP (" + upStarsBalance + " UpStar ✨)")
            .setItems(items, (dialog, which) -> {
                if (which == 0) {
                    Browser.openUrl(context, url);
                } else if (which == 1) {
                    showTransferDialog(context, 0);
                } else if (which == 2) {
                    showModuleDetailDialog(context, "GhostVault", url);
                } else if (which == 3) {
                    showModuleDetailDialog(context, "AIManager", url);
                } else if (which == 4) {
                    showModuleDetailDialog(context, "MeshNetwork", url);
                } else if (which == 5) {
                    showModuleDetailDialog(context, "MediaPaywall", url);
                }
            })
            .setPositiveButton(tr("Botда Sozlash ⚙️", "Настроить в Боте ⚙️", "Configure in Bot ⚙️"), (d, w) -> Browser.openUrl(context, url))
            .setNegativeButton(tr("Yopish", "Закрыть", "Close"), null)
            .show();
    }

    public static void showModuleDetailDialog(Context context, String modKey, String botUrl) {
        String title = "";
        String msg = "";
        if (modKey.equals("GhostVault")) {
            title = tr("🛡️ Ghost Vault (Maxfiy Seyf)", "🛡️ Ghost Vault (Секретный Сейф)", "🛡️ Ghost Vault (Stealth Safe & Anti-Spy)");
            msg = tr(
                "• Anti-Skrinshot va ekran yozuvini bloklash: Faol ✅\\n• Decoy PIN (Yolg'on parol): Faol ✅\\n• Avto-o'chirish taymeri: 30s",
                "• Блокировка скриншотов и записи экрана: Активна ✅\\n• Ложный пароль (Decoy PIN): Активен ✅\\n• Таймер авто-удаления: 30с",
                "• Anti-Screenshot & Screen Recording: Active ✅\\n• Decoy PIN (Fake Safe Mode): Active ✅\\n• Self-Destruct Timer: 30s"
            );
        } else if (modKey.equals("AIManager")) {
            title = tr("🤖 AI Manager (24/7 AI Kotib)", "🤖 AI Manager (24/7 ИИ-Секретарь)", "🤖 AI Manager (24/7 Personal AI Secretary)");
            msg = tr(
                "• 24/7 Aqlli AI Avto-Javob: Faol ✅\\n• 270 davlat tiliga sinxron chat tarjimoni: Faol ✅\\n• Ovozli xabarni matnga o'girish: Faol ✅",
                "• 24/7 Умный ИИ-Автоответчик: Активен ✅\\n• Живой перевод чатов (270 стран): Активен ✅\\n• Расшифровка голосовых в текст: Активна ✅",
                "• 24/7 Smart AI Auto-Reply: Active ✅\\n• Live Chat Translator (270 Countries): Active ✅\\n• Voice-to-Text Instant Summary: Active ✅"
            );
        } else if (modKey.equals("MeshNetwork")) {
            title = tr("🌐 Mesh Network (Offline P2P)", "🌐 Mesh Network (Оффлайн P2P)", "🌐 Mesh Network (Offline P2P & Anti-Block)");
            msg = tr(
                "• Bluetooth / Wi-Fi Direct internetsiz aloqa: Faol ✅\\n• Stealth DPI Anti-Blokirovka: Faol ✅\\n• Relay Mining bonus: +15 UpStar ✨",
                "• Оффлайн связь Bluetooth / Wi-Fi Direct: Активна ✅\\n• Обход блокировок Stealth DPI: Активен ✅\\n• Бонус за раздачу сети: +15 UpStar ✨",
                "• Offline Bluetooth / Wi-Fi Direct Bridge: Active ✅\\n• Stealth DPI Firewall Bypass: Active ✅\\n• Relay Mining Reward: +15 UpStar ✨"
            );
        } else {
            title = tr("💰 Media-Paywall (Monetizatsiya)", "💰 Media-Paywall (Монетизация)", "💰 Media-Paywall (Content Monetization)");
            msg = tr(
                "• Rasm va videolarni UpStar evaziga sotish: Faol ✅\\n• Standart ochish narxi: 25 UpStar\\n• Muallif ulushi: 80%",
                "• Продажа фото и видео за UpStar: Активна ✅\\n• Цена открытия по умолчанию: 25 UpStar\\n• Доля автора: 80%",
                "• Sell photos & videos for UpStars: Active ✅\\n• Default unlock price: 25 UpStar\\n• Creator revenue share: 80%"
            );
        }

        new AlertDialog.Builder(context)
            .setTitle(title)
            .setMessage(msg)
            .setPositiveButton(tr("Botda Sozlash ⚙️", "Настроить в Боте ⚙️", "Configure in Bot ⚙️"), (d, w) -> Browser.openUrl(context, botUrl))
            .setNegativeButton(tr("Orqaga", "Назад", "Back"), (d, w) -> openPayBot(context, "modules"))
            .show();
    }

    public static void showTransferDialog(Context context, long defaultTargetId) {
        if (context == null) return;
        LinearLayout layout = new LinearLayout(context);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(50, 30, 50, 10);

        EditText idInput = new EditText(context);
        idInput.setHint(tr("Qabul qiluvchi ID raqami", "ID получателя", "Recipient Telegram ID"));
        idInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        if (defaultTargetId > 0) idInput.setText(String.valueOf(defaultTargetId));
        layout.addView(idInput);

        EditText amountInput = new EditText(context);
        amountInput.setHint(tr("Miqdor (Masalan: 100)", "Количество (Например: 100)", "Amount (e.g. 100)"));
        amountInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        layout.addView(amountInput);

        new AlertDialog.Builder(context)
            .setTitle(tr("🎁 UP Stars o'tkazish", "🎁 Перевод UP Stars", "🎁 Transfer UP Stars"))
            .setView(layout)
            .setPositiveButton(tr("Jo'natish", "Отправить", "Send"), (d, w) -> {
                try {
                    long toId = Long.parseLong(idInput.getText().toString().trim());
                    int amount = Integer.parseInt(amountInput.getText().toString().trim());
                    transferStars(context, toId, amount);
                } catch (Exception e) {
                    Toast.makeText(context, "Invalid ID / Amount", Toast.LENGTH_SHORT).show();
                }
            })
            .setNegativeButton(tr("Bekor qilish", "Отмена", "Cancel"), null)
            .show();
    }

    public static void transferStars(Context context, long toId, int amount) {
        long fromId = UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId();
        new Thread(() -> {
            try {
                URL url = new URL(SERVER_IP + "/transfer?from_id=" + fromId + "&to_id=" + toId + "&amount=" + amount);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(5000);
                BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder resp = new StringBuilder();
                String line;
                while ((line = in.readLine()) != null) resp.append(line);
                in.close();
                JSONObject json = new JSONObject(resp.toString());
                if (json.optBoolean("ok", false)) {
                    upStarsBalance = json.optInt("new_balance", upStarsBalance - amount);
                    AndroidUtilities.runOnUIThread(() -> Toast.makeText(context, "✅ +" + amount + " UP Stars!", Toast.LENGTH_LONG).show());
                }
            } catch (Exception ignored) {}
        }).start();
    }

    public static boolean isUserUpVip(long userId) {
        if (userId == UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId()) return isUpPremium;
        return Boolean.TRUE.equals(vipUsersCache.getOrDefault(userId, false));
    }

    public static void checkUserStatus() {
        preloadInterfaceLanguage();
        long userId = UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId();
        if (userId == 0) return;

        new Thread(() -> {
            try {
                URL url = new URL(GITHUB_SYNC_URL);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(5000);
                BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = in.readLine()) != null) response.append(line);
                in.close();

                JSONObject allUsers = new JSONObject(response.toString());
                JSONObject u = allUsers.optJSONObject(String.valueOf(userId));
                if (u != null) {
                    isUpPremium = u.optBoolean("is_premium", true);
                    upStarsBalance = u.optInt("upstars", 1000);
                }
            } catch (Exception ignored) {}
        }).start();
    }
}
"""

with open(UP_MANAGER_PATH, "w", encoding="utf-8") as f:
    f.write(up_manager_code)

print("✅ UpManager.java 270 ta davlat interfeys tiliga avto-moslashadigan qilib yangilandi!")
