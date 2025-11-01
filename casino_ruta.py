#!/usr/bin/env python3
# casino_ruta_admin.py
# 🎰 Казино Рута — полный бот с админ-панелью (python-telegram-bot)
# Требует: python-telegram-bot==13.15
#
# Запуск:
# export BOT_TOKEN="8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A"
# python3 casino_ruta_admin.py

import os
import sys
import json
import time
import random
import logging
from typing import Dict, Any, Optional, Tuple, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    MessageEntity,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

# ---------------- Configuration ----------------
ADMIN_ID = 718853742  # <-- твой ID (админ)
DATA_FILE = "balances.json"
BACKUP_FILE = "balances_backup.json"
LOG_FILE = "casino_ruta.log"

MIN_BET = 100
MAX_BET = 5000
DAILY_BONUS = 1000
BONUS_SECONDS = 86400  # 24 hours

SLOT_SYMBOLS = ["🍒", "🍋", "💎", "⭐", "🍀", "7️⃣"]
ROULETTE_WIN_MULTIPLIER = 3
ROULETTE_WIN_CHANCE = 0.30  # 30%

# ---------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------- Token check ----------------
TOKEN = os.getenv("8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A")
if not TOKEN or ":" not in TOKEN:
    print("❌ Error: BOT_TOKEN env variable not set or invalid.")
    print('Set token with: export BOT_TOKEN="123456789:ABC-..."')
    sys.exit(1)

# ---------------- Data model ----------------
# data structure stored in JSON:
# {
#   "balances": { "<user_id>": int, ... },
#   "last_bonus": { "<user_id>": timestamp, ... },
#   "status": { "<user_id>": { "banned": bool, "frozen": bool } }
# }
data: Dict[str, Any] = {
    "balances": {},
    "last_bonus": {},
    "status": {}
}


def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # migrate keys if needed
                data.setdefault("balances", {})
                data.setdefault("last_bonus", {})
                data.setdefault("status", {})
        except Exception as e:
            logger.exception("Failed to load data file, trying backup: %s", e)
            if os.path.exists(BACKUP_FILE):
                try:
                    with open(BACKUP_FILE, "r", encoding="utf-8") as bf:
                        data = json.load(bf)
                except Exception:
                    data = {"balances": {}, "last_bonus": {}, "status": {}}
            else:
                data = {"balances": {}, "last_bonus": {}, "status": {}}
    else:
        data = {"balances": {}, "last_bonus": {}, "status": {}}


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # backup
        with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
            json.dump(data, bf, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Failed to save data")


def ensure_user(uid: int):
    k = str(uid)
    if k not in data["balances"]:
        data["balances"][k] = 1000
    if k not in data["status"]:
        data["status"][k] = {"banned": False, "frozen": False}
    save_data()


def get_balance(uid: int) -> int:
    return int(data["balances"].get(str(uid), 0))


def set_balance(uid: int, amount: int):
    data["balances"][str(uid)] = int(amount)
    save_data()


def change_balance(uid: int, delta: int):
    data["balances"][str(uid)] = int(data["balances"].get(str(uid), 0)) + int(delta)
    save_data()


def get_last_bonus(uid: int) -> float:
    return float(data["last_bonus"].get(str(uid), 0))


def set_last_bonus(uid: int, ts: float):
    data["last_bonus"][str(uid)] = ts
    save_data()


def get_status(uid: int) -> Dict[str, bool]:
    return data["status"].get(str(uid), {"banned": False, "frozen": False})


def set_status(uid: int, banned: Optional[bool] = None, frozen: Optional[bool] = None):
    key = str(uid)
    st = data["status"].get(key, {"banned": False, "frozen": False})
    if banned is not None:
        st["banned"] = bool(banned)
    if frozen is not None:
        st["frozen"] = bool(frozen)
    data["status"][key] = st
    save_data()


def format_top(n: int = 10) -> str:
    items = [(int(k), v) for k, v in data["balances"].items()]
    items.sort(key=lambda x: x[1], reverse=True)
    if not items:
        return "Пока нет игроков."
    lines = []
    for i, (uid, bal) in enumerate(items[:n], start=1):
        lines.append(f"{i}. `{uid}` — {bal} фишек")
    return "\n".join(lines)


# ---------------- Keyboards ----------------
def main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 100", callback_data="bet_100"),
         InlineKeyboardButton("💰 500", callback_data="bet_500"),
         InlineKeyboardButton("💎 1000", callback_data="bet_1000")],
        [InlineKeyboardButton("🎰 Слоты", callback_data="game_slots"),
         InlineKeyboardButton("🎯 Рулетка", callback_data="game_roulette")],
        [InlineKeyboardButton("💳 Баланс", callback_data="balance"),
         InlineKeyboardButton("🎁 Бонус", callback_data="bonus")],
        [InlineKeyboardButton("🔁 Перевод", callback_data="transfer"),
         InlineKeyboardButton("📊 Топ", callback_data="top")]
    ])
    if is_admin:
        kb.inline_keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")])
    return kb


