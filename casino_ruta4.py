# вставь код ниже, сохрани Ctrl+O Enter, выйти Ctrl+X#!/usr/bin/env python3
# Casino Ruta 4.0 — полный бот для Termux (pyTelegramBotAPI)
# Требует: pyTelegramBotAPI
# Перед запуском: pip install pyTelegramBotAPI
# Вставь токен от BotFather в TOKEN

import os
import json
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List

import telebot
from telebot import types

# ---------- CONFIG ----------
TOKEN = "8509920661:AAF5-5hflC_ELoypc_By1HTOg3fgDXs8V1A"   # <-- Вставь сюда токен
ADMIN_ID = 718853742        # <-- твой ID админа (замени, если нужно)

DATA_FILE = "casino_data_v4.json"
BACKUP_FILE = "casino_data_v4_backup.json"
AUTOSAVE_INTERVAL = 60  # сек

MIN_BET = 100
MAX_BET = 50000
DAILY_BONUS = 1000
BONUS_SECONDS = 86400  # 24ч

SLOT_SYMBOLS = ["🍒","🍋","🍇","🍉","💎","7️⃣","🍀","⭐"]
SLOT_ANIM_SECONDS = 5
SLOT_ANIM_PERIOD = 1

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("casino_ruta")

# ---------- BOT ----------
if TOKEN == "" or TOKEN == "":
    print("ERROR: вставь токен в переменную TOKEN в файле casino_ruta4.py")
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# ---------- DATA MODEL ----------
# Structure:
# {
#   "users": {
#      "<id>": {
#          "balance": int,
#          "last_bonus": float,
#          "banned": bool,
#          "frozen": bool,
#          "wins": int,
#          "losses": int,
#          "games_played": int
#      }
#   },
#   "meta": {"created": ts}
# }

data: Dict[str, Any] = {"users": {}, "meta": {"created": time.time()}}

def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Loaded data from %s", DATA_FILE)
        except Exception as e:
            logger.exception("Failed to load data: %s", e)
            # try backup
            if os.path.exists(BACKUP_FILE):
                try:
                    with open(BACKUP_FILE, "r", encoding="utf-8") as bf:
                        data = json.load(bf)
                        logger.info("Loaded data from backup")
                except Exception:
                    data = {"users": {}, "meta": {"created": time.time()}}
            else:
                data = {"users": {}, "meta": {"created": time.time()}}
    else:
        data = {"users": {}, "meta": {"created": time.time()}}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(BACKUP_FILE, "w", encoding="utf-8") as bf:
            json.dump(data, bf, ensure_ascii=False, indent=2)
        logger.info("Data saved")
    except Exception:
        logger.exception("Failed to save data")

# autosave loop in background (lightweight)
_last_save = 0
def autosave_check():
    global _last_save
    if time.time() - _last_save > AUTOSAVE_INTERVAL:
        save_data()
        _last_save = time.time()

# ---------- USER HELPERS ----------
def ensure_user(uid: int):
    k = str(uid)
    if k not in data["users"]:
        data["users"][k] = {
            "balance": 1000,
            "last_bonus": 0.0,
            "banned": False,
            "frozen": False,
            "wins": 0,
            "losses": 0,
            "games_played": 0
        }
        save_data()

def get_user(uid: int) -> Dict[str, Any]:
    ensure_user(uid)
    return data["users"][str(uid)]

def get_balance(uid: int) -> int:
    return int(get_user(uid)["balance"])

def change_balance(uid: int, delta: int):
    u = get_user(uid)
    u["balance"] = int(u.get("balance", 0) + int(delta))
    save_data()

def set_balance(uid: int, amount: int):
    u = get_user(uid)
    u["balance"] = int(amount)
    save_data()

def set_status(uid: int, banned: Optional[bool]=None, frozen: Optional[bool]=None):
    u = get_user(uid)
    if banned is not None:
        u["banned"] = bool(banned)
    if frozen is not None:
        u["frozen"] = bool(frozen)
    save_data()

def can_play(uid: int) -> Tuple[bool, Optional[str]]:
    u = get_user(uid)
    if u.get("banned"):
        return False, "🚫 Вы забанены."
    if u.get("frozen"):
        return False, "❄️ Ваш аккаунт заморожен."
    return True, None

