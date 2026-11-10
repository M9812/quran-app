"""
نوتیفیکیشن ساعتی آیات قرآن همراه با ترجمه فارسی

نصب نیازمندی‌ها:
    pip install requests plyer
    (روی ویندوز ممکن است pip install plyer win10toast-click هم لازم شود؛ plyer معمولاً کافی است)

اجرا:
    python quran_notifier.py
"""

import json
import os
import random
import time

import requests
from plyer import notification

# ---------------- تنظیمات ----------------
TRANSLATION = "fa.makarem"   # ترجمه مکارم شیرازی | گزینه‌های دیگر: fa.fooladvand ، fa.ayati ، fa.khorramshahi
INTERVAL_SECONDS = 3600      # هر یک ساعت
MODE = "sequential"          # "sequential" = به ترتیب قرآن | "random" = تصادفی
MAX_LEN = 250                # ویندوز طول نوتیفیکیشن را محدود می‌کند
# ------------------------------------------

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "quran_data.json")
STATE_FILE = os.path.join(BASE, "state.json")


def download_quran():
    """یک‌بار کل قرآن (عربی + فارسی) را دانلود و ذخیره می‌کند."""
    print("در حال دانلود قرآن ...")
    ar = requests.get("https://api.alquran.cloud/v1/quran/quran-uthmani", timeout=60).json()["data"]["surahs"]
    fa = requests.get(f"https://api.alquran.cloud/v1/quran/{TRANSLATION}", timeout=60).json()["data"]["surahs"]

    ayahs = []
    for s_ar, s_fa in zip(ar, fa):
        for a_ar, a_fa in zip(s_ar["ayahs"], s_fa["ayahs"]):
            ayahs.append({
                "surah": s_ar["name"],
                "surah_number": s_ar["number"],
                "number": a_ar["numberInSurah"],
                "arabic": a_ar["text"],
                "fa": a_fa["text"],
            })

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(ayahs, f, ensure_ascii=False)
    print(f"{len(ayahs)} آیه ذخیره شد.")
    return ayahs


def load_quran():
    if not os.path.exists(DATA_FILE):
        return download_quran()
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_index():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)["index"]
    except Exception:
        return 0


def save_index(i):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"index": i}, f)


def notify(ayah):
    title = f"سوره {ayah['surah']} - آیه {ayah['number']}"
    message = f"{ayah['arabic']}\n\n{ayah['fa']}"
    if len(message) > MAX_LEN:
        message = message[: MAX_LEN - 1] + "…"
    notification.notify(title=title, message=message, app_name="Quran", timeout=30)


def main():
    ayahs = load_quran()
    total = len(ayahs)
    index = load_index()

    while True:
        if MODE == "random":
            index = random.randrange(total)
        ayah = ayahs[index % total]
        notify(ayah)
        print(f"ارسال شد: {ayah['surah']} {ayah['number']}")

        index = (index + 1) % total
        save_index(index)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
