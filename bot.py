from telegram import *
from telegram.ext import *
import json, os
from dotenv import load_dotenv
import logging

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
# дллвтыадлывтатдл
VIDEO_META_FILE = "videos.json"
USER_DATA_FILE = "user_data.json"
ADMIN_FILE = "admin_ids.json"
VIDEO, TITLE, PRICE = range(3)
ITEMS_PER_PAGE = 8

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


def load_videos():
    if not os.path.exists(VIDEO_META_FILE) or os.stat(VIDEO_META_FILE).st_size == 0:
        return []
    with open(VIDEO_META_FILE, "r") as f:
        return json.load(f)


def save_videos(videos):
    with open(VIDEO_META_FILE, "w") as f:
        json.dump(videos, f, indent=2)


def load_user_data():
    if not os.path.exists(USER_DATA_FILE) or os.stat(USER_DATA_FILE).st_size == 0:
        return {}
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)


def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)


def load_admins():
    if not os.path.exists(ADMIN_FILE):
        return []
    with open(ADMIN_FILE, "r") as f:
        return json.load(f)


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in load_admins()
    keyboard = [
        [InlineKeyboardButton("📚 Tutorials", callback_data='tutorials_page_0'),
         InlineKeyboardButton("🎥 My Videos", callback_data='my_videos')],
        [InlineKeyboardButton("💬 Help", callback_data='help')],
    ]
    if is_admin:
        keyboard[1].append(InlineKeyboardButton("⬆️ Upload Video", callback_data='upload_video'))

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                "👋 Welcome! Choose an option:", reply_markup=reply_markup)
        except Exception:
            # fallback if it's a media message and can't be edited
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="👋 Welcome! Choose an option:",
                reply_markup=reply_markup
            )
    elif update.message:
        await update.message.reply_text("👋 Welcome! Choose an option:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("tutorials_page_"):
        page = int(data.split("_")[-1])
        return await show_tutorials(update, context, page)
    if data == 'my_videos':
        return await show_my_videos(update, context)
    if data == 'help':
        await query.edit_message_text("ℹ️ Use 📚 to browse tutorials, 🎥 to view yours.",
                                      reply_markup=InlineKeyboardMarkup(
                                          [[InlineKeyboardButton("🔙 Back", callback_data='back_to_main_menu')]]))
    if data == 'back_to_main_menu':
        return await main_menu(update, context)
    if data == 'back_to_tutorials':
        if context.user_data['last_source'] == 'handle_preview':
            await update.callback_query.message.delete()
        return await show_tutorials(update, context)
    if data == 'back_to_my_videos':
        return await show_my_videos(update, context)
    if data.startswith("preview_"):
        return await handle_preview(update, context)
    if data.startswith("watch_tutorials_"):
        await update.callback_query.message.delete()
        return await watch_tutorials(update, context)
    if data.startswith("buy_video_"):
        return await handle_buy(update, context)


async def handle_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    idx = int(query.data.split("_")[1])
    uid = str(query.from_user.id)
    vid = load_videos()[idx]
    purchased = load_user_data().get(uid, [])

    kb = []
    if idx not in purchased:
        kb.append([InlineKeyboardButton(f"💳 Buy for ${vid['price']}", callback_data=f"buy_video_{idx}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_tutorials')])
    context.user_data['last_source'] = 'handle_preview'
    black_image_file_id = 'AgACAgIAAxkBAAICf2gZ4gNfgl_aGe-noIy82gMYmGziAAI-9TEb3svQSF4KL9uMx8C-AQADAgADeQADNgQ'
    await query.edit_message_media(
        media=InputMediaPhoto(
            media=black_image_file_id,
            caption=f"🎬 *{vid['title']}*",
            parse_mode="Markdown"),
        reply_markup=InlineKeyboardMarkup(kb)
    )


# async def debug_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if update.message.photo:
#         file_id = update.message.photo[-1].file_id  # Get highest-resolution version
#         await update.message.reply_text(f"🆔 File ID: `{file_id}`", parse_mode="Markdown")
#         print("File ID:", file_id)


async def show_tutorials(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    videos = load_videos()
    total = len(videos)
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    chunk = videos[start:end]
    user_id = str(
        update.callback_query.from_user.id if update.callback_query else update.effective_user.id
    )
    purchased = load_user_data().get(user_id, [])
    context.user_data['last_source'] = 'show_tutorials'
    if not chunk:
        return await show_tutorials(update, context, 0)

    kb = []
    for idx, v in enumerate(chunk, start=start):
        if idx in purchased:
            cb = f"watch_tutorials_{idx}"
            label = f"▶️ {v['title'][:25]}{'…' if len(v['title']) > 25 else ''}"
        else:
            cb = f"preview_{idx}"
            label = f"🛒 {v['title'][:25]}{'…' if len(v['title']) > 25 else ''}\n${v['price']}"
        kb.append([InlineKeyboardButton(label, callback_data=cb)])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"tutorials_page_{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"tutorials_page_{page + 1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_main_menu')])

    reply_markup = InlineKeyboardMarkup(kb)
    text = f"🎓 *Tutorials* (Page {page + 1}/{(total - 1) // ITEMS_PER_PAGE + 1})"

    # Case 1: From callback (edit)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            print("edit_message_text failed, sending new message:", e)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="Markdown",
                                           reply_markup=reply_markup)
    # Case 2: From /start or similar (send)
    elif update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def show_my_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    videos = load_videos()
    uid = str(query.from_user.id)
    purchased = load_user_data().get(uid, [])
    context.user_data['last_source'] = 'my_videos'
    if not purchased:
        await query.edit_message_text("🫤 You haven't purchased any videos.", reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data='back_to_main_menu')]]))
        return
    kb = []
    for idx in purchased:
        v = videos[idx]
        kb.append([InlineKeyboardButton(f"▶️ {v['title']}", callback_data=f"watch_tutorials_{idx}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_main_menu')])
    try:
        await query.edit_message_text("🎥 *Your Videos:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        print("edit_message_text failed, sending new message:", e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🎥 *Your Videos:*", parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(kb))


async def watch_tutorials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_")[2])
    videos = load_videos()
    vid = videos[idx]

    if context.user_data['last_source'] == 'my_videos':
        kb = [[InlineKeyboardButton("🔙 Back to My Videos", callback_data="back_to_my_videos")]]
    else:
        kb = [[InlineKeyboardButton("🔙 Back to Tutorials", callback_data="back_to_tutorials")]]
    reply_markup = InlineKeyboardMarkup(kb)

    try:
        # Try editing media (works only if the original message has media)
        await query.edit_message_media(
            media=InputMediaVideo(media=vid['file_id'], caption=f"🎬 {vid['title']}"),
            reply_markup=reply_markup
        )
    except Exception as e:
        # If failed (e.g., original message is text), delete and send new message
        print("Could not edit media, fallback to new message:", e)
        try:
            await query.message.delete()
        except Exception as del_err:
            print("Message deletion failed:", del_err)

        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=vid['file_id'],
            caption=f"🎬 {vid['title']}",
            reply_markup=reply_markup
        )


async def handle_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # query = update.callback_query
    # await query.answer()
    # idx = int(query.data.split("_")[2])
    # videos = load_videos()
    # vid = videos[idx]
    # data = load_user_data()
    # uid = str(query.from_user.id)
    # data.setdefault(uid, [])
    # if idx not in data[uid]:
    #     data[uid].append(idx)
    #     save_user_data(data)
    # await query.message.reply_video(video=vid['file_id'], caption=f"🎬 {vid['title']}")
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_")[2])
    videos = load_videos()
    vid = videos[idx]
    data = load_user_data()
    uid = str(query.from_user.id)

    # Save purchase if not already bought
    data.setdefault(uid, [])
    if idx not in data[uid]:
        data[uid].append(idx)
        save_user_data(data)

    kb = [[InlineKeyboardButton("🔙 Back to Main menu", callback_data="back_to_main_menu")]]
    reply_markup = InlineKeyboardMarkup(kb)

    try:
        # Try editing media (works only if the original message has media)
        await query.edit_message_media(
            media=InputMediaVideo(media=vid['file_id'], caption=f"🎬 {vid['title']}"),
            reply_markup=reply_markup
        )
    except Exception as e:
        pass


async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📤 Send the video file now.", reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Back", callback_data='back_cancel_upload')]]))
    return VIDEO


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        await update.message.reply_text("🚫 Upload cancelled. Please /start again.")
        return ConversationHandler.END
    context.user_data['file_id'] = update.message.video.file_id
    await update.message.reply_text("🎥 Received! Now send the title.", reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Back", callback_data='back_cancel_upload')]]))
    return TITLE


async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("🚫 Upload cancelled. Please /start again.")
        return ConversationHandler.END
    context.user_data['title'] = update.message.text.strip()
    await update.message.reply_text("📝 Title saved! Now send the price.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data='back_cancel_upload')]
    ]))
    return PRICE


