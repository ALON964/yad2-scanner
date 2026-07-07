"""
סקריפט סריקת יד2 - SUV/קרוסאובר גדול (פורסטר וכד')
שולח התראת וואטסאפ כשמוצאת מודעה חדשה שעומדת בקריטריונים
משתמש בחבילת yad2-scraper שמטפלת בחסימות אוטומטית
"""

import sys
import json
import time
import os
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

TWILIO_ACCOUNT_SID   = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN    = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
MY_WHATSAPP_NUMBER   = os.environ.get("MY_WHATSAPP_NUMBER")

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


def fetch_ads_for_model(car):
    try:
        from yad2_scraper.vehicles import fetch_vehicle_category, VehiclesQueryFilters, OrderVehiclesBy

        filters = VehiclesQueryFilters(
            price_range=(0, MAX_PRICE),
            year_range=(MIN_YEAR, CURRENT_YEAR),
            order_by=OrderVehiclesBy.DATE,
        )

        category = fetch_vehicle_category("cars", **filters.__dict__)
        items = []

        for page_data in category.load_next_data().get_data():
            try:
                manufacturer = str(page_data.manufacturer(None) or "").upper()
                model = str(page_data.model(None) or "").upper()

                if car["manufacturer"] not in manufacturer and car["model"] not in model:
                    continue

                ad_id    = str(page_data.id or "")
                ad_km    = int(page_data.km or 0)
                ad_year  = int(page_data.year or 0)
                ad_price = int(page_data.price or 0)
                ad_hand  = int(page_data.hand or 0)

                if ad_hand != HAND:
                    continue

                max_km = MAX_KM_BY_YEAR.get(ad_year, 999999)
                if ad_km > max_km:
                    continue

                items.append({
                    "id":    ad_id,
                    "name":  car["name"],
                    "year":  ad_year,
                    "km":    ad_km,
                    "price": ad_price,
                    "city":  str(page_data.city or ""),
                    "link":  f"https://www.yad2.co.il/item/{ad_id}",
                })
            except Exception:
                continue

        return items

    except Exception as e:
        print(f"   ⚠️ שגיאה בשליפת {car['name']}: {e}")
        return []


def scan_all():
    seen = load_seen_ads()
    new_ads = []

    for car in CAR_MODELS:
        print(f"🔍 סורק {car['name']}...")
        ads = fetch_ads_for_model(car)
        print(f"   נמצאו {len(ads)} מודעות רלוונטיות")

        for ad in ads:
            if not ad["id"] or ad["id"] in seen:
                continue
            seen.add(ad["id"])
            new_ads.append(ad)

        time.sleep(3)

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


if __name__ == "__main__":
    print("🚀 סורק יד2 מתחיל לעבוד!")
    print(f"⏱ סריקה כל {SCAN_INTERVAL_MINUTES} דקות")
    print(f"📅 שנים: {MIN_YEAR}-{CURRENT_YEAR}")
    print(f"💰 מחיר מקסימלי: {MAX_PRICE:,} ₪")
    print(f"🚙 דגמים: {', '.join(c['name'] for c in CAR_MODELS)}")

    if not TWILIO_ACCOUNT_SID:
        print("❌ שגיאה: TWILIO_ACCOUNT_SID לא הוגדר!")
    elif not MY_WHATSAPP_NUMBER:
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
