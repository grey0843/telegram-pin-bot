import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8518027565:AAGJBIU5S55Wankg7uSa6JFiD4HlTcalmFs"
PIN_DURATION = 3600  # 1 hour


async def start_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await update.message.reply_text("Ye bot sirf groups me kaam karta hai. Mujhe group me add karke admin banayein.")
        return

    chat_member = await context.bot.get_chat_member(chat.id, user.id)
    if chat_member.status not in ["creator", "administrator"]:
        await update.message.reply_text("❌ Ye command sirf group admins use kar sakte hain.")
        return

    context.chat_data["is_active"] = True
    context.chat_data["waiting_for_pin"] = True

    hours = PIN_DURATION // 3600
    time_text = f"{hours} hour(s)" if hours >= 1 else f"{PIN_DURATION} seconds"

    await context.bot.send_message(
        chat_id=chat.id,
        text=f"📢 **Notification:** Next message will be pinned for {time_text}!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.message

    if not msg or chat.type == "private":
        return

    is_active = context.chat_data.get("is_active", False)
    waiting_for_pin = context.chat_data.get("waiting_for_pin", False)

    if is_active and waiting_for_pin:
        if msg.from_user and msg.from_user.is_bot:
            return

        context.chat_data["waiting_for_pin"] = False
        context.chat_data["current_msg_id"] = msg.message_id

        try:
            await context.bot.pin_chat_message(
                chat_id=chat.id,
                message_id=msg.message_id,
                disable_notification=False
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat.id,
                text="⚠️ Message pin nahi ho paya. Check karein ki bot ke paas 'Pin Messages' permission hai."
            )
            context.chat_data["waiting_for_pin"] = True
            return

        context.job_queue.run_once(
            unpin_and_repeat,
            when=PIN_DURATION,
            chat_id=chat.id,
            data=msg.message_id
        )


async def unpin_and_repeat(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    msg_id = job.data

    try:
        await context.bot.unpin_chat_message(chat_id=chat_id, message_id=msg_id)
    except Exception as e:
        print(f"Unpin failed: {e}")

    chat_data = context.application.chat_data.get(chat_id, {})
    if chat_data.get("is_active", False):
        chat_data["waiting_for_pin"] = True
        hours = PIN_DURATION // 3600
        time_text = f"{hours} hour(s)" if hours >= 1 else f"{PIN_DURATION} seconds"

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏳ Time complete! Agla message fir se {time_text} ke liye pin hoga!"
        )


async def stop_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        return

    chat_member = await context.bot.get_chat_member(chat.id, user.id)
    if chat_member.status not in ["creator", "administrator"]:
        return

    context.chat_data["is_active"] = False
    context.chat_data["waiting_for_pin"] = False
    await update.message.reply_text("🛑 Auto-Pin cycle band kar di gayi hai.")


async def handle_ping(request):
    return web.Response(text="Bot is running active!")


async def run():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start_cycle", start_cycle))
    app.add_handler(CommandHandler("stop_cycle", stop_cycle))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    # Chhota Web Server jo Render ko port dega
    server = web.Application()
    server.router.add_get("/", handle_ping)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Telegram bot start
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
    
