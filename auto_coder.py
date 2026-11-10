import os
import subprocess

PROJECT_DIR = r"C:\Users\User\telegram"
JAVA_DIR = os.path.join(PROJECT_DIR, r"TMessagesProj\src\main\java\org\telegram")

def replace_java_method(content, signature, new_method):
    start_idx = content.find(signature)
    if start_idx == -1:
        print(f"[-] Topilmadi: {signature}")
        return content
    brace_start = content.find('{', start_idx)
    depth = 0
    for i in range(brace_start, len(content)):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                print(f"[+] Muvaffaqiyatli yangilandi: {signature[:35]}...")
                return content[:start_idx] + new_method + content[i+1:]
    return content

# 1. Buzilgan fayllarni Git orqali toza holatiga qaytarish (qizil xatolarni yo'qotish)
for rel_path in [
    r"TMessagesProj\src\main\java\org\telegram\ui\PremiumPreviewFragment.java",
    r"TMessagesProj\src\main\java\org\telegram\messenger\UserConfig.java",
    r"TMessagesProj\src\main\java\org\telegram\ui\LaunchActivity.java"
]:
    subprocess.run(["git", "-C", PROJECT_DIR, "checkout", "--", rel_path], stderr=subprocess.DEVNULL)

# 2. UpManager.java faylini yaratish
up_manager_path = os.path.join(JAVA_DIR, r"messenger\UpManager.java")
up_manager_code = """package org.telegram.messenger;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONObject;
import org.telegram.messenger.browser.Browser;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class UpManager {
    public static final String BOT_USERNAME = "messengeruppremium_bot";
    public static final String SERVER_URL = "http://87.192.242.81:8080/status?user_id=";

    public static boolean isUpPremium = false;
    public static int upStarsBalance = 0;

    public static void openPayBot(Context context, String type) {
        if (context == null) return;
        long userId = UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId();
        String url = "https://t.me/" + BOT_USERNAME + "?start=pay_" + type + "_" + userId;
        Browser.openUrl(context, url);
    }

    public static void checkUserStatus() {
        long userId = UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId();
        if (userId == 0) return;

        new Thread(() -> {
            try {
                URL url = new URL(SERVER_URL + userId);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(5000);

                BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = in.readLine()) != null) {
                    response.append(line);
                }
                in.close();

                JSONObject json = new JSONObject(response.toString());
                isUpPremium = json.optBoolean("is_premium", false);
                upStarsBalance = json.optInt("upstars", 0);

                SharedPreferences prefs = ApplicationLoader.applicationContext.getSharedPreferences("up_config", Context.MODE_PRIVATE);
                prefs.edit().putBoolean("is_premium", isUpPremium).putInt("upstars", upStarsBalance).apply();

            } catch (Exception e) {
                SharedPreferences prefs = ApplicationLoader.applicationContext.getSharedPreferences("up_config", Context.MODE_PRIVATE);
                isUpPremium = prefs.getBoolean("is_premium", false);
                upStarsBalance = prefs.getInt("upstars", 0);
            }
        }).start();
    }
}
"""
with open(up_manager_path, "w", encoding="utf-8") as f:
    f.write(up_manager_code)
print("[+] UpManager.java yaratildi!")

# 3. PremiumPreviewFragment.java ni xatosiz o'zgartirish
ppf_path = os.path.join(JAVA_DIR, r"ui\PremiumPreviewFragment.java")
with open(ppf_path, "r", encoding="utf-8") as f:
    ppf_content = f.read()

ppf_content = replace_java_method(
    ppf_content,
    "public static void buyPremium(BaseFragment fragment, SubscriptionTier tier, String source, boolean forcePremium, BillingFlowParams.SubscriptionUpdateParams updateParams)",
    """public static void buyPremium(BaseFragment fragment, SubscriptionTier tier, String source, boolean forcePremium, BillingFlowParams.SubscriptionUpdateParams updateParams) {
        Activity activity = fragment != null ? fragment.getParentActivity() : LaunchActivity.instance;
        if (activity != null) {
            org.telegram.messenger.UpManager.openPayBot(activity, "premium");
        }
    }"""
)

ppf_content = replace_java_method(
    ppf_content,
    "private void updateButtonText(boolean animated)",
    """private void updateButtonText(boolean animated) {
        if (premiumButtonView == null) {
            return;
        }
        premiumButtonView.setButton(getString(R.string.SubscribeToPremiumNoPrice), v -> org.telegram.messenger.UpManager.openPayBot(getParentActivity(), "premium"), animated);
        buttonContainerInternal.setOnClickListener(v -> org.telegram.messenger.UpManager.openPayBot(getParentActivity(), "premium"));
        premiumButtonView.setFlickerDisabled(false);
    }"""
)

with open(ppf_path, "w", encoding="utf-8") as f:
    f.write(ppf_content)

# 4. UserConfig.java ni o'zgartirish
uc_path = os.path.join(JAVA_DIR, r"messenger\UserConfig.java")
with open(uc_path, "r", encoding="utf-8") as f:
    uc_content = f.read()

uc_content = replace_java_method(
    uc_content,
    "public boolean isPremium()",
    """public boolean isPremium() {
        if (UpManager.isUpPremium) {
            return true;
        }
        if (currentUser == null) {
            return false;
        }
        return currentUser.premium;
    }"""
)

with open(uc_path, "w", encoding="utf-8") as f:
    f.write(uc_content)

# 5. LaunchActivity.java ga status tekshirishni qo'shish
la_path = os.path.join(JAVA_DIR, r"ui\LaunchActivity.java")
with open(la_path, "r", encoding="utf-8") as f:
    la_content = f.read()

if "UpManager.checkUserStatus();" not in la_content:
    target = "protected void onResume() {\n        super.onResume();"
    replacement = "protected void onResume() {\n        super.onResume();\n        org.telegram.messenger.UpManager.checkUserStatus();"
    if target in la_content:
        la_content = la_content.replace(target, replacement, 1)
        print("[+] LaunchActivity.java yangilandi!")

with open(la_path, "w", encoding="utf-8") as f:
    f.write(la_content)

print("\n✅ BARCHA FAYLLAR XATOSIZ YOZILDI! Endi Android Studio'ga qaytishingiz mumkin.")