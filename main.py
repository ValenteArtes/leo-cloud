import asyncio
import os
import threading
import base64
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agent import process_message, transcribe_audio, synthesize_speech
from telemetry import send_telemetry

# --- DUMMY SERVER PARA O RENDER FICAR FELIZ E LIBERAR O PLANO FREE ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running on Render Free Tier!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()
# ----------------------------------------------------------------------

# Token fornecida pelo usuario (usa variavel de ambiente no Render, hardcoded como fallback local)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Trava de Segurança: Só responde ao Dono (João Batista por padrao). Se for 0, responde a todos.
AUTHORIZED_USER_ID = int(os.environ.get("OWNER_TELEGRAM_ID", 7916905627))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if AUTHORIZED_USER_ID != 0 and update.effective_chat.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Acesso negado. Essa não é a minha senha de criador.")
        return
        
    print(f"[DEBUG] Comando /start recebido de {update.effective_chat.id}")
    
    # Coleta a URL da máquina do cliente para o João colocar no UptimeRobot
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "Local ou não configurada")
    send_telemetry("Novo Cadastro de Cliente", f"ID Telegram: {update.effective_chat.id}\n🌐 URL para o Despertador: {render_url}")
    
    msg_boas_vindas = "Olá! Eu sou seu auxiliar multitarefas.\nGostaria de saber um pouquinho sobre você, seu trabalho e rotinas para que, dessa forma, possa melhor me moldar à sua rotina e te ajudar a otimizar tarefas."
    await update.message.reply_text(msg_boas_vindas)

import re

async def deliver_response(context, chat_id, text):
    # Procura pela Tag Mestra Vinda do Agent OpenRouter de Arquivo Fisico
    file_match = re.search(r'<FILE_GENERATED>\s*(.*?)\s*</FILE_GENERATED>', text)
    if file_match:
        filepath = file_match.group(1).strip()
        text = text.replace(file_match.group(0), "")
        
        if text.strip():
            await context.bot.send_message(chat_id=chat_id, text=text.strip())
            
        try:
            with open(filepath, 'rb') as f:
                await context.bot.send_document(chat_id=chat_id, document=f)
            os.remove(filepath) # Exclui para nao lotar datacenter
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"[!] O arquivo falhou fisicamente: {e}")
    else:
        await context.bot.send_message(chat_id=chat_id, text=text)

async def daily_motivation(context: ContextTypes.DEFAULT_TYPE):
    from agent import process_message
    
    chat_id_str = os.environ.get("MASTER_CHAT_ID", "0")
    if not chat_id_str.isdigit() or chat_id_str == "0":
        print("[!] CronJob abortado: MASTER_CHAT_ID invalido.")
        return
        
    chat_id = int(chat_id_str)
    print(f"[*] Disparando Bom Dia Proativo para o CEO (ID: {chat_id})...")
    
    prompt = (
        "ISSO É UM EVENTO AUTOMÁTICO DE NUVEM (SEU CRON JOB de despertar ativou). "
        "1. Dê 'Bom dia, Mestre!' e avise que o dia já começou com poder total. "
        "2. Cite uma frase famosa intensa e motivadora sobre vitória, construção e persistência. "
        "3. Lembre-o com clareza dos dois combinados inquebráveis do dia: [Teto de Gastos Domésticos Limitado: R$ 50,00] e [Carga Nutricional Liberada: Máximo 2000 Calorias]. "
        "4. Finalmente, conclua PERGUNTANDO ao usuário se ele deseja que você faça a Leitura e Revisão da Agenda dele para o DIA DE HOJE agora!"
    )
    
    try:
        response = await process_message(prompt, chat_id)
        await deliver_response(context, chat_id, response)
    except Exception as e:
        print(f"[!] Falha na mensagem de Bom Dia: {e}")

