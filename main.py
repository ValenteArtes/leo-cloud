import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agent import process_message, transcribe_audio, synthesize_speech

# Token fornecido pelo usuario (usa variavel de ambiente no Render, hardcoded como fallback local)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7571564726:AAFW5sQKdwfRlM8LRHNxDxqNZmuHj7glUQo")

# Trava de Segurança: Só responde ao Dono (João Batista)
AUTHORIZED_USER_ID = 7916905627

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Acesso negado. Eu sirvo apenas ao meu criador.")
        return
        
    print(f"[DEBUG] Comando /start recebido de {update.effective_chat.id}")
    await update.message.reply_text("Olá, mestre! Sou o Léo, seu assistente na nuvem. Identificador de voz e perfil confirmados. Estou pronto para ajudar.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_USER_ID:
        return # Ignore silenciosamente estranhos
        
    text = update.message.text
    print(f"[DEBUG] Mensagem recebida: {text}")
    
    # Send a typing action because even fast APIs take half a second
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    response = await process_message(text, chat_id)
    await update.message.reply_text(response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id != AUTHORIZED_USER_ID:
        return # Ignore silenciosamente audios de estranhos
        
    # Send recording audio action
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        # Pega o arquivo de voz do Telegram
        voice_file = await update.message.voice.get_file()
        file_path = f"temp_voice_{chat_id}.ogg"
        await voice_file.download_to_drive(file_path)
        
        # Transcreve usando Whisper
        transcribed_text = await transcribe_audio(file_path)
        
        # Apaga o arquivo temporario
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if not transcribed_text:
            await update.message.reply_text("Desculpe, mestre. Eu ouvi o áudio mas não consegui entender nenhuma palavra.")
            return
            
        # Opcional: Mostra o que o robo entendeu do audio
        # await update.message.reply_text(f"*(Ouvi: {transcribed_text})*", parse_mode='Markdown')
        
        # Envia o texto pra mente Llama 3
        response_text = await process_message(transcribed_text, chat_id)
        
        # Envia a acao de 'Gravando audio' no Telegram
        await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
        
        # Gera o audio com a voz do Leo
        audio_file = await synthesize_speech(response_text, chat_id)
        
        if audio_file and os.path.exists(audio_file):
            # Responde com o audio
            with open(audio_file, 'rb') as voice:
                await update.message.reply_voice(voice=voice)
            # Apaga o audio gerado para limpar espaco
            os.remove(audio_file)
        else:
            # Fallback se der erro na voz, manda por texto
            await update.message.reply_text(response_text)
        
    except Exception as e:
        print(f"[!] Erro ao processar voz: {e}")
        await update.message.reply_text("Tive um problema ao processar o seu áudio.")

def main():
    if TELEGRAM_TOKEN == "":
        print("[!] ATENÇÃO: Insira seu TELEGRAM_TOKEN no main.py antes de iniciar o bot.")
        return
        
    print("Iniciando o Bot do Léo na Nuvem...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("Bot está rodando! Pressione Ctrl+C para parar.")
    app.run_polling()

if __name__ == "__main__":
    main()
