# 🤖 FlashcardBot - Telegram Flashcards com Backup e Restauração

Bot para criar e revisar flashcards via Telegram, com salvamento local, backup manual e suporte a restauração.

## Funcionalidades

- Criação de flashcards com categoria
- Salvamento por usuário
- Backup local por comando
- Restauração a partir de arquivo JSON
- Pronto para deploy no Render

## Comandos

- `/start` — Inicia o bot
- `/novo` — Cria novo flashcard
- `/backup` — Gera e envia backup JSON
- `/restaurar` — Restaura a partir de backup JSON enviado

## Deploy no Render

1. Crie um repositório no GitHub com este projeto
2. Vá para [https://render.com](https://render.com)
3. Crie um novo serviço Web
4. Escolha seu repositório
5. Configure:
   - **Start command:** `python bot.py`
   - **Environment:** Python 3.10+
   - **Secret environment variable:** `TOKEN` com seu token do BotFather

Pronto! O bot ficará online 24/7.
