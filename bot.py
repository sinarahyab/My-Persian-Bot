from aiogram import Bot, Dispatcher, types, executor
import os
import whisper
import openai

API_TOKEN = 'توکن ربات'
openai.api_key = 'کلید OpenAI'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
model = whisper.load_model("medium")  # برای دقت بالا

@dp.message_handler(content_types=types.ContentType.VIDEO)
async def handle_video(message: types.Message):
    file = await message.video.get_file()
    if message.video.file_size > 2 * 1024 * 1024 * 1024:
        await message.reply("حجم فایل بیش از 2 گیگابایت است.")
        return

    file_path = file.file_path
    file_on_disk = f"temp/{file.file_unique_id}.mp4"
    await bot.download_file(file_path, destination=file_on_disk)

    # تبدیل صوت به متن
    result = model.transcribe(file_on_disk)
    text = result["text"]

    await message.reply("متن استخراج شده:\n\n" + text[:4000])  # حداکثر 4000 کاراکتر

    os.remove(file_on_disk)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
def summarize_news(text):
    prompt = f"""متن زیر را به سبک یک خبر رسمی تنظیم کن:
{text}"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
@dp.message_handler(commands=['تنظیم_خبر'])
async def handle_summarize(message: types.Message):
    reply = summarize_news(message.reply_to_message.text)
    await message.reply(reply)
result = model.transcribe(file_on_disk, language='fa')  # fa، en، ru، zh، fr
