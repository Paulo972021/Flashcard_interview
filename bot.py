from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
import json
import os
from datetime import datetime, timedelta

# Estado da conversa
PERGUNTA, RESPOSTA, CATEGORIA = range(3)

# Banco de dados simples
ARQUIVO_FLASHCARDS = "flashcards.json"

def carregar_flashcards():
    if os.path.exists(ARQUIVO_FLASHCARDS):
        with open(ARQUIVO_FLASHCARDS, "r") as f:
            return json.load(f)
    return []

def salvar_flashcards(flashcards):
    with open(ARQUIVO_FLASHCARDS, "w") as f:
        json.dump(flashcards, f, indent=4, default=str)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Sou seu bot de flashcards. Use /novo para criar um.")

async def novo_flashcard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Digite a *pergunta* do flashcard:", parse_mode="Markdown")
    return PERGUNTA

async def receber_pergunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pergunta"] = update.message.text
    await update.message.reply_text("Agora envie a *resposta*:")
    return RESPOSTA

async def receber_resposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["resposta"] = update.message.text
    await update.message.reply_text("Deseja adicionar uma *categoria* ou campo extra? (ou digite 'pular')")
    return CATEGORIA

async def receber_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categoria = update.message.text
    if categoria.lower() == 'pular':
        categoria = ""
    flashcards = carregar_flashcards()
    flashcards.append({
        "pergunta": context.user_data["pergunta"],
        "resposta": context.user_data["resposta"],
        "categoria": categoria,
        "acertos": 0,
        "erros": 0,
        "ultima_revisao": str(datetime.today().date()),
        "periodicidade": 1
    })
    salvar_flashcards(flashcards)
    await update.message.reply_text("✅ Flashcard salvo com sucesso!")
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Criação de flashcard cancelada.")
    return ConversationHandler.END

if __name__ == "__main__":
    import os
    TOKEN = "8176143836:AAHqMdCksKID2mu_WHDmQsAJdDe8J8OUb_Y"

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("novo", novo_flashcard)],
        states={
            PERGUNTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_pergunta)],
            RESPOSTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_resposta)],
            CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_categoria)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    app.run_polling()
