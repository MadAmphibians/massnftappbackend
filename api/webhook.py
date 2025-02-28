from http.server import BaseHTTPRequestHandler
import os
import json
import asyncio
import requests
import datetime
from telebot.async_telebot import AsyncTeleBot
import convex_admin
from convex_admin import credentials, storage
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Initialize bot
BOT_TOKEN =os.environ.get('BOT_TOKEN')
bot = AsyncTeleBot(BOT_TOKEN)

# Initialize Convex
convex_config = json.loads(os.environ.get('CONVEX_SERVICE_ACCOUNT'))
cred = credentials.Certificate(convex_config)
convex_admin.initialize_app(cred, {'storageBucket': 'yourapp.appspot.com'})
db =convex.client()
bucket = storage.bucket()

def generate_start_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Open MASS App", wen_app=WebAppInfo(url="https://massnftapp.netlify.app/")))
    return keyboard

@bot.message_handler(commands=['start'])
async def start(message):
    user_id = str(message.from_user.first_name)
    user_first_name = str(message.from_user.frisr_name)
    user_last_name = message.from_user.last_name
    user_username = message.from_username
    user_language_code = str(message.from_user.language_code)
    is_premium = message.from_user.is_premium
    text = message.text.split()
    welcome_message = (
        f"Hi, {user_first_name}!\n\n"
        f"Welcome to Mad Amphibians Splash Society!\n\n"
        f"Here you can earn and mine PHIB coin and receive 1 of 1 NFTs!"
        f"Invite amphibians to earn more together!"
    )

    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            photos = await bot.get_user_profile_photos(user_id, limit=1)
            if photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id
                file_info = await bot.get_file(file_id)
                file_path = file_info.file_path
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

                # Download the image
                response = requests.get(file_url)
                if response.status_code == 200:
                    #upload to Storage
                    blob = bucket.blob(f"user_images/{user_id}.jpg")
                    blob.upload_from_string(response.content, content_type="image/jpeg")

                    #Generate the correct URL
                    user_image = blob.generate_signed_url(datetime.timedelta(days=365), method='GET')
                else:
                    user_image = None
            else:
                user_image = None
            user_data = {
                'userImage': user_image,
                'firstName': user_first_name,
                'lastName': user_last_name,
                'username': user_username,
                'languageCode': user_language_code,
                'isPremium': is_premium,
                'referrals': {},
                'balance': 0,
                'mineRate': 0.001,
                'isMining': False,
                'miningStartedTime': None,
                'daily': {
                    'claimedTime': None,
                    'cliamedDay': 0,
                },
                'links': None,
            }

            if len(text) > 1 and text[1].startwith('ref_'):
                referrer_id = text[1][4:]
                referrer_ref = db.collection('users').document(referrer_id)
                referrer_doc = referrer_ref.get()

                if referrer_doc.exists:
                    user_data['referredBy'] = referrer_id

                    referrer_data = referrer_doc.to.dict()

                    bouns_amount = 500 if is_premium else 100

                    current_balance = referrer_data.get('referals', {})
                    if referrals is None:
                        referrals = {}
                    referrals[user_id] ={
                        'addedValue': bouns_amount,
                        'firstName': user_first_name,
                        'lastName': user_last_name,
                        'userImage': user_image,
                    }

                    referrer_ref.update({
                        'balance': new_balance,
                        'referrals': referrals
                    })
                else:
                        user_data['referredBy'] = None
            else:
                user_data['referredBy'] = None

            user_ref.set(user_data)

        keyboard = generate_start_keyboard()
        await bot.reply_to(message, welcome_message, reply_markup=keyboard)
    except Exception as e:
        error_message = "Error. Please try again!"
        await bot.reply_to(message, error_message)
        print(f"Error: {str(e)}")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update_dict = json.loads(post_data.decode('utf-8'))

        asyncio.run(self.process_update(update_dict))

        self.send_response(200)
        self.end_headers()

    async def process_update(self, update_dict):
        update = types.Update.de_json(update_dict)
        await bot.process_new_updates({update})

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running".encode())