async def afternoon_agenda(context: ContextTypes.DEFAULT_TYPE):
    from agent import process_message
    
    chat_id_str = os.environ.get("MASTER_CHAT_ID", "0")
    if not chat_id_str.isdigit() or chat_id_str == "0":
        return
        
    chat_id = int(chat_id_str)
    print(f"[*] Disparando Lembrete Pos-Almoco para o CEO...")
    
    prompt = (
        "ISSO É UM EVENTO AUTOMÁTICO DE NUVEM (SEU CRON JOB PÓS-ALMOÇO). OBRIGATÓRIO: 1. Acione imediatamente sua ferramenta 'read_from_sheet' para ler a aba 'Agenda' da nossa Planilha. 2. Varra todas as linhas lidas procurando os compromissos marcados para a 'DATA DE HOJE'. 3. Escreva um alerta rápido e focado pro chefe no estilo: 'Mestre, espero que o almoço tenha sido excelente! Só passando para não te deixar esquecer os compromissos da tarde/de hoje: [liste os horários]'. Se não achar nada pra hoje, diga de forma alegre que ele está livre de burocracias pelo resto do dia."
    )
    
    try:
        response = await process_message(prompt, chat_id)
        await deliver_response(context, chat_id, response)
    except Exception as e:
        print(f"[!] Falha na mensagem de Tarde: {e}")

async def nightly_agenda(context: ContextTypes.DEFAULT_TYPE):
    from agent import process_message
    
    chat_id_str = os.environ.get("MASTER_CHAT_ID", "0")
    if not chat_id_str.isdigit() or chat_id_str == "0":
        return
        
    chat_id = int(chat_id_str)
    print(f"[*] Disparando Analise Noturna de Agenda para o CEO...")
    
    prompt = (
        "ISSO É UM EVENTO AUTOMÁTICO DE NUVEM (SEU CRON JOB DE BOA NOITE DE AGENDA). OBRIGATÓRIO: 1. Acione imediatamente sua ferramenta 'read_from_sheet' para ler a aba 'Agenda' da nossa Planilha padrão. 2. Varra todas as linhas lidas procurando os compromissos marcados especificamente para a 'DATA DE AMANHÃ'. 3. Escreva um resumo detalhado para o Chefe listando os horários e tarefas (ex: 'Amanhã você tem médico às 7:00h, natação às 11:30h...'). Se não achar nada pra amanhã, diga de forma aliviada que o dia está livre. 4. Encerre desejando uma Excelente Noite de sono."
    )
    
    try:
        response = await process_message(prompt, chat_id)
        await deliver_response(context, chat_id, response)
    except Exception as e:
        print(f"[!] Falha na mensagem de Boa Noite: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if AUTHORIZED_USER_ID != 0 and chat_id != AUTHORIZED_USER_ID:
        return # Ignore silenciosamente estranhos
        
    text = update.message.text
    print(f"[DEBUG] Mensagem recebida: {text}")
    
    # Send a typing action because even fast APIs take half a second
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    response = await process_message(text, chat_id)
    await deliver_response(context, chat_id, response)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if AUTHORIZED_USER_ID != 0 and chat_id != AUTHORIZED_USER_ID:
        return

    # User can send a photo with or without text
    text = update.message.caption or "Analise os detalhes desta imagem cuidadosamente."
    print(f"[DEBUG] Foto recebida. Caption: {text}")
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        # Pega a foto em melhor qualidade
        photo_file = await update.message.photo[-1].get_file()
        file_path = f"temp_photo_{chat_id}.jpg"
        await photo_file.download_to_drive(file_path)
        
        with open(file_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        os.remove(file_path)
        
        response = await process_message(text, chat_id, base64_image=base64_image)
        await deliver_response(context, chat_id, response)
        
    except Exception as e:
        print(f"[!] Erro ao processar foto: {e}")
        await update.message.reply_text("Desculpe, tive um tropeço ao tentar processar esta imagem.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if AUTHORIZED_USER_ID != 0 and chat_id != AUTHORIZED_USER_ID:
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

    # Programa o despertador para as 08:00 no Brasil (11:00 em Greenwich/UTC)
    time_8am = datetime.time(hour=11, minute=0, tzinfo=datetime.timezone.utc)
    app.job_queue.run_daily(daily_motivation, time_8am)
    
    # Programa o Lembrete Pós-Almoço para 13:00 no Brasil (16:00 UTC)
    time_1pm = datetime.time(hour=16, minute=0, tzinfo=datetime.timezone.utc)
    app.job_queue.run_daily(afternoon_agenda, time_1pm)
    
    # Programa a Agenda Noturna para as 21:00 no Brasil (00:00 UTC)
    time_9pm = datetime.time(hour=0, minute=0, tzinfo=datetime.timezone.utc)
    app.job_queue.run_daily(nightly_agenda, time_9pm)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Iniciando servidor fantasma na porta 10000 para plano Free...")
    threading.Thread(target=run_dummy_server, daemon=True).start()

    print("Bot está rodando! Pressione Ctrl+C para parar.")
    app.run_polling()

if __name__ == "__main__":
    main()