# ---------- UI ----------
def main_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎰 Слоты", "🎯 Рулетка", "🎲 Кости")
    kb.row("🎁 Бонус", "💰 Баланс", "📊 Топ")
    kb.row("💸 Перевести", "ℹ️ Помощь")
    return kb

def inline_bet_buttons(prefix: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💵 100", callback_data=f"{prefix}_bet_100"),
           types.InlineKeyboardButton("💰 500", callback_data=f"{prefix}_bet_500"),
           types.InlineKeyboardButton("💎 1000", callback_data=f"{prefix}_bet_1000"))
    kb.add(types.InlineKeyboardButton("🔙 Меню", callback_data="menu_back"))
    return kb

def admin_keyboard_inline():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Начислить", callback_data="adm_add"),
           types.InlineKeyboardButton("➖ Снять", callback_data="adm_remove"))
    kb.add(types.InlineKeyboardButton("🚫 Бан", callback_data="adm_ban"),
           types.InlineKeyboardButton("✅ Разбан", callback_data="adm_unban"))
    kb.add(types.InlineKeyboardButton("❄️ Заморозить", callback_data="adm_freeze"),
           types.InlineKeyboardButton("🔥 Разморозить", callback_data="adm_unfreeze"))
    kb.add(types.InlineKeyboardButton("♻ Обнулить", callback_data="adm_reset"),
           types.InlineKeyboardButton("📁 Экспорт", callback_data="adm_export"))
    kb.add(types.InlineKeyboardButton("🔙 Меню", callback_data="menu_back"))
    return kb

# ---------- UTILS ----------
def format_top(n=10) -> str:
    items = [(int(k), v["balance"]) for k, v in data["users"].items()]
    items.sort(key=lambda x: x[1], reverse=True)
    lines = []
    for i, (uid, bal) in enumerate(items[:n], start=1):
        lines.append(f"{i}. `{uid}` — {bal} фишек")
    return "\n".join(lines) if lines else "Пока нет игроков."

# ---------- HANDLERS ----------
@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    kb = main_keyboard()
    bot.send_message(m.chat.id, f"🎰 <b>Казино Рута 4.0</b>\nПривет, {m.from_user.first_name}!\n💰 Баланс: {get_balance(uid)} фишек",
                     reply_markup=kb, parse_mode="HTML")

