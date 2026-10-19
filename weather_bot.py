import os
import io
import requests
import datetime
from datetime import datetime as dt
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# អានទិន្នន័យពី file .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN or TOKEN == "YOUR_TOKEN_HERE":
    print("❌ បញ្ហា៖ សូមដាក់ Token ក្នុង file .env ជាមុនសិន!")
    exit()

plt.rcParams['font.family'] = 'Leelawadee UI' 

PHNOM_TOUCH_LAT = 13.4093
PHNOM_TOUCH_LON = 103.0426
PHNOM_TOUCH_NAME = "ភូមិភ្នំតូច, ស្រុកមង្គលបូរី, ខេត្តបន្ទាយមានជ័យ"
SUBSCRIBERS_FILE = "subscribers.txt"

PHNOM_PENH_KHANS = {
    "ខណ្ឌចំការមន": (11.5362, 104.9132),
    "ខណ្ឌដូនពេញ": (11.5710, 104.9200),
    "ខណ្ឌប្រាំពីរមករា": (11.5640, 104.9140),
    "ខណ្ឌទួលគោក": (11.5650, 104.9000),
    "ខណ្ឌដង្កោ": (11.5200, 104.8500),
    "ខណ្ឌមានជ័យ": (11.5200, 104.9400),
    "ខណ្ឌឫស្សីកែវ": (11.6200, 104.9100),
    "ខណ្ឌសែនសុខ": (11.6000, 104.8800),
    "ខណ្ឌពោធិ៍សែនជ័យ": (11.5500, 104.8200),
    "ខណ្ឌជ្រោយចង្វារ": (11.6000, 104.9500),
    "ខណ្ឌព្រែកព្នៅ": (11.6500, 104.8500),
    "ខណ្ឌច្បារអំពៅ": (11.5300, 104.9500),
    "ខណ្ឌបឹងកេងកង": (11.5450, 104.9200),
    "ខណ្ឌកំបូល": (11.5200, 104.7500)
}

# ប្រព័ន្ធគ្រប់គ្រងអ្នកទទួលសារ
def save_subscriber(chat_id):
    chat_id = str(chat_id)
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "w") as f:
            f.write(f"{chat_id}\n")
        return
    with open(SUBSCRIBERS_FILE, "r") as f:
        subscribers = f.read().splitlines()
    if chat_id not in subscribers:
        with open(SUBSCRIBERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")

def get_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    with open(SUBSCRIBERS_FILE, "r") as f:
        return f.read().splitlines()

def get_weather_desc(code):
    return {
        0: "មេឃស្រឡះ", 1: "មេឃស្រឡះខ្លះ", 2: "មេឃមានពពកខ្លះ", 3: "មេឃមានពពកច្រើន",
        45: "មានអ័ព្ទ", 48: "មានអ័ព្ទកក់ក្តៅ", 
        51: "ភ្លៀងរ៉ៃៗស្រាល", 53: "ភ្លៀងរ៉ៃៗមធ្យម", 55: "ភ្លៀងរ៉ៃៗខ្លាំង",
        61: "ភ្លៀងស្រាល", 63: "ភ្លៀងមធ្យម", 65: "ភ្លៀងធ្ងន់",
        80: "ភ្លៀងរាយប៉ាយស្រាល", 81: "ភ្លៀងរាយប៉ាយមធ្យម", 82: "ភ្លៀងរាយប៉ាយខ្លាំង",
        95: "មានផ្គររន្ទះ", 96: "ផ្គររន្ទះ និងព្រិលធ្លាក់", 99: "ផ្គររន្ទះខ្លាំង"
    }.get(code, "មិនស្គាល់")

def get_aqi_desc(aqi):
    if aqi <= 50: return "ល្អ (Good) 🟢"
    elif aqi <= 100: return "មធ្យម (Moderate) 🟡"
    elif aqi <= 150: return "មិនល្អសម្រាប់អ្នកប្រកាន់អាឡែស៊ី 🟠"
    elif aqi <= 200: return "មិនល្អ (Unhealthy) 🔴"
    else: return "បង្គ្រប់គ្រោះ (Hazardous) 🟣"

def get_full_weather_data(lat, lon):
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,precipitation_probability_max",
        "hourly": "precipitation_probability", 
        "timezone": "auto", "forecast_days": 3 
    }
    aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aqi_params = {"latitude": lat, "longitude": lon, "current": "us_aqi,pm2_5", "timezone": "auto"}
    
    try:
        w_res = requests.get(weather_url, params=weather_params, timeout=10).json()
        a_res = requests.get(aqi_url, params=aqi_params, timeout=10).json()
        return w_res, a_res
    except Exception as e:
        print(f"API Error: {e}")
        return None, None