def admin_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Начислить", callback_data="adm_add")],
        [InlineKeyboardButton("➖ Снять", callback_data="adm_remove")],
        [InlineKeyboardButton("🚫 Забанить", callback_data="adm_ban"),
         InlineKeyboardButton("✅ Разбанить", callback_data="adm_unban")],
        [InlineKeyboardButton("❄️ Заморозить", callback_data="adm_freeze"),
         InlineKeyboardButton("🔥 Разморозить", callback_data="adm_unfreeze")],
        [InlineKeyboardButton("♻️ Обнулить баланс", callback_data="adm_reset")],
        [InlineKeyboardButton("📋 Топ (100)", callback_data="adm_top")],
        [InlineKeyboardButton("📁 Экспорт данных", callback_data="adm_export")],
        [InlineKeyboardButton("🔙 Назад", callback_data="adm_back")]
    ])
    return kb


# ---------------- Handlers ----------------
def is_banned(uid: int) -> bool:
    return get_status(uid).get("banned", False)


def is_frozen(uid: int) -> bool:
    return get_status(uid).get("frozen", False)


def start_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    ensure_user(uid)
    kb = main_keyboard(is_admin=(uid == ADMIN_ID))
    text = (
        f"🎰 <b>Казино Рута</b>\n\n"
        f"Привет, {user.first_name}!\n"
        f"💰 Баланс: {get_balance(uid)} фишек\n\n"
        f"Играй через кнопки или командой /bet <сумма>.\n"
        f"Ежедневный бонус: /bonus (раз в 24 часа)."
    )
    update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


