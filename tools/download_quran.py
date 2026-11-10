"""
یک‌بار اجرا کنید تا کل قرآن (عربی + ترجمه فارسی) در assets/quran.json ذخیره شود.

    pip install requests
    python tools/download_quran.py      (از داخل پوشه پروژه)
"""
import json
import os

import requests

TRANSLATION = "fa.makarem"  # یا fa.fooladvand ، fa.ayati ، fa.khorramshahi

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "quran.json")

print("در حال دانلود ...")
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

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(ayahs, f, ensure_ascii=False)
print(f"{len(ayahs)} آیه در {os.path.normpath(OUT)} ذخیره شد.")
