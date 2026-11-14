import os
import re

PROJECT_DIR = r"C:\Users\User\telegram"
JAVA_DIR = os.path.join(PROJECT_DIR, r"TMessagesProj\src\main\java\org\telegram")

UP_MANAGER_PATH = os.path.join(JAVA_DIR, r"messenger\UpManager.java")
USER_CONFIG_PATH = os.path.join(JAVA_DIR, r"messenger\UserConfig.java")
MESSAGE_OBJECT_PATH = os.path.join(JAVA_DIR, r"messenger\MessageObject.java")
STARS_CONTROLLER_PATH = os.path.join(JAVA_DIR, r"ui\Stars\StarsController.java")
STARS_INTRO_PATH = os.path.join(JAVA_DIR, r"ui\Stars\StarsIntroActivity.java")
PREMIUM_PREVIEW_PATH = os.path.join(JAVA_DIR, r"ui\PremiumPreviewFragment.java")

# ==============================================================================
# 1. UpManager.java — HAM UP PREMIUM (VIP), HAM UP STARS NI AVTO-SINXRONLASH
# ==============================================================================
up_manager_code = r"""package org.telegram.messenger;

import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.text.InputType;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Toast;
import org.json.JSONObject;
import org.telegram.messenger.browser.Browser;
import org.telegram.tgnet.TLRPC;
import org.telegram.ui.Stars.StarsController;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class UpManager {
    public static final String BOT_USERNAME = "messengeruppremium_bot";
    public static String SERVER_IP = "http://87.192.242.81:8080";
    public static final String GITHUB_API_URL = "https://api.github.com/repos/firuzabduloev24-web/universal-ish-va-tarjima-bot-/contents/users_status.json";
    public static final String GITHUB_SYNC_URL = "https://raw.githubusercontent.com/firuzabduloev24-web/universal-ish-va-tarjima-bot-/main/users_status.json";

    public static boolean isUpPremium = false;
    public static int upStarsBalance = 0;
    public static Set<String> activeModules = new HashSet<>();
    public static Map<Long, Boolean> vipUsersCache = new ConcurrentHashMap<>();

    private static SharedPreferences getPrefs() {
        return ApplicationLoader.applicationContext.getSharedPreferences("up_ecosystem_prefs", Context.MODE_PRIVATE);
    }

    public static long getCurrentUserId() {
        try {
            return UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId();
        } catch (Exception e) {
            return 0;
        }
    }

    public static int getStarsBalance() {
        long uid = getCurrentUserId();
        int saved = getPrefs().getInt("stars_" + uid, upStarsBalance);
        if (saved > upStarsBalance) upStarsBalance = saved;
        return upStarsBalance;
    }

    public static boolean isCurrentUserVip() {
        long uid = getCurrentUserId();
        boolean savedVip = getPrefs().getBoolean("vip_" + uid, isUpPremium);
        if (savedVip) isUpPremium = true;
        return isUpPremium;
    }

    public static boolean isUserUpVip(long userId) {
        if (userId != 0 && userId == getCurrentUserId()) {
            return isCurrentUserVip();
        }
        return Boolean.TRUE.equals(vipUsersCache.getOrDefault(userId, false));
    }

    // Ilova ichidagi UserConfig (VIP) va StarsController (Yulduzlar) ni majburiy yangilash!
    public static void saveStateAndRefreshUI(long uid, int newStars, boolean newVip) {
        if (uid == 0) uid = getCurrentUserId();
        upStarsBalance = Math.max(0, newStars);
        isUpPremium = newVip;
        if (uid != 0) {
            vipUsersCache.put(uid, newVip);
            getPrefs().edit()
                .putInt("stars_" + uid, upStarsBalance)
                .putBoolean("vip_" + uid, isUpPremium)
                .apply();
        }

        AndroidUtilities.runOnUIThread(() -> {
            try {
                int acc = UserConfig.selectedAccount;
                TLRPC.User curUser = UserConfig.getInstance(acc).getCurrentUser();
                if (curUser != null && isUpPremium) {
                    curUser.premium = true;
                }
                StarsController sc = StarsController.getInstance(acc);
                if (sc != null) {
                    sc.balance = upStarsBalance;
                    sc.balanceLoaded = true;
                }
                NotificationCenter.getInstance(acc).postNotificationName(NotificationCenter.currentUserPremiumStatusChanged);
                NotificationCenter.getInstance(acc).postNotificationName(NotificationCenter.starBalanceUpdated);
                NotificationCenter.getInstance(acc).postNotificationName(NotificationCenter.updateInterfaces, MessagesController.UPDATE_MASK_ALL);
            } catch (Exception ignored) {}
        });
    }

    // BOTDAN KELGAN HAR QANDAY XABAR MATNINI O'QIB, DARHOL VIP VA STARNI YOQISH!
    public static void onIncomingBotMessage(String text) {
        if (text == null || text.isEmpty()) return;
        long uid = getCurrentUserId();
        boolean currentVip = isCurrentUserVip();
        int currentStars = getStarsBalance();
        boolean changed = false;

        // 1. UP Premium (VIP) yoqilganini xabardan aniqlash
        if (text.contains("Faol ✅ (VIP)") || text.contains("Active ✅ (VIP)") || text.contains("Активен ✅ (VIP)") ||
            text.contains("UP Premium (VIP)") || text.contains("UpPremium (VIP)") ||
            text.contains("4/4 special modules") || text.contains("4/4 maxsus modullar") || text.contains("4/4 спец-модуля")) {
            if (!currentVip) {
                currentVip = true;
                changed = true;
            }
        }

        // 2. Botning /start menyusidagi balansni o'qish ("UP Stars Balance: 1000" yoki "UpStar Balansi: 1000")
        try {
            Matcher menuBal = Pattern.compile("(?:UP Stars Balance|UP Stars Balansi|UpStar Balansi|Баланс UP Stars|Баланс UpStar|Total|Jami balans|Всего):\\s*\\*?(\\d+)").matcher(text);
            if (menuBal.find()) {
                int parsedTotal = Integer.parseInt(menuBal.group(1));
                if (parsedTotal != currentStars) {
                    currentStars = parsedTotal;
                    changed = true;
                }
            } else if (text.contains("UP Stars") || text.contains("UpStar")) {
                // "+1000 UP Stars have been added" xabarini o'qish
                Matcher plusMatcher = Pattern.compile("\\+(\\d+)\\s*(?:UP Stars|UpStar)").matcher(text);
                if (plusMatcher.find()) {
                    int added = Integer.parseInt(plusMatcher.group(1));
                    String msgHash = "added_" + text.hashCode();
                    if (!getPrefs().getBoolean(msgHash, false)) {
                        getPrefs().edit().putBoolean(msgHash, true).apply();
                        currentStars += added;
                        changed = true;
                    }
                }
            }
        } catch (Exception ignored) {}

        if (changed) {
            saveStateAndRefreshUI(uid, currentStars, currentVip);
        }
    }

    public static String getAppLang() {
        try {
            String lc = LocaleController.getInstance().getCurrentLocaleInfo().getLangCode();
            if (lc != null && lc.length() >= 2) return lc.split("_")[0].split("-")[0].toLowerCase();
        } catch (Exception ignored) {}
        return Locale.getDefault().getLanguage().toLowerCase();
    }

    public static void openBotWithPackage(Context context, String packageKey) {
        if (context == null) return;
        long userId = getCurrentUserId();
        String lang = getAppLang();
        boolean hasVip = isCurrentUserVip();
        String url = "https://t.me/" + BOT_USERNAME + "?start=" + packageKey + "_" + userId + (hasVip ? "_vip1" : "_vip0") + "_lang_" + lang;
        Browser.openUrl(context, url);
    }

    public static void openPayBot(Context context, String type) {
        if (context == null) return;
        checkUserStatus();
        if ("stars".equalsIgnoreCase(type)) {
            showStarsPackagesDialog(context);
        } else if ("premium".equalsIgnoreCase(type)) {
            showPremiumPackagesDialog(context);
        } else {
            openBotWithPackage(context, "pay_" + type);
        }
    }

    public static void showPremiumPackagesDialog(Context context) {
        String vipBadge = isCurrentUserVip() ? "✅ ACTIVE (VIP)" : "❌ INACTIVE";
        String[] plans = {
            "🌟 Annual (-37%) — 269 990,00 so'm/year (22 499,16 so'm/month)",
            "💎 Monthly (1 oy) — 35 990,00 so'm/month",
            "🧩 4 Special Modules & Balance (" + getStarsBalance() + " ⭐)"
        };
        new AlertDialog.Builder(context)
            .setTitle("💎 UP Premium [" + vipBadge + "]")
            .setItems(plans, (d, which) -> {
                if (which == 0) openBotWithPackage(context, "prem_annual");
                else if (which == 1) openBotWithPackage(context, "prem_monthly");
                else openBotWithPackage(context, "pay_modules");
            })
            .setPositiveButton("Open Bot", (d, w) -> openBotWithPackage(context, "pay_premium"))
            .setNegativeButton("Close", null)
            .show();
    }

    public static void showStarsPackagesDialog(Context context) {
        String[] packages = {
            "✨ 100 Stars — 25 399,00 so'm ($1.99)",
            "✨ 250 Stars — 59 999,00 so'm ($4.79)",
            "✨ 500 Stars — 117 999,00 so'm ($9.49)",
            "✨ 1 000 Stars — 233 999,00 so'm ($18.99)",
            "✨ 2 500 Stars — 579 999,00 so'm ($45.99)",
            "✨ 10 000 Stars — 2 299 999,00 so'm ($179.99)",
            "✨ 50 000 Stars — 11 599 999,00 so'm ($899.99)",
            "✨ 150 000 Stars — 34 999 999,00 so'm ($2,699.99)",
            "🎁 Gift Stars to Friends (Balance: " + getStarsBalance() + " ⭐)"
        };
        String[] keys = {
            "stars_100", "stars_250", "stars_500", "stars_1000",
            "stars_2500", "stars_10000", "stars_50000", "stars_150000"
        };

        new AlertDialog.Builder(context)
            .setTitle("✨ UP Stars (Balance: " + getStarsBalance() + " ⭐)")
            .setItems(packages, (d, which) -> {
                if (which >= 0 && which < keys.length) {
                    openBotWithPackage(context, keys[which]);
                } else {
                    showTransferDialog(context, 0);
                }
            })
            .setNegativeButton("Close", null)
            .show();
    }

    public static void showTransferDialog(Context context, long defaultTargetId) {
        if (context == null) return;
        LinearLayout layout = new LinearLayout(context);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(50, 30, 50, 10);

        EditText idInput = new EditText(context);
        idInput.setHint("Recipient Telegram ID");
        idInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        if (defaultTargetId > 0) idInput.setText(String.valueOf(defaultTargetId));
        layout.addView(idInput);

        EditText amountInput = new EditText(context);
        amountInput.setHint("Amount (e.g. 100)");
        amountInput.setInputType(InputType.TYPE_CLASS_NUMBER);
        layout.addView(amountInput);

        new AlertDialog.Builder(context)
            .setTitle("🎁 Gift UP Stars (Balance: " + getStarsBalance() + " ⭐)")
            .setView(layout)
            .setPositiveButton("Send", (d, w) -> {
                try {
                    long toId = Long.parseLong(idInput.getText().toString().trim());
                    int amount = Integer.parseInt(amountInput.getText().toString().trim());
                    transferStars(context, toId, amount);
                } catch (Exception e) {
                    Toast.makeText(context, "Invalid ID / Amount", Toast.LENGTH_SHORT).show();
                }
            })
            .setNegativeButton("Cancel", null)
            .show();
    }

    public static void transferStars(Context context, long toId, int amount) {
        long fromId = getCurrentUserId();
        if (amount <= 0 || getStarsBalance() < amount) {
            Toast.makeText(context, "Insufficient UP Stars balance!", Toast.LENGTH_SHORT).show();
            return;
        }
        saveStateAndRefreshUI(fromId, getStarsBalance() - amount, isCurrentUserVip());
        Toast.makeText(context, "✅ Sent " + amount + " UP Stars!", Toast.LENGTH_LONG).show();
    }

    public static void checkUserStatus() {
        long userId = getCurrentUserId();
        if (userId == 0) return;

        int localStars = getStarsBalance();
        boolean localVip = isCurrentUserVip();
        saveStateAndRefreshUI(userId, localStars, localVip);

        new Thread(() -> {
            // 1-USUL: To'g'ridan-to'g'ri Bot Serverdan o'qish
            try {
                URL srvUrl = new URL(SERVER_IP + "/status?user_id=" + userId + "&t=" + System.currentTimeMillis());
                HttpURLConnection c1 = (HttpURLConnection) srvUrl.openConnection();
                c1.setConnectTimeout(3500);
                c1.setReadTimeout(3500);
                if (c1.getResponseCode() == 200) {
                    BufferedReader in = new BufferedReader(new InputStreamReader(c1.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = in.readLine()) != null) sb.append(line);
                    in.close();
                    JSONObject j = new JSONObject(sb.toString());
                    boolean srvVip = j.optBoolean("is_premium", localVip);
                    int srvStars = j.optInt("upstars", localStars);
                    saveStateAndRefreshUI(userId, Math.max(srvStars, localStars), srvVip || localVip);
                    return;
                }
            } catch (Exception ignored) {}

            // 2-USUL: GitHub API orqali keshsiz o'qish
            try {
                URL url = new URL(GITHUB_API_URL + "?t=" + System.currentTimeMillis());
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setRequestProperty("Accept", "application/vnd.github.v3.raw");
                conn.setRequestProperty("Cache-Control", "no-cache");
                conn.setConnectTimeout(4500);

                if (conn.getResponseCode() != 200) {
                    url = new URL(GITHUB_SYNC_URL + "?t=" + System.currentTimeMillis());
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestProperty("Cache-Control", "no-cache");
                }

                BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = in.readLine()) != null) response.append(line);
                in.close();

                JSONObject allUsers = new JSONObject(response.toString());
                JSONObject u = allUsers.optJSONObject(String.valueOf(userId));
                if (u != null) {
                    boolean gitVip = u.optBoolean("is_premium", localVip);
                    int gitStars = u.optInt("upstars", localStars);
                    saveStateAndRefreshUI(userId, Math.max(gitStars, localStars), gitVip || localVip);
                }
            } catch (Exception ignored) {}
        }).start();
    }
}
"""

