import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = "8653503796:AAHUcha-iwJ7cbLR-imut-rAXU5lqwYcmkQ"
DB_FILE = "db.json"
ADMIN_PASSWORD = "6769"


# ---------------- ЗВАНИЯ ----------------
RANKS = [
    ("Новичок", 10),
    ("Молодец", 100),
    ("Крутой", 300),
    ("Мастер", 500),
    ("Элита", 1000),
    ("Грандмастер", 1500),
    ("Легенда", 2000),
    ("Администратор", 9999999999999),
]


# ---------------- БАЗА ----------------
def load_data():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ---------------- СООБЩЕНИЯ ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if update.message.chat.type == "private":
        return

    user = update.message.from_user
    chat_id = str(update.message.chat_id)
    user_id = str(user.id)

    data = load_data()

    if chat_id not in data:
        data[chat_id] = {}

    if user_id not in data[chat_id]:
        data[chat_id][user_id] = {
            "name": user.first_name,
            "money": 0,
            "messages": 0,
            "rank": "Без звания",
            "owned_ranks": [],
            "admin": False
        }

    u = data[chat_id][user_id]

    u.setdefault("rank", "Без звания")
    u.setdefault("owned_ranks", [])
    u.setdefault("admin", False)

    u["name"] = user.first_name
    u["money"] += 1
    u["messages"] += 1

    save_data(data)


# ---------------- /MY ----------------
async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    data = load_data()

    if chat_id not in data or user_id not in data[chat_id]:
        await update.message.reply_text("У тебя пока нет статистики 🤷‍♂️")
        return

    users = data[chat_id]
    sorted_users = sorted(users.items(), key=lambda x: x[1]["money"], reverse=True)

    place = next((i for i,(uid,_) in enumerate(sorted_users,1) if uid==user_id), 0)

    u = users[user_id]

    await update.message.reply_text(
        f"👤 Имя: {u['name']}\n"
        f"🏆 Место: {place}\n"
        f"💰 Деньги: {u['money']}$\n"
        f"💬 Сообщений: {u['messages']}\n"
        f"🎖 Звание: {u.get('rank','Без звания')}"
    )


# ---------------- /STATA ----------------
async def top_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    data = load_data()

    if chat_id not in data:
        await update.message.reply_text("Нет данных 🤷‍♂️")
        return

    users = data[chat_id]
    sorted_users = sorted(users.items(), key=lambda x: x[1]["money"], reverse=True)

    medals = ["🥇","🥈","🥉"]

    text = "🏆 ТОП:\n\n"

    for i,(uid,u) in enumerate(sorted_users[:10],1):
        medal = medals[i-1] if i<=3 else f"{i}."
        text += f"{medal} {u['name']} [{u.get('rank','Без звания')}] — {u['money']}$\n"

    await update.message.reply_text(text)


# ---------------- /INFO ----------------
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот экономики\n\n"
        "💬 +1$ за сообщение\n"
        "/my /stata /shop"
    )


# ---------------- /SHOP ----------------
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🏷 Магазин званий", callback_data="rank_shop")]]

    await update.message.reply_text(
        "🛒 Магазин:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- КНОПКИ ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "rank_shop":
        data = load_data()
        user_id = str(query.from_user.id)

        owned = []
        for chat_id in data:
            if user_id in data[chat_id]:
                owned = data[chat_id][user_id].get("owned_ranks", [])
                break

        keyboard = []

        for i,(name,price) in enumerate(RANKS):
            text = f"✅ {name}" if name in owned else f"{name} — {price}$"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"rank_{i}")])

        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="🏷 Магазин званий:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await query.message.reply_text("📩 Отправил в личные сообщения!")


async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    user_id = str(query.from_user.id)

    idx = int(query.data.split("_")[1])
    rank_name, price = RANKS[idx]

    for chat_id in data:
        if user_id in data[chat_id]:
            u = data[chat_id][user_id]
            u.setdefault("owned_ranks", [])

            if rank_name in u["owned_ranks"]:
                u["rank"] = rank_name
                save_data(data)
                await query.message.reply_text(f"🎖 Выбрано: {rank_name}")
                return

            if u["money"] < price:
                await query.message.reply_text("❌ Нет денег")
                return

            u["money"] -= price
            u["rank"] = rank_name
            u["owned_ranks"].append(rank_name)

            save_data(data)

            await query.message.reply_text(f"💸 Куплено: {rank_name}")
            return


