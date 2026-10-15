import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Aapka bot token
BOT_TOKEN = "8518027565:AAGJBIU5S55Wankg7uSa6JFiD4HlTcalmFs"

# Pin Duration: 1 ghanta = 3600 seconds
PIN_DURATION = 3600  


async def start_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # Private chat me block karein
    if chat.type == "private":
        await update.message.reply_text("Ye bot sirf groups me kaam karta hai. Mujhe apne group me add karke admin banayein.")
        return

    # Check karein command dene wala group admin hai ya nahi
    chat_member = await context.bot.get_chat_member(chat.id, user.id)
    if chat_member.status not in ["creator", "administrator"]:
        await update.message.reply_text("❌ Ye command sirf group admins use kar sakte hain.")
        return

    # Is group ke liye auto-pin on karein
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

    # Agar cycle on hai aur next message ka wait hai
    if is_active and waiting_for_pin:
        # Bot ke messages ko ignore karein
        if msg.from_user and msg.from_user.is_bot:
            return

        context.chat_data["waiting_for_pin"] = False
        context.chat_data["current_msg_id"] = msg.message_id

        # Message pin karein
        try:
            await context.bot.pin_chat_message(
                chat_id=chat.id,
                message_id=msg.message_id,
                disable_notification=False
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat.id,
                text="⚠️ Message pin nahi ho paya. Kripya check karein ki bot ko group me 'Pin Messages' permission di gayi hai."
            )
            context.chat_data["waiting_for_pin"] = True
            return

        # Timer lagayein unpin karne ke liye
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

    # Purana message unpin karein
    try:
        await context.bot.unpin_chat_message(chat_id=chat_id, message_id=msg_id)
    except Exception as e:
        print(f"Unpin failed in chat {chat_id}: {e}")

    # Agar cycle band nahi ki gayi hai toh agla message announce karein
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


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start_cycle", start_cycle))
    app.add_handler(CommandHandler("stop_cycle", stop_cycle))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("Bot is successfully running...")
    app.run_polling()


if __name__ == "__main__":
    main()
  