def create_rain_charts(hourly_data, daily_data, location_name):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    today_str = dt.now().strftime("%Y-%m-%d")
    start_time_str = f"{today_str}T00:00" 
    
    try:
        start_index = hourly_data["time"].index(start_time_str)
    except ValueError:
        start_index = 0 
        
    times = hourly_data["time"][start_index:start_index+24]
    rain_prob = hourly_data["precipitation_probability"][start_index:start_index+24]
    hours_labels = [dt.strptime(t, "%Y-%m-%dT%H:%M").strftime("%H:00") for t in times]
    
    bars = ax1.bar(hours_labels, rain_prob, color='skyblue', edgecolor='blue')
    for bar, prob in zip(bars, rain_prob):
        if prob >= 50: bar.set_color('dodgerblue')
            
    ax1.set_title(f"1. ឱកាសភ្លៀង 24 ម៉ោង (00:00 ដល់ 23:00) - {location_name}", fontsize=14, fontweight='bold')
    ax1.set_ylabel("ឱកាសភ្លៀង (%)", fontsize=12)
    ax1.tick_params(axis='x', rotation=45, labelsize=9)
    for label in ax1.get_xticklabels(): label.set_horizontalalignment('right')
    ax1.set_ylim(0, 100)
    ax1.grid(axis='y', linestyle='--', alpha=0.7)

    daily_times = daily_data["time"]
    daily_rain = daily_data["precipitation_probability_max"]
    daily_labels = [dt.strptime(t, "%Y-%m-%d").strftime("%d/%m") for t in daily_times]
        
    bars2 = ax2.bar(daily_labels, daily_rain, color='lightgreen', edgecolor='green', width=0.4)
    for bar, prob in zip(bars2, daily_rain):
        if prob >= 50: bar.set_color('forestgreen')
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{prob}%', ha='center', va='bottom', fontsize=10)

    ax2.set_title(f"2. ឱកាសភ្លៀងខ្ពស់បំផុតប្រចាំថ្ងៃ (%) - {location_name}", fontsize=14, fontweight='bold')
    ax2.set_xlabel("ថ្ងៃ/ខែ", fontsize=12)
    ax2.set_ylabel("ឱកាសភ្លៀង (%)", fontsize=12)
    ax2.set_ylim(0, 110) 
    ax2.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    return buf

def format_weather_message(location_name, w_data, a_data):
    current = w_data["current"]
    daily = w_data["daily"]
    aqi = a_data["current"]["us_aqi"]
    pm25 = a_data["current"]["pm2_5"]
    uv = daily["uv_index_max"][0]
    sunrise = dt.strptime(daily["sunrise"][0], "%Y-%m-%dT%H:%M").strftime("%H:%M")
    sunset = dt.strptime(daily["sunset"][0], "%Y-%m-%dT%H:%M").strftime("%H:%M")

    message = (
        f"🌤️ <b>អាកាសធាតុបច្ចុប្បន្ននៅ {location_name}</b>\n\n"
        f"🌡️ សីតុណ្ហភាព៖ {current['temperature_2m']}°C (ហុយដូច {current['apparent_temperature']}°C)\n"
        f"💧 សំណើម៖ {current['relative_humidity_2m']}%\n"
        f"💨 ខ្យល់៖ {current['wind_speed_10m']} គីឡូម៉ែត្រ/ម៉ោង\n"
        f"📝 ស្ថានភាព៖ {get_weather_desc(current['weather_code'])}\n"
        f"☀️ សន្ទស្សន៍ UV៖ {uv} (កម្រិតខ្ពស់បំផុតថ្ងៃនេះ)\n"
        f"🌅 ថ្ងៃរះ៖ {sunrise} | ថ្ងៃលិច៖ {sunset}\n"
        f"🌫️ គុណភាពខ្យល់ (AQI)៖ {aqi} - {get_aqi_desc(aqi)} (PM2.5: {pm25})\n\n"
        f"📅 <b>ព្យាករណ៍ ២ ថ្ងៃខាងមុខ៖</b>\n"
    )
    for i in range(1, 3):
        date_obj = dt.strptime(daily["time"][i], "%Y-%m-%d")
        message += (
            f"🔹 <b>{date_obj.strftime('%d/%m/%Y')}</b>\n"
            f"   🌡️ {daily['temperature_2m_min'][i]}°C - {daily['temperature_2m_max'][i]}°C\n"
            f"   🌧️ ឱកាសភ្លៀង៖ {daily['precipitation_probability_max'][i]}%\n"
            f"   📝 {get_weather_desc(daily['weather_code'][i])}\n\n"
        )
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_subscriber(update.effective_chat.id)
    
    reply_keyboard = [
        [KeyboardButton("🌤️ អាកាសធាតុភូមិភ្នំតូច")],
        [KeyboardButton("🏙️ អាកាសធាតុរាជធានីភ្នំពេញ (ខណ្ឌ)")]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, is_persistent=True)
    await update.message.reply_text(
        "សួស្តី! ខ្ញុំជា Bot ព្យាករណ៍អាកាសធាតុឆ្លាតវៃ។\n"
        "✅ ខ្ញុំបានចងចាំអ្នកហើយ! ខ្ញុំនឹងផ្ញើសារជូនដំណឹងអាកាសធាតុមកអ្នកនៅម៉ោង ៦ ព្រឹករៀងរាល់ថ្ងៃ និងព្រមានពេលមានភ្លៀង។\n\n"
        "សូមចុចប៊ូតុងខាងក្រោមដើម្បីជ្រើសរើសទីតាំង៖",
        reply_markup=reply_markup
    )

