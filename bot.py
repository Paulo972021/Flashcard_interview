import os
import csv
import sqlite3
import shutil
import pandas as pd
from datetime import datetime, timedelta
from threading import Thread
from time import sleep
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Document
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, CallbackContext, ConversationHandler, CallbackQueryHandler)

# Estados da conversa
(ADD_QUESTION, ADD_ANSWER, SET_INTERVAL, SET_SUCCESS_MSG, SET_FAIL_MSG, REVIEW_ANSWER, UPLOAD_FILE) = range(7)

# Banco de dados local
DB_PATH = os.path.join("data", "flashcards.db")
BACKUP_PATH = os.path.join("data", "flashcards_backup.db")
TEMPLATE_PATH = os.path.join("data", "modelo_flashcards.xlsx")
os.makedirs("data", exist_ok=True)

# Exportação CSV
EXPORT_PATH = os.path.join("data", "flashcards_export.csv")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            interval INTEGER DEFAULT 1,
            success_msg TEXT DEFAULT 'Boa!',
            fail_msg TEXT DEFAULT 'Errou!',
            last_review TEXT,
            deck TEXT,
            category TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            flashcard_id INTEGER,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            FOREIGN KEY(flashcard_id) REFERENCES flashcards(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            last_review TEXT,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            interval INTEGER DEFAULT 1,
            success_msg TEXT DEFAULT 'Boa!',
            fail_msg TEXT DEFAULT 'Errou!',
            last_review TEXT,
            deck TEXT,
            category TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            flashcard_id INTEGER,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            FOREIGN KEY(flashcard_id) REFERENCES flashcards(id)
        )
    ''')
    conn.commit()
    conn.close()

def create_template():
    if not os.path.exists(TEMPLATE_PATH):
        df = pd.DataFrame(columns=["frente", "verso", "deck", "categoria"])
        df.to_excel(TEMPLATE_PATH, index=False)

def create_quiz_template():
    path = os.path.join("data", "modelo_quiz.xlsx")
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["pergunta", "resposta_certa", "alternativa_a", "alternativa_b", "alternativa_c", "alternativa_d"])
        df.to_excel(path, index=False)
    return path
    if not os.path.exists(TEMPLATE_PATH):
        df = pd.DataFrame(columns=["frente", "verso", "deck", "categoria"])
        df.to_excel(TEMPLATE_PATH, index=False)

def send_template(update: Update, context: CallbackContext):
    create_template()
    update.message.reply_document(document=open(TEMPLATE_PATH, 'rb'), filename='modelo_flashcards.xlsx')

def send_quiz_template(update: Update, context: CallbackContext):
    path = create_quiz_template()
    update.message.reply_document(document=open(path, 'rb'), filename='modelo_quiz.xlsx')
    create_template()
    update.message.reply_document(document=open(TEMPLATE_PATH, 'rb'), filename='modelo_flashcards.xlsx')

def backup_database():
    shutil.copyfile(DB_PATH, BACKUP_PATH)

def start(update: Update, context: CallbackContext):
    msg = (
        "👋 Bem-vindo ao seu bot local de Flashcards e Quizzes!\n\n"
        "📌 *Comandos disponíveis:*\n"
        "/add – Criar um novo flashcard manualmente\n"
        "/review – Revisar flashcards disponíveis\n"
        "/list – Listar todos os flashcards\n"
        "/delete <id> – Excluir um flashcard pelo ID\n"
        "/export – Exportar flashcards para CSV\n"
        "/backup – Gerar um backup do banco\n"
        "/upload – Enviar planilha com flashcards\n"
        "/modelo – Baixar template de flashcards\n"
        "/modelo_quiz – Baixar template de quizzes\n\n"
        "❗ Envie arquivos CSV ou Excel conforme os templates para importar dados corretamente."
    )
    update.message.reply_text(msg, parse_mode='Markdown')

def backup_command(update: Update, context: CallbackContext):
    backup_database()
    update.message.reply_document(document=open(BACKUP_PATH, 'rb'), filename='flashcards_backup.db')

def upload_command(update: Update, context: CallbackContext):
    update.message.reply_text("Envie o arquivo CSV ou Excel contendo as colunas: frente, verso, deck, categoria.")
    return UPLOAD_FILE

def handle_upload(update: Update, context: CallbackContext):
    file = update.message.document
    if not file:
        update.message.reply_text("Nenhum arquivo enviado.")
        return ConversationHandler.END

    file_path = os.path.join("data", file.file_name)
    file.get_file().download(file_path)

    inserted = 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        if file.file_name.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file.file_name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path)
        else:
            update.message.reply_text("Formato de arquivo não suportado. Envie um arquivo .csv ou .xlsx.")
            return ConversationHandler.END

        for _, row in df.iterrows():
            question = row.get('frente')
            answer = row.get('verso')
            deck = row.get('deck', '')
            category = row.get('categoria', '')
            if pd.notna(question) and pd.notna(answer):
                cur.execute('''
                    INSERT INTO flashcards (question, answer, deck, category)
                    VALUES (?, ?, ?, ?)
                ''', (question, answer, deck, category))
                flashcard_id = cur.lastrowid
                cur.execute('INSERT INTO scores (flashcard_id) VALUES (?)', (flashcard_id,))
                inserted += 1

        conn.commit()
        update.message.reply_text(f"{inserted} flashcards importados com sucesso.")
    except Exception as e:
        update.message.reply_text(f"Erro ao importar arquivo: {e}")
    finally:
        conn.close()

    return ConversationHandler.END

def add_flashcard(update: Update, context: CallbackContext):
    update.message.reply_text("Digite a pergunta (use | para separar campos se quiser):")
    return ADD_QUESTION

def save_question(update: Update, context: CallbackContext):
    context.user_data['question'] = update.message.text
    update.message.reply_text("Agora digite a resposta:")
    return ADD_ANSWER

def save_answer(update: Update, context: CallbackContext):
    context.user_data['answer'] = update.message.text
    update.message.reply_text("Intervalo de repetição (em dias):")
    return SET_INTERVAL

def set_interval(update: Update, context: CallbackContext):
    try:
        interval = int(update.message.text)
        context.user_data['interval'] = interval
        update.message.reply_text("Mensagem de sucesso personalizada:")
        return SET_SUCCESS_MSG
    except ValueError:
        update.message.reply_text("Por favor, digite um número inteiro.")
        return SET_INTERVAL

def set_success_msg(update: Update, context: CallbackContext):
    context.user_data['success_msg'] = update.message.text
    update.message.reply_text("Mensagem de erro personalizada:")
    return SET_FAIL_MSG

def set_fail_msg(update: Update, context: CallbackContext):
    context.user_data['fail_msg'] = update.message.text

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO flashcards (question, answer, interval, success_msg, fail_msg)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        context.user_data['question'],
        context.user_data['answer'],
        context.user_data['interval'],
        context.user_data['success_msg'],
        context.user_data['fail_msg']
    ))
    flashcard_id = cur.lastrowid
    cur.execute('INSERT INTO scores (flashcard_id) VALUES (?)', (flashcard_id,))
    conn.commit()
    conn.close()

    update.message.reply_text("Flashcard salvo com sucesso! Use /review para revisar depois.")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

def review(update: Update, context: CallbackContext):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, question, answer, interval, last_review FROM flashcards')
    cards = cur.fetchall()
    conn.close()

    now = datetime.now()
    for card in cards:
        fid, question, answer, interval, last_review = card
        if not last_review or datetime.strptime(last_review, "%Y-%m-%d") + timedelta(days=interval) <= now:
            context.user_data['review_card'] = {
                'id': fid,
                'question': question,
                'answer': answer
            }
            buttons = [[InlineKeyboardButton("Responder", callback_data=f"review_{fid}")]]
            update.message.reply_text(f"Pergunta:\n{question}", reply_markup=InlineKeyboardMarkup(buttons))

            return REVIEW_ANSWER

    update.message.reply_text("Nenhum flashcard disponível para revisão agora.")
    return ConversationHandler.END

def handle_review_response(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Digite a resposta:")
    return REVIEW_ANSWER

def check_review_answer(update: Update, context: CallbackContext):
    user_answer = update.message.text.strip().lower()
    card = context.user_data.get('review_card')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT success_msg, fail_msg FROM flashcards WHERE id = ?', (card['id'],))
    row = cur.fetchone()
    success_msg, fail_msg = row

    if user_answer == card['answer'].strip().lower():
        msg = success_msg
        cur.execute('UPDATE scores SET correct = correct + 1 WHERE flashcard_id = ?', (card['id'],))
        cur.execute('UPDATE flashcards SET last_review = ? WHERE id = ?', (datetime.now().strftime("%Y-%m-%d"), card['id']))
    else:
        msg = f"{fail_msg}\nResposta correta: {card['answer']}"

        cur.execute('UPDATE scores SET wrong = wrong + 1 WHERE flashcard_id = ?', (card['id'],))

    conn.commit()
    conn.close()
    update.message.reply_text(msg)
    return ConversationHandler.END

def list_flashcards(update: Update, context: CallbackContext):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, question FROM flashcards')
    cards = cur.fetchall()
    conn.close()

    if not cards:
        update.message.reply_text("Nenhum flashcard cadastrado.")
    else:
        msg = "Seus flashcards:\n" + "\n".join([f"ID {cid}: {q}" for cid, q in cards])


def delete_flashcard(update: Update, context: CallbackContext):
    try:
        fid = int(context.args[0])
    except (IndexError, ValueError):
        update.message.reply_text("Uso: /delete <id>")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM flashcards WHERE id = ?', (fid,))
    cur.execute('DELETE FROM scores WHERE flashcard_id = ?', (fid,))
    conn.commit()
    conn.close()

    update.message.reply_text(f"Flashcard ID {fid} removido.")

def export_flashcards(update: Update, context: CallbackContext):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT question, answer, interval, success_msg, fail_msg, last_review, deck, category FROM flashcards')
    cards = cur.fetchall()
    conn.close()

    if not cards:
        update.message.reply_text("Nenhum flashcard para exportar.")
        return

    with open(EXPORT_PATH, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Pergunta', 'Resposta', 'Intervalo', 'Sucesso', 'Erro', 'Última Revisão', 'Deck', 'Categoria'])
        writer.writerows(cards)

    update.message.reply_document(document=open(EXPORT_PATH, 'rb'), filename='flashcards_export.csv')

def automatic_backup(interval_minutes=60):
    while True:
        sleep(interval_minutes * 60)
        backup_database()

def main():
    init_db()
    create_template()
    create_quiz_template()

    Thread(target=automatic_backup, daemon=True).start()

    PORT = int(os.environ.get('PORT', 8443))
    TOKEN = os.environ.get('BOT_TOKEN', 'SEU_TOKEN_AQUI')
    APP_URL = os.environ.get('APP_URL', 'https://seu-app-no-render.onrender.com')

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_flashcard)],
        states={
            ADD_QUESTION: [MessageHandler(Filters.text & ~Filters.command, save_question)],
            ADD_ANSWER: [MessageHandler(Filters.text & ~Filters.command, save_answer)],
            SET_INTERVAL: [MessageHandler(Filters.text & ~Filters.command, set_interval)],
            SET_SUCCESS_MSG: [MessageHandler(Filters.text & ~Filters.command, set_success_msg)],
            SET_FAIL_MSG: [MessageHandler(Filters.text & ~Filters.command, set_fail_msg)],
            REVIEW_ANSWER: [MessageHandler(Filters.text & ~Filters.command, check_review_answer)],
            UPLOAD_FILE: [MessageHandler(Filters.document, handle_upload)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('review', review))
    dp.add_handler(CommandHandler('list', list_flashcards))
    dp.add_handler(CommandHandler('delete', delete_flashcard))
    dp.add_handler(CommandHandler('export', export_flashcards))
    dp.add_handler(CommandHandler('backup', backup_command))
    dp.add_handler(CommandHandler('upload', upload_command))
    dp.add_handler(CommandHandler('modelo', send_template))
    dp.add_handler(CommandHandler('modelo_quiz', send_quiz_template))
    dp.add_handler(CallbackQueryHandler(handle_review_response, pattern='^review_\d+$'))
    dp.add_handler(conv_handler)

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{APP_URL}/{TOKEN}"
    )

    updater.idle()

if __name__ == '__main__':
    main()
