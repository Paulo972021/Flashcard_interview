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
    update.message.reply_text("Bem-vindo ao seu bot local de flashcards! Use /add para criar, /review para revisar, /list para listar, /export para exportar, /delete <id> para excluir, /backup para salvar uma cópia do banco, /upload para importar uma planilha, ou /modelo para baixar o template.")

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
