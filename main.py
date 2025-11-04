import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import firebase_admin
from firebase_admin import credentials, firestore
import flask
import os

# --- আপনার তথ্য এখানে পরিবর্তন করুন ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_WEB_APP_URL = "https://your-webapp-link.com"  # এখানে আপনার ওয়েব অ্যাপের URL বসান
# ------------------------------------

# Firebase Admin SDK ইনিশিয়ালাইজ করুন
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase App সফলভাবে চালু হয়েছে!")
except Exception as e:
    print(f"Firebase চালু করতে সমস্যা হয়েছে: {e}")
    db = None

# বট টোকেন না পেলে বট চালু হবে না
if not BOT_TOKEN:
    print("ত্রুটি: টেলিগ্রাম বটের টোকেন পাওয়া যায়নি। অনুগ্রহ করে Environment Variable সেট করুন।")
    exit() # টোকেন না থাকলে প্রোগ্রাম বন্ধ করে দাও

# বট এবং ফ্লাস্ক অ্যাপ অবজেক্ট তৈরি করুন
bot = telebot.TeleBot(BOT_TOKEN, threaded=False) # Webhook এর জন্য threaded=False ব্যবহার করা ভালো
app = flask.Flask(__name__)

# --- Webhook অংশ ---
# এই রুটটি টেলিগ্রাম থেকে মেসেজ গ্রহণ করবে
@app.route('/', methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        flask.abort(403)

# এই রুটটি শুধু দেখানোর জন্য যে সার্ভার চালু আছে
@app.route('/')
def index():
    return "Bot is alive and using Webhook!"


# --- Telegram Bot অংশ ---
def create_webapp_keyboard():
    keyboard = InlineKeyboardMarkup()
    web_app_button = InlineKeyboardButton(text="▶️ Open App", web_app=WebAppInfo(url=YOUR_WEB_APP_URL))
    keyboard.add(web_app_button)
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    print(f"'/start' কমান্ড পাওয়া গেছে: {chat_id} ({user_name}) থেকে")
    
    welcome_message = f"👋 Hello, {user_name}!\n\nWelcome to our bot. Click the button below to start."
    
    try:
        if db:
            settings_ref = db.collection('settings').document('app')
            settings_doc = settings_ref.get()
            if settings_doc.exists:
                settings_data = settings_doc.to_dict()
                if 'welcomeMessage' in settings_data and settings_data['welcomeMessage']:
                    welcome_message = settings_data['welcomeMessage'].replace('{name}', user_name)
    except Exception as e:
        print(f"Firebase থেকে ওয়েলকাম মেসেজ আনতে সমস্যা হয়েছে: {e}")

    try:
        bot.send_message(chat_id, welcome_message, parse_mode="Markdown", reply_markup=create_webapp_keyboard())
    except Exception:
        bot.send_message(chat_id, welcome_message, reply_markup=create_webapp_keyboard())


# --- Webhook সেট করার অংশ (সার্ভার চালু হওয়ার পর শুধু একবার চলবে) ---
# Render সার্ভিসের URL টি স্বয়ংক্রিয়ভাবে পেতে
WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"

if __name__ != '__main__':
    print(f"Webhook সেট করা হচ্ছে: {WEBHOOK_URL}")
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook সফলভাবে সেট হয়েছে।")