@bot.message_handler(commands=["balance"])
def cmd_balance(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    bot.send_message(m.chat.id, f"💰 Твой баланс: {get_balance(uid)} фишек", reply_markup=main_keyboard())

@bot.message_handler(commands=["top"])
def cmd_top(m: types.Message):
    bot.send_message(m.chat.id, "📊 Топ игроков:\n\n"+format_top(10), parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(commands=["bonus"])
def cmd_bonus(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    now = time.time()
    last = get_user(uid).get("last_bonus", 0.0)
    if now - last < BONUS_SECONDS:
        rem = int((BONUS_SECONDS - (now - last))//3600)
        bot.send_message(m.chat.id, f"⏳ Бонус уже взят. Через ~{rem} ч.", reply_markup=main_keyboard()); return
    change_balance(uid, DAILY_BONUS)
    get_user(uid)["last_bonus"] = now
    save_data()
    bot.send_message(m.chat.id, f"🎁 Ты получил {DAILY_BONUS} фишек! Баланс: {get_balance(uid)}", reply_markup=main_keyboard())

# Transfers: /transfer <id> <amount> or interactive
@bot.message_handler(commands=["transfer"])
def cmd_transfer(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    parts = m.text.split()
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        target = int(parts[1]); amount = int(parts[2])
        if amount < MIN_BET:
            bot.send_message(m.chat.id, f"Минимум для перевода {MIN_BET} фишек"); return
        if get_balance(uid) < amount:
            bot.send_message(m.chat.id, "❌ Недостаточно фишек"); return
        ensure_user(target)
        change_balance(uid, -amount)
        change_balance(target, amount)
        bot.send_message(m.chat.id, f"✅ Перевёл {amount} фишек пользователю `{target}`\nБаланс: {get_balance(uid)}", parse_mode="Markdown", reply_markup=main_keyboard())
        try:
            bot.send_message(target, f"💸 Тебе перевели {amount} фишек от @{m.from_user.username or uid}")
        except:
            pass
        return
    bot.send_message(m.chat.id, "🔁 Введи ID получателя:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(m, transfer_step1)

def transfer_step1(m: types.Message):
    if not m.text or not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Неверный ID. Операция отменена.", reply_markup=main_keyboard()); return
    target = int(m.text)
    msg = bot.send_message(m.chat.id, "💰 Введи сумму:")
    bot.register_next_step_handler(msg, transfer_step2, target)

def transfer_step2(m: types.Message, target:int):
    if not m.text or not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Неверная сумма. Операция отменена.", reply_markup=main_keyboard()); return
    amount = int(m.text)
    uid = m.from_user.id
    if amount < MIN_BET:
        bot.send_message(m.chat.id, f"Минимум для перевода {MIN_BET} фишек", reply_markup=main_keyboard()); return
    if get_balance(uid) < amount:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек", reply_markup=main_keyboard()); return
    ensure_user(target)
    change_balance(uid, -amount)
    change_balance(target, amount)
    bot.send_message(m.chat.id, f"✅ Перевёл {amount} фишек пользователю `{target}`\nБаланс: {get_balance(uid)}", parse_mode="Markdown", reply_markup=main_keyboard())
    try:
        bot.send_message(target, f"💸 Тебе перевели {amount} фишек от @{m.from_user.username or uid}")
    except:
        pass

# ---------- SLOTS with animation ----------
def spin_slots_and_animate(chat_id:int, uid:int, amount:int, edit_message_id:Optional[int]=None):
    # Deduct bet upfront
    change_balance(uid, -amount)
    total_frames = SLOT_ANIM_SECONDS // SLOT_ANIM_PERIOD
    last_combo = None
    # Send or edit initial message
    if edit_message_id:
        try:
            bot.edit_message_text("🎰 Крутим барабаны...", chat_id, edit_message_id)
            msg_id = edit_message_id
        except:
            m = bot.send_message(chat_id, "🎰 Крутим барабаны...")
            msg_id = m.message_id
    else:
        m = bot.send_message(chat_id, "🎰 Крутим барабаны...")
        msg_id = m.message_id

    for i in range(total_frames):
        s1 = random.choice(SLOT_SYMBOLS)
        s2 = random.choice(SLOT_SYMBOLS)
        s3 = random.choice(SLOT_SYMBOLS)
        last_combo = (s1,s2,s3)
        frame = f"🎰 | {s1} | {s2} | {s3} |"
        try:
            bot.edit_message_text(frame, chat_id, msg_id)
        except Exception:
            # can't edit (maybe in groups) - send new message
            try:
                bot.send_message(chat_id, frame)
            except:
                pass
        time.sleep(SLOT_ANIM_PERIOD)
    # Final evaluate
    s1,s2,s3 = last_combo
    u = get_user(uid)
    u["games_played"] = u.get("games_played",0)+1
    if s1==s2==s3:
        win = amount * 5
        change_balance(uid, win)
        u["wins"] += 1
        result_text = f"💎 Джекпот! +{win} фишек!"
    elif s1==s2 or s2==s3 or s1==s3:
        win = amount * 2
        change_balance(uid, win)
        u["wins"] += 1
        result_text = f"⭐ 2 совпали! +{win} фишек!"
    else:
        u["losses"] = u.get("losses",0)+1
        result_text = f"💀 Проигрыш. -{amount} фишек."
    final = f"🎰 | {s1} | {s2} | {s3} |\n\n{result_text}\n\n💰 Баланс: {get_balance(uid)}"
    try:
        bot.edit_message_text(final, chat_id, msg_id, reply_markup=main_keyboard())
    except:
        bot.send_message(chat_id, final, reply_markup=main_keyboard())
    save_data()

@bot.message_handler(func=lambda m: m.text == "🎰 Слоты")
def show_slots_kb(m: types.Message):
    kb = inline_bet_buttons("slot")
    bot.send_message(m.chat.id, "Выберите ставку для слотов:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("slot_bet_"))
def on_slot_bet(call: types.CallbackQuery):
    uid = call.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.answer_callback_query(call.id, reason, show_alert=True)
        return
    amount = int(call.data.split("_")[-1])
    if amount < MIN_BET or amount > MAX_BET:
        bot.answer_callback_query(call.id, f"Ставка от {MIN_BET} до {MAX_BET}", show_alert=True)
        return
    if get_balance(uid) < amount:
        bot.answer_callback_query(call.id, "Недостаточно фишек", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    # Animate in same message
    try:
        spin_slots_and_animate(call.message.chat.id, uid, amount, edit_message_id=call.message.message_id)
    except Exception as e:
        logger.exception("Error spinning slots: %s", e)
        bot.send_message(call.message.chat.id, "Ошибка при игре.")

# ---------- ROULETTE ----------
@bot.message_handler(func=lambda m: m.text == "🎯 Рулетка")
def show_roulette_kb(m: types.Message):
    kb = inline_bet_buttons("roul")
    bot.send_message(m.chat.id, "Выберите ставку для рулетки (шанс ~30%, ×3):", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("roul_bet_"))
def on_roul_bet(call: types.CallbackQuery):
    uid = call.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.answer_callback_query(call.id, reason, show_alert=True)
        return
    amount = int(call.data.split("_")[-1])
    if amount < MIN_BET or amount > MAX_BET:
        bot.answer_callback_query(call.id, f"Ставка от {MIN_BET} до {MAX_BET}", show_alert=True); return
    if get_balance(uid) < amount:
        bot.answer_callback_query(call.id, "Недостаточно фишек", show_alert=True); return
    bot.answer_callback_query(call.id)
    change_balance(uid, -amount)
    u = get_user(uid)
    u["games_played"] = u.get("games_played",0)+1
    if random.random() < 0.30:
        win = amount * 3
        change_balance(uid, win)
        u["wins"] += 1
        bot.edit_message_text(f"🎉 Победа! +{win} фишек\n💰 Баланс: {get_balance(uid)}", call.message.chat.id, call.message.message_id, reply_markup=main_keyboard())
    else:
        u["losses"] = u.get("losses",0)+1
        bot.edit_message_text(f"💀 Проигрыш. -{amount} фишек\n💰 Баланс: {get_balance(uid)}", call.message.chat.id, call.message.message_id, reply_markup=main_keyboard())
    save_data()

# ---------- DICE ----------
@bot.message_handler(func=lambda m: m.text == "🎲 Кости")
def cmd_dice(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    roll = random.randint(1,6)
    u = get_user(uid)
    u["games_played"] = u.get("games_played",0)+1
    bot.send_message(m.chat.id, f"🎲 Выпало: {roll}", reply_markup=main_keyboard())
    save_data()

# ---------- GUESS NUMBER ----------
@bot.message_handler(func=lambda m: m.text == "🎯 Угадай число" or m.text and m.text.startswith("/guess"))
def start_guess(m: types.Message):
    msg = bot.send_message(m.chat.id, "Введите число от 1 до 5 (ставка фиксирована — 500 фишек, выигрыш +1500):")
    bot.register_next_step_handler(msg, finish_guess)

def finish_guess(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    ok, reason = can_play(uid)
    if not ok:
        bot.send_message(m.chat.id, reason); return
    if not m.text or not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Неверный ввод.", reply_markup=main_keyboard()); return
    choice = int(m.text)
    if choice < 1 or choice > 5:
        bot.send_message(m.chat.id, "Введите число 1–5", reply_markup=main_keyboard()); return
    stake = 500
    if get_balance(uid) < stake:
        bot.send_message(m.chat.id, "❌ Недостаточно фишек (нужны 500).", reply_markup=main_keyboard()); return
    # play
    change_balance(uid, -stake)
    num = random.randint(1,5)
    u = get_user(uid)
    u["games_played"] = u.get("games_played",0)+1
    if choice == num:
        win = 1500
        change_balance(uid, win)
        u["wins"] += 1
        bot.send_message(m.chat.id, f"🎯 Угадал! Было {num}. +{win} фишек\n💰 Баланс: {get_balance(uid)}", reply_markup=main_keyboard())
    else:
        u["losses"] = u.get("losses",0)+1
        bot.send_message(m.chat.id, f"😢 Неверно, было {num}. -{stake} фишек\n💰 Баланс: {get_balance(uid)}", reply_markup=main_keyboard())
    save_data()

# ---------- SIMPLE BUTTONS ----------
@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def btn_balance(m: types.Message):
    uid = m.from_user.id
    ensure_user(uid)
    bot.send_message(m.chat.id, f"💰 Твой баланс: {get_balance(uid)} фишек", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🎁 Бонус")
def btn_bonus(m: types.Message):
    cmd_bonus(m)  # просто вызываем существующую команду /bonus

@bot.message_handler(func=lambda m: m.text == "📊 Топ")
def btn_top(m: types.Message):
    cmd_top(m)  # вызываем /top

@bot.message_handler(func=lambda m: m.text == "💸 Перевести")
def btn_transfer(m: types.Message):
    cmd_transfer(m)  # вызываем /transfer

@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def btn_help(m: types.Message):
    text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "🎰 <b>Слоты</b> — три барабана, шанс на выигрыш ×5 или ×2.\n"
        "🎯 <b>Рулетка</b> — шанс 30%, выигрыш ×3.\n"
        "🎲 <b>Кости</b> — просто бросок для удовольствия.\n"
        "🎁 <b>Бонус</b> — ежедневные +1000 фишек.\n"
        "💸 <b>Перевести</b> — отправь фишки другу.\n"
        "\n👑 Админ панель: /admin (только для владельца)"
    )
    bot.send_message(m.chat.id, text, parse_mode="HTML", reply_markup=main_keyboard())

# ---------- ADMIN ----------
@bot.message_handler(commands=["admin"])
def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    kb = admin_keyboard_inline()
    bot.send_message(m.chat.id, "👑 Админ-панель", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_"))
def admin_cb(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Нет доступа", show_alert=True); return
    action = call.data.split("_",1)[1]
    bot.answer_callback_query(call.id)
    if action in ("add","remove"):
        msg = bot.send_message(call.message.chat.id, "Введите: <user_id> <amount>")
        bot.register_next_step_handler(msg, admin_add_remove, action)
    elif action in ("ban","unban","freeze","unfreeze","reset"):
        msg = bot.send_message(call.message.chat.id, "Введите: <user_id>")
        bot.register_next_step_handler(msg, admin_status_action, action)
    elif action == "export":
        save_data()
        try:
            bot.send_document(call.message.chat.id, open(DATA_FILE, "rb"))
        except Exception as e:
            logger.exception("Export error: %s", e)
            bot.send_message(call.message.chat.id, "Ошибка экспорта данных.")

def admin_add_remove(m: types.Message, action: str):
    if m.from_user.id != ADMIN_ID: return
    parts = m.text.strip().split()
    if len(parts)!=2 or not parts[0].isdigit() or not parts[1].lstrip('-').isdigit():
        bot.send_message(m.chat.id, "Неверный формат. Используй: <user_id> <amount>"); return
    target = int(parts[0]); amount = int(parts[1])
    ensure_user(target)
    if action=="add":
        change_balance(target, amount)
        bot.send_message(m.chat.id, f"✅ Добавлено {amount} фишек пользователю {target}. Баланс: {get_balance(target)}")
        try: bot.send_message(target, f"👑 Админ начислил вам {amount} фишек.")
        except: pass
    else:
        if get_balance(target) < amount:
            bot.send_message(m.chat.id, "У пользователя недостаточно фишек."); return
        change_balance(target, -amount)
        bot.send_message(m.chat.id, f"✅ Снято {amount} фишек у пользователя {target}. Баланс: {get_balance(target)}")
        try: bot.send_message(target, f"👑 Админ снял {amount} фишек с вашего баланса.")
        except: pass

def admin_status_action(m: types.Message, action: str):
    if m.from_user.id != ADMIN_ID: return
    if not m.text.strip().isdigit():
        bot.send_message(m.chat.id, "Неверный формат. Введи ID"); return
    target = int(m.text.strip())
    ensure_user(target)
    if action=="ban":
        set_status(target, banned=True); bot.send_message(m.chat.id, f"🚫 {target} забанен")
        try: bot.send_message(target, "🚫 Вы были забанены администратором.")
        except: pass
    elif action=="unban":
        set_status(target, banned=False); bot.send_message(m.chat.id, f"✅ {target} разбанен")

# ---------- RUN ----------
if __name__ == "__main__":
    load_data()
    print("🎰 Бот Казино Рута 4.0 запущен!")
    bot.infinity_polling()
