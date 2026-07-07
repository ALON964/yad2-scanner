"""
סקריפט סריקת יד2 - SUV/קרוסאובר גדול
שולח התראת Telegram כשמוצאת מודעה חדשה
"""

import sys
import json
import time
import os
import requests
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SCAN_INTERVAL_MINUTES = 10
SEEN_FILE = "seen_ads.json"

CURRENT_YEAR = datetime.now().year
MAX_KM_BY_YEAR = {
    year: (CURRENT_YEAR - year + 1) * 10000
    for year in range(2019, CURRENT_YEAR + 1)
}

CAR_MODELS = [
    {"name": "סובארו פורסטר",    "manufacturer": "SUBARU",     "model": "FORESTER"},
    {"name": "טויוטה RAV4",       "manufacturer": "TOYOTA",     "model": "RAV-4"},
    {"name": "קיה ספורטאג",       "manufacturer": "KIA",        "model": "SPORTAGE"},
    {"name": "יונדאי טוסון",      "manufacturer": "HYUNDAI",    "model": "TUCSON"},
    {"name": "סקודה קודיאק",      "manufacturer": "SKODA",      "model": "KODIAQ"},
    {"name": "מיצובישי אאוטלנדר", "manufacturer": "MITSUBISHI", "model": "OUTLANDER"},
]

MAX_PRICE = 120000
MIN_YEAR  = 2019
HAND      = 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8",
    "Referer": "https://www.yad2.co.il/vehicles/cars",
    "Origin": "https://www.yad2.co.il",
}


def load_seen_ads():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ads(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        if resp.status_code == 200:
            print("📱 נשלחה הודעת Telegram בהצלחה!")
        else:
            print(f"❌ שגיאה: {resp.text}")
    except Exception as e:
        print(f"❌ שגיאה: {e}")


def fetch_ads(manufacturer_id, model_id, year):
    """שליפה ישירה מ-API של יד2"""
    max_km = MAX_KM_BY_YEAR.get(year, 999999)
    session = requests.Session()

    # קבלת cookies
    try:
        session.get("https://www.yad2.co.il/vehicles/cars", headers=HEADERS, timeout=10)
        time.sleep(1)
    except:
        pass

    url = "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars"
    params = {
        "manufacturer": manufacturer_id,
        "model": model_id,
        "year": f"{year}-{year}",
        "km": f"-{max_km}",
        "price": f"-{MAX_PRICE}",
        "hand": HAND,
        "page": 1,
    }

    try:
        resp = session.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"   HTTP {resp.status_code}")
            return []

        data = resp.json()
        items = data.get("data", {}).get("feed", {}).get("feed_items", [])
        return [i for i in items if i.get("type") == "ad"]
    except Exception as e:
        print(f"   ⚠️ שגיאה: {e}")
        return []


# מיפוי ID של יצרנים ודגמים ביד2
CAR_IDS = [
    {"name": "סובארו פורסטר",    "manufacturer_id": 34,  "model_id": 278},
    {"name": "טויוטה RAV4",       "manufacturer_id": 39,  "model_id": 302},
    {"name": "קיה ספורטאג",       "manufacturer_id": 23,  "model_id": 189},
    {"name": "יונדאי טוסון",      "manufacturer_id": 20,  "model_id": 156},
    {"name": "סקודה קודיאק",      "manufacturer_id": 35,  "model_id": 931},
    {"name": "מיצובישי אאוטלנדר", "manufacturer_id": 26,  "model_id": 204},
]


def scan_all():
    seen = load_seen_ads()
    new_ads = []

    for car in CAR_IDS:
        for year in range(MIN_YEAR, CURRENT_YEAR + 1):
            print(f"🔍 {car['name']} {year}...")
            ads = fetch_ads(car["manufacturer_id"], car["model_id"], year)
            print(f"   {len(ads)} תוצאות")

            for ad in ads:
                ad_id = str(ad.get("id", ""))
                if not ad_id or ad_id in seen:
                    continue

                try:
                    ad_km    = int(ad.get("kilometers", 0))
                    ad_year  = int(ad.get("year", 0))
                    ad_price = int(str(ad.get("price", "0")).replace(",", "").replace("₪", "").strip() or 0)
                except:
                    continue

                max_km = MAX_KM_BY_YEAR.get(ad_year, 999999)
                if ad_km > max_km:
                    continue

                seen.add(ad_id)
                new_ads.append({
                    "id":    ad_id,
                    "name":  car["name"],
                    "year":  ad_year,
                    "km":    ad_km,
                    "price": ad_price,
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
        f"🚗 <b>מציאה ביד2!</b>\n"
        f"רכב: {ad['name']} {ad['year']}\n"
        f"קילומטראז': {ad['km']:,} ק\"מ\n"
        f"מחיר: {price_str}\n"
        f"עיר: {ad['city']}\n"
        f"🔗 {ad['link']}"
    )


if __name__ == "__main__":
    print("🚀 סורק יד2 מתחיל לעבוד!")
    print(f"⏱ סריקה כל {SCAN_INTERVAL_MINUTES} דקות")
    print(f"📅 שנים: {MIN_YEAR}-{CURRENT_YEAR}")
    print(f"💰 מחיר מקסימלי: {MAX_PRICE:,} ₪")

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ חסרים פרטי Telegram!")
    else:
        print("✅ Telegram מוגדר!")
        send_telegram("✅ סורק יד2 עלה בהצלחה! אחפש לך רכב כל 10 דקות 🚗")

    while True:
        print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - מתחיל סריקה...")
        new_ads = scan_all()

        if new_ads:
            print(f"✅ נמצאו {len(new_ads)} מודעות חדשות!")
            for ad in new_ads:
                send_telegram(format_message(ad))
                time.sleep(2)
        else:
            print("😴 אין מודעות חדשות")

        print(f"💤 ממתין {SCAN_INTERVAL_MINUTES} דקות...")
        time.sleep(SCAN_INTERVAL_MINUTES * 60)