# ---------------- /ADMIN (ЛС) ----------------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        await update.message.reply_text("❌ Только ЛС")
        return

    context.user_data["admin_login"] = True
    await update.message.reply_text("🔐 Введите пароль:")


async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    if not context.user_data.get("admin_login"):
        return

    if update.message.text == ADMIN_PASSWORD:
        user_id = str(update.message.from_user.id)
        data = load_data()

        for chat_id in data:
            if user_id in data[chat_id]:
                data[chat_id][user_id]["admin"] = True
                save_data(data)

                await update.message.reply_text("👑 Ты админ!")
                context.user_data["admin_login"] = False
                return

        await update.message.reply_text("❌ Сначала напиши в группе")
    else:
        await update.message.reply_text("❌ Неверный пароль")


# ---------------- /CHANGE ----------------
async def change_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return

    user_id = str(update.message.from_user.id)
    chat_id = str(update.message.chat_id)

    data = load_data()

    u = data.get(chat_id, {}).get(user_id)
    if not u or not u.get("admin"):
        await update.message.reply_text("❌ Нет прав")
        return

    arg = update.message.text.split(" ",1)
    if len(arg)<2:
        await update.message.reply_text("❌ /change <звание>")
        return

    u["rank"] = arg[1]
    save_data(data)

    await update.message.reply_text(f"👑 Звание: {arg[1]}")


# ---------------- /ADD ----------------
async def add_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return

    user_id = str(update.message.from_user.id)
    chat_id = str(update.message.chat_id)

    data = load_data()

    u = data.get(chat_id, {}).get(user_id)
    if not u or not u.get("admin"):
        await update.message.reply_text("❌ Нет прав")
        return

    arg = update.message.text.split(" ",1)
    if len(arg)<2 or not arg[1].isdigit():
        await update.message.reply_text("❌ /add <число>")
        return

    u["money"] += int(arg[1])
    save_data(data)

    await update.message.reply_text(f"➕ +{arg[1]}$")


# ---------------- /REMOVE ----------------
async def remove_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return

    user_id = str(update.message.from_user.id)
    chat_id = str(update.message.chat_id)

    data = load_data()

    u = data.get(chat_id, {}).get(user_id)
    if not u or not u.get("admin"):
        await update.message.reply_text("❌ Нет прав")
        return

    arg = update.message.text.split(" ",1)
    if len(arg)<2 or not arg[1].isdigit():
        await update.message.reply_text("❌ /remove <число>")
        return

    u["money"] -= int(arg[1])
    save_data(data)

    await update.message.reply_text(f"➖ -{arg[1]}$")
    
async def give_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        await update.message.reply_text("❌ Команда работает только в личных сообщениях")
        return

    user_id = str(update.message.from_user.id)
    data = load_data()

    found = False

    for chat_id in data:
        if user_id in data[chat_id]:
            data[chat_id][user_id]["admin"] = True
            found = True

    if not found:
        await update.message.reply_text("❌ Сначала напиши что-то в группе")
        return

    save_data(data)

    await update.message.reply_text("👑 Ты получил права администратора!")


# ---------------- ЗАПУСК ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.add_handler(CommandHandler("my", my_stats))
app.add_handler(CommandHandler("stata", top_stats))
app.add_handler(CommandHandler("info", info))
app.add_handler(CommandHandler("shop", shop))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("change", change_rank))
app.add_handler(CommandHandler("add", add_money))
app.add_handler(CommandHandler("remove", remove_money))
app.add_handler(CommandHandler("givemeanadmin", give_admin))

app.add_handler(CallbackQueryHandler(button_handler, pattern="rank_shop"))
app.add_handler(CallbackQueryHandler(buy_handler, pattern="rank_"))

app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, admin_password))

print("БОТ ЗАПУЩЕН...")

app.run_polling()