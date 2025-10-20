import os
import io
import json
import chess
import chess.svg
import cairosvg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, CallbackContext

# Oyunları saklamak için dict
games = {}

# JSON dosyasıyla oyunları kaydet
def save_games():
    with open("games.json", "w") as f:
        json.dump({str(chat_id): {
            "board_fen": game["board"].fen(),
            "players": game["players"],
            "turn": game["turn"]
        } for chat_id, game in games.items()}, f)

# JSON dosyasından oyunları yükle
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
def send_board(update: Update, board, message):
    svg_data = chess.svg.board(board=board)
    png_data = cairosvg.svg2png(bytestring=svg_data)
    bio = io.BytesIO(png_data)
    bio.name = "board.png"
    bio.seek(0)
    update.message.reply_photo(photo=bio, caption=message)

# Inline butonlar: her hamle bir tuş
def generate_buttons(board):
    buttons = []
    for move in board.legal_moves:
        buttons.append([InlineKeyboardButton(move.uci(), callback_data=move.uci())])
    return InlineKeyboardMarkup(buttons)

# Başlangıç mesajı
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Merhaba! Satranç oynamak için /play yazın.")

# Oyunu başlat
def play(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in games:
        update.message.reply_text("Zaten aktif bir oyununuz var!")
        return

    board = chess.Board()
    games[chat_id] = {
        "board": board,
        "players": [update.message.from_user.id],
        "turn": 0  # Beyaz başlar
    }
    save_games()
    update.message.reply_text("Oyun başlatıldı! Rakibinizin /join ile katılmasını bekleyin.")

# Oyuna katıl
def join(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    if chat_id not in games:
        update.message.reply_text("Henüz oyun başlamadı, /play ile başlatın.")
        return

    game = games[chat_id]
    if len(game["players"]) >= 2:
        update.message.reply_text("Oyun zaten dolu!")
        return

    game["players"].append(user_id)
    save_games()
    send_board(update, game["board"], "Oyuna katıldınız! Beyaz oyuncu hamleye başladı.")

# Buton callback
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if chat_id not in games:
        query.answer("Oyun bulunamadı!")
        return

    game = games[chat_id]
    board = game["board"]

    # Sıra kontrolü
    if user_id != game["players"][game["turn"]]:
        query.answer("Sıra sizde değil!")
        return

    move_uci = query.data
    move = chess.Move.from_uci(move_uci)
    if move in board.legal_moves:
        board.push(move)
        save_games()  # Her hamleden sonra kaydet

        # Oyun bitiş kontrolü
        if board.is_checkmate():
            send_board(update, board, f"Şah mat! Kazanan: {'Beyaz' if game['turn']==0 else 'Siyah'}")
            del games[chat_id]
            save_games()
            return
        elif board.is_stalemate() or board.is_insufficient_material():
            send_board(update, board, "Oyun berabere!")
            del games[chat_id]
            save_games()
            return

        game["turn"] = 1 - game["turn"]

        # Mesajı güncelle
        query.edit_message_caption(
            caption=f"Hamle yapıldı! Sıradaki: {'Beyaz' if game['turn']==0 else 'Siyah'}",
            reply_markup=generate_buttons(board)
        )
        query.answer()
    else:
        query.answer("Geçersiz hamle!")

def main():
    load_games()  # Bot başlatıldığında kayıtlı oyunları yükle

    # Tokenı ortam değişkeninden al
    token = os.environ.get("7651843103:AAGiChGdicvHQ9LOhV_Pk0hhqaF4fAWaEVw")
    if not token:
        print("Lütfen TELEGRAM_TOKEN ortam değişkenini ayarlayın!")
        return

    app = ApplicationBuilder().token(token).build()

    # Komutlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CallbackQueryHandler(button))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
