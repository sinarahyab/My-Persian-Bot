import os
import logging
import tempfile
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import whisper
import ffmpeg
import torch
from transformers import pipeline

# تنظیمات ربات
TOKEN = os.getenv("TELEGRAM_TOKEN") or "YOUR_TOKEN_HERE"  # توکن خودت رو اینجا قرار بده
MAX_SIZE = 2000 * 1024 * 1024  # 2 گیگابایت

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# بارگیری مدل تصحیح املایی (فقط یکبار در حافظه میمونه)
corrector = pipeline("text2text-generation", model="erfan226/persian-spell-checker")

def enhance_persian_text(text):
    """تابع اختصاصی برای بهبود کیفیت متن فارسی"""
    # تصحیح املایی با مدل
    corrected = corrector(text)[0]['generated_text']
    
    # اصلاح خطاهای رایج دستی
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
    
    # بهبود ساختار جمله
    sentences = corrected.split('.')
    enhanced = []
    for sentence in sentences:
        if sentence.strip():
            # حذف تکرارهای غیرضروری
            sentence = re.sub(r'(\b\w+\b)(?=.*\1)', '', sentence)
            enhanced.append(sentence.strip())
    
    return '. '.join(enhanced)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # دریافت فایل
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
        
        # تشخیص گفتار با تنظیمات پیشرفته
        model = whisper.load_model("large-v3")
        result = model.transcribe(
            audio_path,
            language="fa",
            task="transcribe",
            temperature=0.1,
            best_of=3,
            beam_size=5,
            fp16=False  # الزامی برای CPU
        )
        transcript = result["text"]
        # کاهش حجم متن برای پردازش بهتر
transcript = transcript[:2000]  # فقط 2000 کاراکتر اول

# ارسال به سرویس تصحیح رایگان ایرانی
import requests
url = "https://api.faradars.org/spell-check"
response = requests.post(url, json={"text": transcript})
corrected_text = response.json()["corrected_text"]
        # بهبود کیفیت متن
        await update.message.reply_text("🔧 در حال بهبود کیفیت متن...")
        enhanced_text = enhance_persian_text(transcript)
        
        # قالب‌بندی حرفه‌ای
        formatted_text = f"""
🎤 متن استخراج شده:
-------------------
{transcript}

✅ نسخه بهبود یافته:
-------------------
{enhanced_text}

✨ پردازش با موفقیت انجام شد!
        """
        
        # ارسال نتیجه
        await update.message.reply_text(formatted_text)
        
        # پاک‌سازی فایل‌های موقت
        os.unlink(input_path)
        os.unlink(audio_path)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"⚠️ خطا در پردازش: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # افزودن هندلر برای انواع فایل‌های رسانه‌ای
    media_filter = filters.VIDEO | filters.AUDIO | filters.Document.VIDEO | filters.Document.AUDIO
    app.add_handler(MessageHandler(media_filter, handle_media))
    
    app.run_polling()

if __name__ == "__main__":
    main()
