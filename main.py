import io
import json
import chess
import chess.svg
import cairosvg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot tokenınızı buraya yazın (BotFather’dan aldığınız)
token = "7651843103:AAGiChGdicvHQ9LOhV_Pk0hhqaF4fAWaEVw"

# Oyun durumları
games = {}

# Oyunları kaydet
def save_games():
    with open("games.json", "w") as f:
        json.dump({str(chat_id): {
            "board_fen": game["board"].fen(),
            "players": game["players"],
            "turn": game["turn"]
        } for chat_id, game in games.items()}, f)

# Oyunları yükle
def load_games():
    global games
    try:
        with open("games.json", "r") as f:
            data = json.load(f)
            for chat_id, g in data.items():
                board = chess.Board(g["board_fen"])
                games[int(chat_id)] = {
                    "board": board,
                    "players": g["players"],
                    "turn": g["turn"]
                }
    except FileNotFoundError:
        games = {}

# Tahtayı görsel olarak gönder
async def send_board(update: Update, board, message):
    svg_data = chess.svg.board(board=board)
    png_data = cairosvg.svg2png(bytestring=svg_data)
    bio = io.BytesIO(png_data)
    bio.name = "board.png"
    bio.seek(0)
    await update.message.reply_photo(photo=bio, caption=message)

# Inline hamle butonları
def generate_buttons(board):
    buttons = []
    for move in board.legal_moves:
        buttons.append([InlineKeyboardButton(move.uci(), callback_data=move.uci())])
    return InlineKeyboardMarkup(buttons)

# Başlangıç mesajı
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Satranç oynamak için /play yazın.")

# Oyunu başlat
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id in games:
        await update.message.reply_text("Zaten aktif bir oyununuz var!")
        return

    board = chess.Board()
    games[chat_id] = {
        "board": board,
        "players": [update.message.from_user.id],
        "turn": 0
    }
    save_games()
    await update.message.reply_text("Oyun başlatıldı! Rakibinizin /join ile katılmasını bekleyin.")

# Oyuna katıl
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    if chat_id not in games:
        await update.message.reply_text("Henüz oyun başlamadı, /play ile başlatın.")
        return

    game = games[chat_id]
    if len(game["players"]) >= 2:
        await update.message.reply_text("Oyun zaten dolu!")
        return

    game["players"].append(user_id)
    save_games()
    await send_board(update, game["board"], "Oyuna katıldınız! Beyaz oyuncu hamleye başladı.")

# Hamle butonu
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if chat_id not in games:
        await query.edit_message_caption(caption="Oyun bulunamadı!")
        return

    game = games[chat_id]
    board = game["board"]

    if user_id != game["players"][game["turn"]]:
        await query.answer("Sıra sizde değil!")
        return

    move_uci = query.data
    move = chess.Move.from_uci(move_uci)
    if move in board.legal_moves:
        board.push(move)
        save_games()

        if board.is_checkmate():
            await query.edit_message_caption(caption=f"Şah mat! Kazanan: {'Beyaz' if game['turn']==0 else 'Siyah'}")
            del games[chat_id]
            save_games()
            return
        elif board.is_stalemate() or board.is_insufficient_material():
            await query.edit_message_caption(caption="Oyun berabere!")
            del games[chat_id]
            save_games()
            return

        game["turn"] = 1 - game["turn"]

        await query.edit_message_caption(
            caption=f"Hamle yapıldı! Sıradaki: {'Beyaz' if game['turn']==0 else 'Siyah'}",
            reply_markup=generate_buttons(board)
        )
    else:
        await query.answer("Geçersiz hamle!")

# Botu başlat
def main():
    load_games()
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CallbackQueryHandler(button))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
