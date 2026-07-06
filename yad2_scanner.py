"""
סקריפט סריקת יד2 - SUV/קרוסאובר גדול (פורסטר וכד')
שולח התראת וואטסאפ כשמוצאת מודעה חדשה שעומדת בקריטריונים
"""

import sys
import requests
import json
import time
import os
from datetime import datetime

# הגדרה חשובה - מבטיחה שהלוגים מופיעים מיד ב-Render
sys.stdout.reconfigure(line_buffering=True)

# ============================================================
# הגדרות - נקראות מ-Environment Variables ב-Render
# ============================================================

TWILIO_ACCOUNT_SID   = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN    = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
MY_WHATSAPP_NUMBER   = os.environ.get("MY_WHATSAPP_NUMBER")

SCAN_INTERVAL_MINUTES = 10
SEEN_FILE = "seen_ads.json"

# ============================================================
# קריטריונים לחיפוש
# ============================================================

CURRENT_YEAR = datetime.now().year
MAX_KM_BY_YEAR = {
    year: (CURRENT_YEAR - year + 1) * 10000
    for year in range(2019, CURRENT_YEAR + 1)
}

SEARCHES = [
    {"name": "סובארו פורסטר",    "manufacturer": 34, "model": 278},
    {"name": "טויוטה RAV4",       "manufacturer": 39, "model": 302},
    {"name": "קיה ספורטאג",       "manufacturer": 23, "model": 189},
    {"name": "יונדאי טוסון",      "manufacturer": 20, "model": 156},
    {"name": "סקודה קודיאק",      "manufacturer": 35, "model": 931},
    {"name": "מיצובישי אאוטלנדר", "manufacturer": 26, "model": 204},
]

MAX_PRICE = 120000
MIN_YEAR  = 2019
HAND      = 1

# ============================================================
# Headers מלאים שמדמים דפדפן אמיתי
# ============================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.yad2.co.il/vehicles/cars",
    "Origin": "https://www.yad2.co.il",
    "Connection": "keep-alive",
}

# ============================================================
# פונקציות
# ============================================================

def load_seen_ads():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ads(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def send_whatsapp(message):
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=MY_WHATSAPP_NUMBER
        )
        print(f"📱 נשלחה הודעה בהצלחה!")
    except Exception as e:
        print(f"❌ שגיאה בשליחת וואטסאפ: {e}")


def fetch_ads(manufacturer, model, year, max_km):
    # ניסיון ראשון - API חדש
    urls = [
        "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars",
        "https://www.yad2.co.il/api/pre-load/getFeedIndex/vehicles/cars",
    ]
    params = {
        "manufacturer": manufacturer,
        "model": model,
        "year": f"{year}-{year}",
        "km": f"-{max_km}",
        "price": f"-{MAX_PRICE}",
        "hand": HAND,
    }

    session = requests.Session()
    # פתיחת עמוד ראשי קודם כדי לקבל cookies
    try:
        session.get("https://www.yad2.co.il/vehicles/cars", headers=HEADERS, timeout=10)
    except:
        pass

    for url in urls:
        try:
            resp = session.get(url, params=params, headers=HEADERS, timeout=15)
            print(f"   status: {resp.status_code}, size: {len(resp.text)} chars")
            if resp.status_code == 200 and len(resp.text) > 10:
                data = resp.json()
                items = data.get("data", {}).get("feed", {}).get("feed_items", [])
                if items is not None:
                    return items
        except Exception as e:
            print(f"   ⚠️ שגיאה: {e}")
            continue

    return []


def check_km_valid(ad_km, year):
    max_km = MAX_KM_BY_YEAR.get(year, 999999)
    return ad_km <= max_km


def scan_all():
    seen = load_seen_ads()
    new_ads = []

    for search in SEARCHES:
        for year in range(MIN_YEAR, CURRENT_YEAR + 1):
            max_km = MAX_KM_BY_YEAR[year]
            print(f"🔍 בודק {search['name']} שנת {year} (עד {max_km:,} ק\"מ)...")
            ads = fetch_ads(search["manufacturer"], search["model"], year, max_km)

            for ad in ads:
                ad_id = str(ad.get("id", ""))
                if not ad_id or ad_id in seen:
                    continue

                try:
                    ad_km = int(ad.get("kilometers", 0))
                    ad_year = int(ad.get("year", 0))
                except:
                    continue

                if not check_km_valid(ad_km, ad_year):
                    continue

                seen.add(ad_id)
                new_ads.append({
                    "id":    ad_id,
                    "name":  search["name"],
                    "year":  ad_year,
                    "km":    ad_km,
                    "price": ad.get("price", "?"),
                    "city":  ad.get("city", ""),
                    "link":  f"https://www.yad2.co.il/item/{ad_id}",
                })
            time.sleep(2)

    save_seen_ads(seen)
    return new_ads


def format_message(ad):
    try:
        price_str = f"{int(ad['price']):,} ₪"
    except:
        price_str = f"{ad['price']} ₪"
    return (
        f"🚗 מציאה ביד2!\n"
        f"רכב: {ad['name']} {ad['year']}\n"
        f"קילומטראז': {ad['km']:,} ק\"מ\n"
        f"מחיר: {price_str}\n"
        f"עיר: {ad['city']}\n"
        f"🔗 {ad['link']}"
    )


# ============================================================
# לולאה ראשית
# ============================================================

if __name__ == "__main__":
    print("🚀 סורק יד2 מתחיל לעבוד!")
    print(f"⏱ סריקה כל {SCAN_INTERVAL_MINUTES} דקות")
    print(f"📅 שנים: {MIN_YEAR}-{CURRENT_YEAR}")
    print(f"💰 מחיר מקסימלי: {MAX_PRICE:,} ₪")
    print(f"🚙 דגמים: {', '.join(s['name'] for s in SEARCHES)}")

    if not TWILIO_ACCOUNT_SID:
        print("❌ שגיאה: TWILIO_ACCOUNT_SID לא הוגדר!")
    if not TWILIO_AUTH_TOKEN:
        print("❌ שגיאה: TWILIO_AUTH_TOKEN לא הוגדר!")
    if not MY_WHATSAPP_NUMBER:
        print("❌ שגיאה: MY_WHATSAPP_NUMBER לא הוגדר!")
    else:
        print(f"✅ וואטסאפ מוגדר ל: {MY_WHATSAPP_NUMBER}")
        send_whatsapp("✅ סורק יד2 עלה בהצלחה! אחפש לך רכב כל 10 דקות 🚗")

    while True:
        print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - מתחיל סריקה...")
        new_ads = scan_all()

        if new_ads:
            print(f"✅ נמצאו {len(new_ads)} מודעות חדשות!")
            for ad in new_ads:
                msg = format_message(ad)
                send_whatsapp(msg)
                time.sleep(2)
        else:
            print("😴 אין מודעות חדשות")

        print(f"💤 ממתין {SCAN_INTERVAL_MINUTES} דקות לסריקה הבאה...")
        time.sleep(SCAN_INTERVAL_MINUTES * 60)
