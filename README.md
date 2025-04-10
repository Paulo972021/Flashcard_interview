# Flashcard Bot para Telegram 📚

Um bot de Telegram com suporte a flashcards e quizzes, totalmente local, com armazenamento em SQLite.

## Funcionalidades
- Criar flashcards com frente/verso, deck e categoria
- Criar quizzes com múltiplas alternativas
- Revisões com base em periodicidade
- Importação de planilhas `.csv` ou `.xlsx`
- Backup automático do banco
- Painel de desempenho (em desenvolvimento)

## Deploy no Render

### Pré-requisitos:
- Conta no [Render](https://render.com/)
- Repositório no GitHub com este código

### Variáveis de Ambiente:
- `BOT_TOKEN`: Token do seu bot no Telegram
- `APP_URL`: URL pública fornecida pelo Render (ex: `https://seubot.onrender.com`)

### Passos:
1. Faça fork ou clone deste repositório.
2. Configure o deploy no Render como **Web Service**.
3. Use `render.yaml` para configuração automática.
4. O serviço iniciará com webhook e será acessado automaticamente pelo Telegram.

## Templates
Use os comandos:
- `/modelo` – Baixa o modelo para flashcards
- `/modelo_quiz` – Baixa o modelo para quizzes

---
