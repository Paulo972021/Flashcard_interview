import json
import os
from datetime import datetime
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)

# Estados da conversa
PERGUNTA, RESPOSTA, CATEGORIA, RECEBENDO_ARQUIVO = range(4)
ARQUIVO_FLASHCARDS = "flashcards.json"

# Utilitários de armazenamento por usuário
def carregar_todos_flashcards():
    if os.path.exists(ARQUIVO_FLASHCARDS):
        with open(ARQUIVO_FLASHCARDS, "r") as f:
            return json.load(f)
    return {}

def salvar_todos_flashcards(dados):
    with open(ARQUIVO_FLASHCARDS, "w") as f:
        json.dump(dados, f, indent=4, default=str)

def carregar_flashcards_usuario(user_id):
    dados = carregar_todos_flashcards()
    return dados.get(str(user_id), [])

def salvar_flashcards_usuario(user_id, flashcards):
    dados = carregar_todos_flashcards()
    dados[str(user_id)] = flashcards
    salvar_todos_flashcards(dados)

# Comandos principais
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Eu sou o seu bot de flashcards. Use /novo para criar um novo ou /backup para salvar seus dados.")

async def novo_flashcard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Digite a *pergunta* do flashcard:", parse_mode="Markdown")
    return PERGUNTA

async def receber_pergunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pergunta"] = update.message.text
    await update.message.reply_text("Agora digite a *resposta*:", parse_mode="Markdown")
    return RESPOSTA

async def receber_resposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["resposta"] = update.message.text
    await update.message.reply_text("Deseja adicionar uma *categoria* ou campo extra? (ou digite 'pular')")
    return CATEGORIA

async def receber_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categoria = update.message.text
    if categoria.lower() == 'pular':
        categoria = ""

    user_id = str(update.effective_user.id)
    flashcards = carregar_flashcards_usuario(user_id)
    flashcards.append({
        "pergunta": context.user_data["pergunta"],
        "resposta": context.user_data["resposta"],
        "categoria": categoria,
        "acertos": 0,
        "erros": 0,
        "ultima_revisao": str(datetime.today().date()),
        "periodicidade": 1
    })
    salvar_flashcards_usuario(user_id, flashcards)

    await update.message.reply_text("✅ Flashcard salvo com sucesso!")
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operacão cancelada.")
    return ConversationHandler.END

# Backup e restauração
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    flashcards = carregar_flashcards_usuario(user_id)

    if not flashcards:
        await update.message.reply_text("Você ainda não possui flashcards salvos.")
        return

    filename = f"flashcards_backup_{user_id}.json"
    with open(filename, "w") as f:
        json.dump(flashcards, f, indent=4, default=str)

    await update.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
    await update.message.reply_document(document=open(filename, "rb"), filename=filename,
        caption="🧠 Aqui está o seu backup. Guarde-o com segurança.")
    os.remove(filename)

async def restaurar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📎 Envie agora o arquivo `.json` de backup que deseja restaurar.")
    return RECEBENDO_ARQUIVO

async def receber_arquivo_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    document = update.message.document

    if not document.file_name.endswith(".json"):
        await update.message.reply_text("❌ Envie apenas arquivos com extensão `.json`.")
        return ConversationHandler.END

    file = await document.get_file()
    file_path = f"temp_restore_{user_id}.json"
    await file.download_to_drive(file_path)

    try:
        with open(file_path, "r") as f:
            dados = json.load(f)
        salvar_flashcards_usuario(user_id, dados)
        await update.message.reply_text("✅ Backup restaurado com sucesso!")
    except Exception:
        await update.message.reply_text("⚠️ Ocorreu um erro ao tentar restaurar seu backup.")
    finally:
        os.remove(file_path)

    return ConversationHandler.END

# Execução do bot
if __name__ == "__main__":
    import os
    TOKEN = os.getenv("TOKEN")
    
    app = ApplicationBuilder().token(TOKEN).build()

    conv_novo = ConversationHandler(
        entry_points=[CommandHandler("novo", novo_flashcard)],
        states={
            PERGUNTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_pergunta)],
            RESPOSTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_resposta)],
            CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_categoria)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    conv_restaurar = ConversationHandler(
        entry_points=[CommandHandler("restaurar", restaurar)],
        states={
            RECEBENDO_ARQUIVO: [MessageHandler(filters.Document.ALL, receber_arquivo_backup)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_novo)
    app.add_handler(conv_restaurar)
    app.add_handler(CommandHandler("backup", backup))

    print("Bot iniciado...")
    app.run_polling()