def balance_handler(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    ensure_user(uid)
    kb = main_keyboard(is_admin=(uid == ADMIN_ID))
    update.message.reply_text(f"💳 Твой баланс: {get_balance(uid)} фишек", reply_markup=kb)


def bonus_handler(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    ensure_user(uid)
    now = time.time()
    last = get_last_bonus(uid)
    if now - last < BONUS_SECONDS:
        remain_h = int((BONUS_SECONDS - (now - last)) // 3600)
        update.message.reply_text(f"⏳ Бонус уже взят. Приходи через ~{remain_h} ч.")
        return
    if is_banned(uid):
        update.message.reply_text("🚫 Вы забанены и не можете получать бонус.")
        return
    if is_frozen(uid):
        update.message.reply_text("❄️ Ваш аккаунт заморожен — операции ограничены.")
        return
    change_balance(uid, DAILY_BONUS)
    set_last_bonus(uid, now)
    update.message.reply_text(f"🎁 Вы получили {DAILY_BONUS} фишек! 💰 Баланс: {get_balance(uid)}")


def bet_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    ensure_user(uid)
    if is_banned(uid):
        update.message.reply_text("🚫 Вы забанены и не можете играть.")
        return
    if is_frozen(uid):
        update.message.reply_text("❄️ Ваш аккаунт заморожен — операции ограничены.")
        return

    args = context.args
    if not args:
        update.message.reply_text(f"Используй: /bet <сумма> (минимум {MIN_BET}, максимум {MAX_BET})")
        return
    try:
        amount = int(args[0])
    except:
        update.message.reply_text("❌ Неверная сумма.")
        return
    if amount < MIN_BET or amount > MAX_BET:
        update.message.reply_text(f"Ставка должна быть от {MIN_BET} до {MAX_BET}.")
        return
    if get_balance(uid) < amount:
        update.message.reply_text("❌ Недостаточно фишек.")
        return

    # choose random game based on context or default to slots simple logic:
    # We'll simulate a slots-like outcome:
    change_balance(uid, -amount)
    msg = update.message.reply_text("🎲 Крутим барабаны...")
    time.sleep(1.0)
    s1, s2, s3 = random.choices(SLOT_SYMBOLS, k=3)
    result = f"| {s1} | {s2} | {s3} |"
    if s1 == s2 == s3:
        win = amount * 5
        change_balance(uid, win)
        text = f"💎 Джекпот! Ты выиграл +{win} фишек!"
    elif s1 == s2 or s2 == s3 or s1 == s3:
        win = amount * 2
        change_balance(uid, win)
        text = f"⭐ 2 совпали! +{win} фишек!"
    else:
        text = f"💀 Увы, ничего не совпало. -{amount} фишек."
    msg.edit_text(f"🎰 {result}\n\n{text}\n\n💰 Баланс: {get_balance(uid)}")


def transfer_handler(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    ensure_user(uid)
    if is_banned(uid):
        update.message.reply_text("🚫 Вы забанены и не можете переводить.")
        return
    if is_frozen(uid):
        update.message.reply_text("❄️ Ваш аккаунт заморожен — операции ограничены.")
        return
    args = context.args
    if len(args) != 2:
        update.message.reply_text("📤 Пример: /transfer <user_id> <сумма>")
        return
    target, amount = args
    if not target.isdigit() or not amount.isdigit():
        update.message.reply_text("❌ Неверный формат.")
        return
    target_id = int(target)
    amt = int(amount)
    if amt < MIN_BET:
        update.message.reply_text(f"Минимальная сумма перевода {MIN_BET} фишек.")
        return
    if get_balance(uid) < amt:
        update.message.reply_text("❌ Недостаточно фишек.")
        return
    ensure_user(target_id)
    change_balance(uid, -amt)
    change_balance(target_id, amt)
    update.message.reply_text(f"💸 Переведено {amt} фишек пользователю `{target_id}`.\nБаланс: {get_balance(uid)}", parse_mode=ParseMode.MARKDOWN)
    try:
        context.bot.send_message(target_id, f"💸 Тебе перевели {amt} фишек от @{update.effective_user.username or update.effective_user.id}!")
    except Exception:
        # user may not accept messages from bot; ignore
        pass


def top_handler(update: Update, context: CallbackContext):
    update.message.reply_text(f"📊 Топ игроков:\n\n{format_top(10)}", parse_mode=ParseMode.MARKDOWN)


# ---------------- Callback (buttons) ----------------
def callback_query_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    uid = user.id
    data_cb = query.data
    logger.info("Callback from %s: %s", uid, data_cb)

    # quick bets
    if data_cb.startswith("bet_"):
        if is_banned(uid):
            query.answer("🚫 Ты забанен.")
            query.edit_message_text("🚫 Ты забанен.")
            return
        if is_frozen(uid):
            query.answer("❄️ Твой аккаунт заморожен.")
            query.edit_message_text("❄️ Твой аккаунт заморожен.")
            return
        amount = int(data_cb.split("_")[1])
        if get_balance(uid) < amount:
            query.answer("Недостаточно фишек.", show_alert=True)
            query.edit_message_text("❌ Недостаточно фишек.", reply_markup=main_keyboard(uid == ADMIN_ID))
            return
        change_balance(uid, -amount)
        query.edit_message_text("🎲 Крутим барабаны...", reply_markup=main_keyboard(uid == ADMIN_ID))
        time.sleep(1.0)
        s1, s2, s3 = random.choices(SLOT_SYMBOLS, k=3)
        result = f"| {s1} | {s2} | {s3} |"
        if s1 == s2 == s3:
            win = amount * 5
            change_balance(uid, win)
            text = f"💎 Джекпот! +{win} фишек!"
        elif s1 == s2 or s2 == s3 or s1 == s3:
            win = amount * 2
            change_balance(uid, win)
            text = f"⭐ 2 совпали! +{win} фишек!"
        else:
            text = f"💀 Проигрыш. -{amount} фишек."
        query.edit_message_text(f"🎰 {result}\n\n{text}\n\n💰 Баланс: {get_balance(uid)}", reply_markup=main_keyboard(uid == ADMIN_ID))
        query.answer()
        return

    # balance
    if data_cb == "balance":
        ensure_user(uid)
        query.edit_message_text(f"💳 Твой баланс: {get_balance(uid)} фишек", reply_markup=main_keyboard(uid == ADMIN_ID))
        query.answer()
        return

    # bonus
    if data_cb == "bonus":
        ensure_user(uid)
        now = time.time()
        last = get_last_bonus(uid)
        if now - last < BONUS_SECONDS:
            remain_h = int((BONUS_SECONDS - (now - last)) // 3600)
            query.edit_message_text(f"⏳ Бонус уже взят. Приходи через ~{remain_h} ч.", reply_markup=main_keyboard(uid == ADMIN_ID))
            query.answer()
            return
        if is_banned(uid):
            query.answer("🚫 Ты забанен.")
            query.edit_message_text("🚫 Ты забанен.")
            return
        if is_frozen(uid):
            query.answer("❄️ Твой аккаунт заморожен.")
            query.edit_message_text("❄️ Твой аккаунт заморожен.")
            return
        change_balance(uid, DAILY_BONUS)
        set_last_bonus(uid, now)
        query.edit_message_text(f"🎁 Ты получил {DAILY_BONUS} фишек!\n💰 Баланс: {get_balance(uid)}", reply_markup=main_keyboard(uid == ADMIN_ID))
        query.answer()
        return

    # transfer (interactive)
    if data_cb == "transfer":
        ensure_user(uid)
        waiting_text = "🔁 Введи ID пользователя, которому хочешь перевести фишки (или /cancel):"
        query.edit_message_text(waiting_text)
        context.user_data["transfer_state"] = "ask_id"
        query.answer()
        return

    # top
    if data_cb == "top":
        query.edit_message_text(f"📊 Топ игроков:\n\n{format_top(10)}", parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard(uid == ADMIN_ID))
        query.answer()
        return

    # games menu
    if data_cb == "game_slots":
        query.edit_message_text("🎰 Слоты — выбери ставку:", reply_markup=main_keyboard(uid == ADMIN_ID))
        query.answer()
        return
    if data_cb == "game_roulette":
        query.edit_message_text(
            "🎯 Рулетка — правила:\n"
            f"- Ставка через /bet <сумма> (минимум {MIN_BET}).\n"
            f"- Шанс победы ~{int(ROULETTE_WIN_CHANCE*100)}%: выигрыш ×{ROULETTE_WIN_MULTIPLIER}.",
            reply_markup=main_keyboard(uid == ADMIN_ID),
        )
        query.answer()
        return

    # admin panel
    if data_cb == "admin_panel":
        if uid != ADMIN_ID:
            query.answer("Нет доступа", show_alert=True)
            return
        query.edit_message_text("👑 Админ-панель — выбери действие:", reply_markup=admin_keyboard())
        query.answer()
        return

    # admin actions
    if data_cb in ("adm_add", "adm_remove", "adm_ban", "adm_unban", "adm_freeze", "adm_unfreeze", "adm_reset", "adm_top", "adm_export", "adm_back"):
        if uid != ADMIN_ID:
            query.answer("Нет доступа", show_alert=True)
            return
        if data_cb == "adm_add":
            context.user_data["admin_action"] = "add"
            query.edit_message_text("➕ Введи: <user_id> <amount> (например: 123456789 5000)")
            query.answer()
            return
        if data_cb == "adm_remove":
            context.user_data["admin_action"] = "remove"
            query.edit_message_text("➖ Введи: <user_id> <amount> (например: 123456789 500)")
            query.answer()
            return
        if data_cb == "adm_ban":
            context.user_data["admin_action"] = "ban"
            query.edit_message_text("🚫 Введи: <user_id> (будет забанен)")
            query.answer()
            return
        if data_cb == "adm_unban":
            context.user_data["admin_action"] = "unban"
            query.edit_message_text("✅ Введи: <user_id> (снимется бан)")
            query.answer()
            return
        if data_cb == "adm_freeze":
            context.user_data["admin_action"] = "freeze"
            query.edit_message_text("❄️ Введи: <user_id> (заморозить)")
            query.answer()
            return
        if data_cb == "adm_unfreeze":
            context.user_data["admin_action"] = "unfreeze"
            query.edit_message_text("🔥 Введи: <user_id> (разморозить)")
            query.answer()
            return
        if data_cb == "adm_reset":
            context.user_data["admin_action"] = "reset"
            query.edit_message_text("♻️ Введи: <user_id> (баланс будет обнулён)")
            query.answer()
            return
        if data_cb == "adm_top":
            query.edit_message_text(f"📋 Топ игроков:\n\n{format_top(100)}", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_keyboard())
            query.answer()
            return
        if data_cb == "adm_export":
            # export data file to admin as a file
            try:
                save_data()
                query.edit_message_text("📁 Экспорт данных: отправляю файл...")
                context.bot.send_document(ADMIN_ID, open(DATA_FILE, "rb"))
                query.answer("Файл отправлен")
            except Exception:
                logger.exception("Failed to send data file")
                query.answer("Ошибка при экспорте")
            return
        if data_cb == "adm_back":
            query.edit_message_text("Вернулись в главное меню.", reply_markup=main_keyboard(is_admin=True))
            query.answer()
            return

    # unknown callback
    query.answer()


# ---------------- Message handler for interactive flows ----------------
def text_message_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    txt = update.message.text.strip()

    # admin interactive actions
    if uid == ADMIN_ID and "admin_action" in context.user_data:
        action = context.user_data.pop("admin_action", None)
        parts = txt.split()
        if action in ("add", "remove"):
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip('-').isdigit():
                update.message.reply_text("Неверный формат. Используй: <user_id> <amount>")
                return
            target_id = int(parts[0]); amount = int(parts[1])
            ensure_user(target_id)
            if action == "add":
                change_balance(target_id, amount)
                update.message.reply_text(f"✅ Добавлено {amount} фишек пользователю `{target_id}`. Баланс: {get_balance(target_id)}", parse_mode=ParseMode.MARKDOWN)
                try:
                    context.bot.send_message(target_id, f"👑 Админ добавил тебе {amount} фишек!")
                except:
                    pass
            else:
                if get_balance(target_id) < amount:
                    update.message.reply_text("⚠️ У пользователя недостаточно фишек.")
                    return
                change_balance(target_id, -amount)
    