async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
        videos = load_videos()
        videos.append({
            'file_id': context.user_data['file_id'],
            'title': context.user_data['title'],
            'price': price
        })
        save_videos(videos)
        await update.message.reply_text("✅ Video uploaded successfully!", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data='back_to_main_menu')]]))
    except:
        await update.message.reply_text("❌ Invalid price. Upload cancelled.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data='back_to_main_menu')]
        ]))
    return ConversationHandler.END


async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🚫 Upload cancelled.")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("🚫 Upload cancelled.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data='back_to_main_menu')]]))
    return ConversationHandler.END


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    admin_filter = filters.User(user_id=load_admins())
    # app.add_handler(MessageHandler(filters.PHOTO, debug_photo))

    app.add_handler(CommandHandler("start", main_menu))
    app.add_handler(CallbackQueryHandler(button_handler,
                                         pattern='^(tutorials_page_\d+|my_videos|help|back_to_tutorials|back_to_my_videos|preview_\d+|watch_tutorials_\d+|buy_video_\d+|back_to_main_menu)$'))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_upload, pattern='^upload_video$')],
        states={
            VIDEO: [MessageHandler(filters.VIDEO & admin_filter, receive_video)],
            TITLE: [MessageHandler(filters.TEXT & admin_filter, receive_title)],
            PRICE: [MessageHandler(filters.TEXT & admin_filter, receive_price)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_upload),
            CallbackQueryHandler(cancel_upload, pattern='^back_cancel_upload$')
        ]
    ))
    print("Bot running...")
    app.run_polling()