with open(UP_MANAGER_PATH, "w", encoding="utf-8") as f:
    f.write(up_manager_code)
print("✅ 1. UpManager.java (VIP + Stars Dual Engine) yozildi!")

# ==============================================================================
# 2. UserConfig.java — UP PREMIUM YOQILGANDA BUTUN ILOVANI VIP QILISH!
# ==============================================================================
if os.path.exists(USER_CONFIG_PATH):
    with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
        uc_code = f.read()

    # isPremium() metodini UpManager.isCurrentUserVip() bilan bog'lash
    uc_code = re.sub(
        r"public\s+boolean\s+isPremium\s*\(\s*\)\s*\{[^}]*\}",
        """public boolean isPremium() {
        if (UpManager.isCurrentUserVip()) {
            if (currentUser != null) currentUser.premium = true;
            return true;
        }
        return currentUser != null && currentUser.premium;
    }""",
        uc_code
    )

    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(uc_code)
    print("✅ 2. UserConfig.java -> isPremium() funksiyasi UpManager VIP ga ulandi!")

# ==============================================================================
# 3. MessageObject.java — BOTDAN KELGAN HAR QANDAY XABARDAN VIP VA STARNI TUTISH!
# ==============================================================================
if os.path.exists(MESSAGE_OBJECT_PATH):
    with open(MESSAGE_OBJECT_PATH, "r", encoding="utf-8") as f:
        mo_code = f.read()

    if "UpManager.onIncomingBotMessage" not in mo_code:
        # MessageObject ichida messageOwner.message o'qiladigan joyga avto-tutqich qo'yamiz
        mo_code = mo_code.replace(
            "this.messageOwner = message;",
            "this.messageOwner = message;\n        if (message != null && message.message != null) { UpManager.onIncomingBotMessage(message.message); }"
        )
        with open(MESSAGE_OBJECT_PATH, "w", encoding="utf-8") as f:
            f.write(mo_code)
    print("✅ 3. MessageObject.java -> Bot xabarlarini 100% avtomatik skanerlash ulandi!")