async def fetch_and_send_weather(message_obj, location_name, lat, lon, is_callback=False):
    wait_msg = None
    if not is_callback:
        wait_msg = await message_obj.reply_text("⏳ កំពុងទាញយកទិន្នន័យ...")
        
    w_data, a_data = get_full_weather_data(lat, lon)
    
    if w_data and a_data:
        message = format_weather_message(location_name, w_data, a_data)
        chart_buf = create_rain_charts(w_data["hourly"], w_data["daily"], location_name)
        
        if is_callback:
            await message_obj.edit_message_text(message, parse_mode="HTML")
            await message_obj.message.reply_photo(photo=chart_buf, caption="📊 ក្រាបឱកាសភ្លៀង")
        else:
            await wait_msg.delete()
            await message_obj.reply_text(message, parse_mode="HTML")
            await message_obj.reply_photo(photo=chart_buf, caption="📊 ក្រាបឱកាសភ្លៀង")
    else:
        if wait_msg: await wait_msg.delete()
        await message_obj.reply_text("សូមទោស មានបញ្ហាក្នុងការទាញទិន្នន័យ។")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_subscriber(update.effective_chat.id)
    
    text = update.message.text
    if text == "🌤️ អាកាសធាតុភូមិភ្នំតូច":
        await fetch_and_send_weather(update.message, PHNOM_TOUCH_NAME, PHNOM_TOUCH_LAT, PHNOM_TOUCH_LON)
    elif text == "🏙️ អាកាសធាតុរាជធានីភ្នំពេញ (ខណ្ឌ)":
        keyboard = []
        khan_list = list(PHNOM_PENH_KHANS.keys())
        for i in range(0, len(khan_list), 2):
            row = [InlineKeyboardButton(khan_list[i], callback_data=f"khan_{i}")]
            if i + 1 < len(khan_list):
                row.append(InlineKeyboardButton(khan_list[i+1], callback_data=f"khan_{i+1}"))
            keyboard.append(row)
        await update.message.reply_text("🏙️ សូមជ្រើសរើស <b>ខណ្ឌ</b>៖", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("khan_"):
        index = int(query.data.split("_")[1])
        khan_name = list(PHNOM_PENH_KHANS.keys())[index]
        lat, lon = PHNOM_PENH_KHANS[khan_name]
        await query.edit_message_text(f"⏳ កំពុងទាញយកទិន្នន័យនៅ {khan_name}...")
        await fetch_and_send_weather(query, khan_name, lat, lon, is_callback=True)

# មុខងារជូនដំណឹងស្វ័យប្រវត្តិ
async def daily_morning_alert(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_subscribers()
    if not subscribers: return
    
    w_data, a_data = get_full_weather_data(PHNOM_TOUCH_LAT, PHNOM_TOUCH_LON)
    if w_data and a_data:
        message = "🌅 <b>អាកាសធាតុព្រឹកនេះ៖</b>\n\n" + format_weather_message(PHNOM_TOUCH_NAME, w_data, a_data)
        for chat_id in subscribers:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
            except Exception as e:
                print(f"បរាជ័យក្នុងការផ្ញើទៅ {chat_id}: {e}")

async def check_rain_alert(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_subscribers()
    if not subscribers: return
    
    w_data, _ = get_full_weather_data(PHNOM_TOUCH_LAT, PHNOM_TOUCH_LON)
    if not w_data: return
    
    current_hour = dt.now().hour
    next_3_hours_rain = w_data["hourly"]["precipitation_probability"][current_hour:current_hour+3]
    
    if any(prob >= 60 for prob in next_3_hours_rain):
        message = "⚠️ <b>ការជូនដំណឹងភ្លៀងធ្លាក់!</b>\n\n"
        message += "មានឱកាសខ្ពស់ដែលនឹងមានភ្លៀងធ្លាក់នៅក្នុងរយៈពេល ២ ទៅ ៣ ម៉ោងខាងមុខនេះ។ សូមរៀបចំឆ័ត្រ!"
        for chat_id in subscribers:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
            except Exception as e:
                print(f"បរាជ័យក្នុងការផ្ញើទៅ {chat_id}: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    job_queue = app.job_queue
    if job_queue:
        cambodia_tz = datetime.timezone(datetime.timedelta(hours=7))
        
        # ជូនដំណឹងអាកាសធាតុព្រឹក រៀងរាល់ម៉ោង 06:00 ព្រឹក
        job_queue.run_daily(daily_morning_alert, time=datetime.time(hour=6, minute=0, tzinfo=cambodia_tz))
        
        # ពិនិត្យភ្លៀងរៀងរាល់ 3 ម៉ោងម្តង
        job_queue.run_repeating(check_rain_alert, interval=datetime.timedelta(hours=3), first=10)
        
        print("✅ ប្រព័ន្ធជូនដំណឹងស្វ័យប្រវត្តិ ត្រូវបានបើក!")

    print("✅ Bot កំពុងដំណើរការ...")
    print("សូមចូលទៅ Telegram រួចវាយ /start ដើម្បីឱ្យ Bot ចងចាំអ្នក!")
    
    app.run_polling()