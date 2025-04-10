import os

PORT = int(os.environ.get('PORT', 8443))
TOKEN = os.environ.get('BOT_TOKEN', 'SEU_TOKEN_AQUI')
APP_URL = os.environ.get('APP_URL', 'https://seu-app-no-render.onrender.com')  # sem / no final

def main():
    init_db()
    create_template()
    create_quiz_template()

    Thread(target=automatic_backup, daemon=True).start()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # ... (handlers como antes)

    dp.add_handler(CommandHandler('start', start))
    # outros handlers ...

    # Substitua polling por webhook
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{APP_URL}/{TOKEN}"
    )

    updater.idle()