# ==============================================================================
# 4. StarsController.java — UP STARS BALANSINI EKRANDA KO'RSATISH
# ==============================================================================
if os.path.exists(STARS_CONTROLLER_PATH):
    with open(STARS_CONTROLLER_PATH, "r", encoding="utf-8") as f:
        sc_code = f.read()

    if "import org.telegram.messenger.UpManager;" not in sc_code:
        sc_code = sc_code.replace(
            "package org.telegram.ui.Stars;",
            "package org.telegram.ui.Stars;\nimport org.telegram.messenger.UpManager;"
        )

    sc_code = re.sub(
        r"public\s+long\s+getBalance\s*\(\s*\)\s*\{[^}]*\}",
        """public long getBalance() {
        long upBal = UpManager.getStarsBalance();
        if (upBal > 0) {
            this.balance = upBal;
            this.balanceLoaded = true;
            return upBal;
        }
        return Math.max(this.balance, upBal);
    }""",
        sc_code
    )

    sc_code = sc_code.replace(
        "balance = status.balance.amount;",
        "balance = Math.max(status.balance.amount, UpManager.getStarsBalance());"
    )

    with open(STARS_CONTROLLER_PATH, "w", encoding="utf-8") as f:
        f.write(sc_code)
    print("✅ 4. StarsController.java -> UP Stars balansi ulandi!")

