import os
import re
import logging
import tempfile
import requests
import ffmpeg
import whisper
import torch

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from transformers import pipeline

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات ربات
TOKEN = os.getenv("TELEGRAM_TOKEN") or "7823167590:AAFCOkYE5FX6wJbK4clxzNo8UMquKAbYvCc"
MAX_SIZE = 2000 * 1024 * 1024  # 2 گیگابایت

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# بارگیری مدل تصحیح املایی
corrector = pipeline("text2text-generation", model="erfan226/persian-spell-checker")

def enhance_persian_text(text):
    """بهبود متن فارسی با تصحیح املایی و اصلاحات دستی"""
    corrected = corrector(text)[0]['generated_text']

    corrections = {
        r'مرض\b': 'مرز',
        r'شاہد': 'شاهد',
        r'بیسیار': 'بسیار',
        r'رایی': 'راحت',
        r'تِرِد': 'تردد',
        r'صادق\b': 'سادات',
        r'سلیمانی\b': 'سلیمانیه',
        r'چارشنبه': 'چهارشنبه',
        r'خوابگذاری': 'خبرگذاری',
        r'صفحه': 'پایانه',
        r'تحالیت': 'تحویل',
        r'صهیب': 'سعید',
        r'مردمی': 'مرزی'
    }

    for pattern, replacement in corrections.items():
        corrected = re.sub(pattern, replacement, corrected)

    # بهبود ساختار جملات
    sentences = corrected.split('.')
    enhanced = []
    for sentence in sentences:
        if sentence.strip():
            sentence = re.sub(r'(\b\w+\b)(?=.*\1)', '', sentence)
            enhanced.append(sentence.strip())

    return '. '.join(enhanced)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = await update.message.effective_attachment.get_file()

        if file.file_size > MAX_SIZE:
            await update.message.reply_text("❌ حجم فایل بیش از ۲ گیگابایت است!")
            return

        await update.message.reply_text("⏳ فایل دریافت شد. پردازش آغاز شد...")

        # دانلود فایل موقت
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
            await file.download_to_drive(tmp_file.name)
            input_path = tmp_file.name

        # تبدیل به صوت
        audio_path = f"{input_path}.wav"
        (
            ffmpeg.input(input_path)
            .output(audio_path, ar=16000, ac=1)
            .run(overwrite_output=True, quiet=True)
        )

        # تشخیص گفتار با مدل Whisper
        model = whisper.load_model("large-v3")
        result = model.transcribe(
            audio_path,
            language="fa",
            task="transcribe",
            temperature=0.1,
            best_of=3,
            beam_size=5,
            fp16=torch.cuda.is_available()
        )
        transcript = result["text"][:2000]  # محدود کردن متن برای پردازش

        # استفاده از API ایرانی برای تصحیح املایی
        try:
            response = requests.post("https://api.faradars.org/spell-check", json={"text": transcript})
            if response.status_code == 200:
                corrected_text = response.json().get("corrected_text", transcript)
            else:
                corrected_text = transcript
        except:
            corrected_text = transcript

        await update.message.reply_text("🔧 در حال بهبود کیفیت متن...")

        # بهبود نهایی متن
        enhanced_text = enhance_persian_text(corrected_text)

        # قالب‌بندی خروجی
        formatted_text = f"""
🎤 متن استخراج شده:
-------------------
{transcript}

✅ نسخه بهبود یافته:
-------------------
{enhanced_text}

✨ پردازش با موفقیت انجام شد!
        """

        await update.message.reply_text(formatted_text)

        # پاک‌سازی فایل‌های موقت
        os.unlink(input_path)
        os.unlink(audio_path)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"⚠️ خطا در پردازش: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()

    # هندلر برای دریافت فایل‌های صوتی و تصویری
    media_filter = filters.VIDEO | filters.AUDIO | filters.Document.VIDEO | filters.Document.AUDIO
    app.add_handler(MessageHandler(media_filter, handle_media))

    app.run_polling()

if __name__ == "__main__":
    main()