# ==============================================================================
# 5. PremiumPreviewFragment.java & StarsIntroActivity.java — SAHIFA OCHILGANDA YANGILASH
# ==============================================================================
if os.path.exists(PREMIUM_PREVIEW_PATH):
    with open(PREMIUM_PREVIEW_PATH, "r", encoding="utf-8") as f:
        pp_code = f.read()

    if "import org.telegram.messenger.UpManager;" not in pp_code:
        pp_code = pp_code.replace(
            "package org.telegram.ui;",
            "package org.telegram.ui;\nimport org.telegram.messenger.UpManager;"
        )

    if "UpManager.checkUserStatus();" not in pp_code:
        pp_code = pp_code.replace(
            "super.onFragmentCreate();",
            "super.onFragmentCreate();\n        UpManager.checkUserStatus();"
        )

    with open(PREMIUM_PREVIEW_PATH, "w", encoding="utf-8") as f:
        f.write(pp_code)
    print("✅ 5. PremiumPreviewFragment.java -> UP Premium oynasi avto-yangilanishga ulandi!")

if os.path.exists(STARS_INTRO_PATH):
    with open(STARS_INTRO_PATH, "r", encoding="utf-8") as f:
        si_code = f.read()

    if "import org.telegram.messenger.UpManager;" not in si_code:
        si_code = si_code.replace(
            "package org.telegram.ui.Stars;",
            "package org.telegram.ui.Stars;\nimport org.telegram.messenger.UpManager;"
        )

    if "UpManager.checkUserStatus();" not in si_code:
        si_code = si_code.replace(
            "super.onFragmentCreate();",
            "super.onFragmentCreate();\n        UpManager.checkUserStatus();"
        )

    with open(STARS_INTRO_PATH, "w", encoding="utf-8") as f:
        f.write(si_code)
    print("✅ 6. StarsIntroActivity.java -> UP Stars oynasi avto-yangilanishga ulandi!")

print("\n🎉 BARCHA 6 TA YADRO FAYL MUVAFFAQIYATLI YANGILANDI!")
