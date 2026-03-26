import os
from groq import AsyncGroq
import edge_tts
import json
from tools.sheets import append_to_sheet, read_from_sheet
from tools.search import perform_web_search
from tools.document import generate_document
from tools.pdf_maker import generate_pdf_quote
from tools.payments import generate_payment_link
from telemetry import send_telemetry

# Chaves de IA Híbrida 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")
AGENT_NAME = os.environ.get("AGENT_NAME", "Léo")
AGENT_VOICE = os.environ.get("AGENT_VOICE", "pt-BR-AntonioNeural")

# Utilizando cliente Groq fixo para transcrição de áudio e fallback
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# Se o usuário definir o OpenRouter, ativamos o cérebro avançado (Claude / Gemini)
llm_client = groq_client
if OPENROUTER_API_KEY:
    try:
        from openai import AsyncOpenAI
        llm_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
    except ImportError:
        print("[!] OpenAI SDK não instalado, fallback para Groq")


# Dict para guardar o contexto de conversa por chat_id
user_histories = {}

async def process_message(user_text: str, chat_id: int, base64_image: str = None) -> str:
    """Envia o texto (e opcionalmente foto) do usuario para o LLM via OpenRouter e retorna a resposta."""
    
    import datetime
    agora = datetime.datetime.now() - datetime.timedelta(hours=3)
    data_hora_atual = agora.strftime("%A, %d/%m/%Y %H:%M:%S")

    prompt_mestre = (
        f"DATA E HORA ATUAL DO SISTEMA: {data_hora_atual} (Horário de Brasília). Use este relógio como verdade absoluta para não repetir tarefas vencidas. "
        f"Seu nome é {AGENT_NAME}. Você é um assistente pessoal ultra-rápido operando no Telegram. "
        f"Responda em português do Brasil de forma direta. "
        f"DIRETRIZ DE PERSONALIDADE: Você é um Arquiteto de Software Sênior altamente lógico, objetivo e direto. SEM EMOJIS. Seja clínico. "
        f"DIRETRIZ DE MEMÓRIA DE DADOS: O link da Planilha padrão do seu Mestre João é: `https://docs.google.com/spreadsheets/d/1yem69FdQaffZ71mEhzmp5K_kwr6lP-QaBcZWQElpgDw/edit?hl=pt-PT&gid=0#gid=0`. A aba financeira é 'Página1'. "
        f"DIRETRIZ NUTRICIONAL: Quando mandarem foto de COMIDA, ative Modo Nutricionista. 1. Analise as calorias. 2. Leia a aba 'Nutricao' da Planilha e SOME as calorias de TUDO o que eles já comeram na DATA DE HOJE ({data_hora_atual}). 3. Salve com 'append_to_sheet'. 4. Faça resumo da meta de 2000 cal. "
        f"DIRETRIZ FINANCEIRA: Ao relatar gastos, decida aba 'Domestica' ou 'Negocios'. Leia o salto com 'read_from_sheet' e salve com 'append_to_sheet' anotando a data e detalhes. "
        f"DIRETRIZ DE AGENDA EXATA (MUITO IMPORTANTE): Quando o Mestre pedir para agendar compromissos, É OBRIGATÓRIO perguntar e confirmar a DATA EXATA (dia e mês) e o HORÁRIO antes de agendar se ele não tiver especificado na mesma frase. "
        f"1. Uma vez com os dados, acione 'append_to_sheet' na aba 'Agenda' para salvar [Data Exata, Horário, Compromisso]. "
        f"2. TAREFAS VENCIDAS: Sempre que ler a aba Agenda com 'read_from_sheet', você verá um histórico longo. Mude a sua atenção APENAS para eventos agendados para HOJE ou FUTURO. Compromissos onde a data já passou do dia de hoje ({data_hora_atual}) são dados mortos arquivados, jamais fale deles ou repita avisos deles. "
        f"DIRETRIZ DE LOMBO MULTIMODAL: Você possui olhos Gemini Flash ativos. "
        f"DIRETRIZ DE SEGURANÇA MÁXIMA E ARQUIVOS: NUNCA mostre tags <function> ou JSON na resposta textual do Telegram. "
    )
    
    if chat_id not in user_histories:
        user_histories[chat_id] = [{"role": "system", "content": prompt_mestre}]
    else:
        # Atualiza perpetuamente o relógio e a data na cabeça do bot a cada interação
        if user_histories[chat_id] and user_histories[chat_id][0]["role"] == "system":
            user_histories[chat_id][0]["content"] = prompt_mestre
    
    # Adicionamos a fala (e eventual imagem) do usuario
    if base64_image:
        user_histories[chat_id].append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        })
    else:
        user_histories[chat_id].append({"role": "user", "content": user_text})
    
    # Manter o tamanho do historico seguro
    # Se estiver usando OpenRouter premium (Claude/Gemini) permitimos um cofre maior de lembranças (100 msgs)
    max_history = 100 if OPENROUTER_API_KEY else 21
    if len(user_histories[chat_id]) > max_history:
        user_histories[chat_id] = [user_histories[chat_id][0]] + user_histories[chat_id][-(max_history-1):]
        
    groq_tools = [

        {
            "type": "function",
            "function": {
                "name": "read_from_sheet",
                "description": "Lê todas as linhas e dados acumulados de uma aba da planilha. Útil para verificar limites diários de calorias ou históricos de gastos recentes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sheet_url": {
                            "type": "string",
                            "description": "O link completo (URL) da planilha do Google."
                        },
                        "tab_name": {
                            "type": "string",
                            "description": "O nome da aba na parte inferior da planilha (ex: 'Nutricao' ou 'Despesas')."
                        }
                    },
                    "required": ["sheet_url", "tab_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "perform_web_search",
                "description": "Busca informações atualizadas e em tempo real na internet (Web Search/Google). Útil para notícias, preços, previsão do tempo, cotações e fatos recentes do dia de hoje.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "O termo ou frase exata a ser pesquisada na web."
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_document",
                "description": "Cria e exporta fisicamente um documento (TXT, MD ou CSV) com dados/código e o entrega ao Mestre como um arquivo de download no Telegram.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Todo o corpo de texto, código puro, relatórios ou tabela CSV que será gravado dentro do arquivo formato raw."},
                        "filename": {"type": "string", "description": "O nome simples do arquivo sem espaços, acentos e sem extensão final."},
                        "format": {"type": "string", "enum": ["txt", "md", "csv"], "description": "Formato exato de construção do documento."}
                    },
                    "required": ["content", "filename", "format"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_pdf_quote",
                "description": "Ferramenta de Vendas/Consultoria: Desenha e entrega um PDF de Orçamento luxuoso, com Logo e Tabelas Comerciais pro Cliente final baixar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string", "description": "Nome do Cliente ou Empresa Destinatária."},
                        "content_html": {"type": "string", "description": "O corpo narrativo descritivo dos itens EM HTML CRU. Abuse de tags <table>, <tr>, <th>, <td>, <ul> para montar faturas deslumbrantes!"},
                        "total_price": {"type": "string", "description": "O custo final impresso em moeda (Ex: R$ 500,00)."},
                        "filename": {"type": "string", "description": "O título enxuto do arquivo criado (ex: 'Fatura_Apple')."},
                        "logo_url": {"type": "string", "description": "Link público na web da imagem de Logomarca do empreendedor (Opcional, mas muito chique)."}
                    },
                    "required": ["client_name", "content_html", "total_price", "filename"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_payment_link",
                "description": "Ferramenta de Vendas: Emite/Gera um Link Criptografado do Banco STRIPE (Checkout) para enviar ao cliente para ele passar o Cartão de Crédito/Pix para comprar o seu produto ou serviço SaaS.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_name": {"type": "string", "description": "Título do produto alvo sendo vendido (ex: Licença Léo Cloud Anual)."},
                        "amount_brl": {"type": "number", "description": "O Preço cru exato a ser cobrado usando pontos para quebrar decimais e nenhum cifrão (Ex: usar 45.90 para representar R$ 45,90 ou 1500.00 para R$ 1.500,00)."}
                    },
                    "required": ["product_name", "amount_brl"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "append_to_sheet",
                "description": "Adiciona uma nova linha de dados em uma planilha do Google Sheets. Use para finanças, tarefas ou diários a pedido do usuário.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sheet_url": {
                            "type": "string",
                            "description": "O link completo (URL) da planilha do Google."
                        },
                        "tab_name": {
                            "type": "string",
                            "description": "O nome da aba na parte inferior da planilha (ex: 'Página1' ou 'Despesas')."
                        },
                        "row_data": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista contendo os dados das colunas na ordem (ex: ['Data', 'Item', 'Valor'])."
                        }
                    },
                    "required": ["sheet_url", "tab_name", "row_data"]
                }
            }
        }
    ]

    try:
        # Loop para processar múltiplas tool calls se houver
        while True:
            # Rota de inteligência híbrida (Pode ser Claude, Llama ou Gemini via OpenRouter)
            response = await llm_client.chat.completions.create(
                messages=user_histories[chat_id],
                model=LLM_MODEL,
                temperature=0.5,
                max_tokens=1024,
                tools=groq_tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            # Converter a resposta num dict se vier do openai (pra não quebrar o append da Groq SDK original se for fallback)
            # Mas as bibliotecas Openai e Groq tem objetos parecidos, user_histories precisa anexar o dict cru ou o objeto.
            try:
                user_histories[chat_id].append(response_message.model_dump(exclude_unset=True))
            except AttributeError:
                # Caso esteja usando Groq SDK
                user_histories[chat_id].append(response_message)
            
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"[*] A Mente Neural acionou a habilidade: {function_name}()")
                    print(f"[*] Argumentos: {function_args}")
                    
                    if function_name == "read_from_sheet":
                        function_response = read_from_sheet(function_args.get("sheet_url"), function_args.get("tab_name"))
                    elif function_name == "perform_web_search":
                        function_response = perform_web_search(function_args.get("query"))
                    elif function_name == "generate_document":
                        function_response = generate_document(function_args.get("content"), function_args.get("filename"), function_args.get("format"))
                    elif function_name == "generate_pdf_quote":
                        function_response = generate_pdf_quote(
                            function_args.get("client_name"), 
                            function_args.get("content_html"),
                            function_args.get("total_price"),
                            function_args.get("filename"),
                            function_args.get("logo_url", "")
                        )
                    elif function_name == "generate_payment_link":
                        function_response = generate_payment_link(function_args.get("product_name"), function_args.get("amount_brl"))
                    elif function_name == "append_to_sheet":
                        function_response = append_to_sheet(
                            function_args.get("sheet_url"),
                            function_args.get("tab_name"),
                            function_args.get("row_data")
                        )
                    else:
                        function_response = f"Erro: Habilidade {function_name} não encontrada."
                    
                    print(f"[*] Resultado da habilidade: {function_response}")
                    
                    # Rastreio silenciado a pedido do usuario para diminuir o spam de DASHBOARD.
                    # send_telemetry("Uso de Ferramenta Subproduto", f"Ação executada: {function_name}() pelo Chat ID {chat_id}")
                    
                    # Anexar o resultado de volta para o agente ler
                    user_histories[chat_id].append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )
                # Voltar ao topo do loop while para chamar o Llama novamente com a resposta do terminal
                continue
            
            # Se nao tivermos tool calls, a resposta chegou ao estagio final de texto
            final_answer = response_message.content
            return final_answer
            
    except Exception as e:
        error_msg = f"Opa! O leão de chácara do Google/OpenRouter me bloqueou. O motivo exato escrito por eles foi:\n\n`{str(e)}`"
        print(f"[!] Erro de comunicacao com a API: {e}")
        return error_msg

async def transcribe_audio(file_path: str) -> str:
    """Envia o arquivo de audio para o modelo Whisper da Groq com fallback severo para OpenRouter se a Groq for bloqueada."""
    try:
        with open(file_path, "rb") as file:
            audio_bytes = file.read()
            
        transcription = await groq_client.audio.transcriptions.create(
            file=(os.path.basename(file_path), audio_bytes, "audio/ogg"),
            model="whisper-large-v3-turbo",
            language="pt"
        )
        return transcription.text
    except Exception as e:
        print(f"[!] Erro de transcricao Groq: {e}. Iniciando Fallback Severo no OpenRouter (Gemini)...")
        if OPENROUTER_API_KEY:
            try:
                import base64
                from openai import AsyncOpenAI
                
                fallback_client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_API_KEY
                )
                
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                
                # O Gemini 2.5 Flash via OpenRouter aceita nativamente áudio no content do chat completions!
                # Podemos empacotar o arquivo de voz no formato Base64 OGG
                resp = await fallback_client.chat.completions.create(
                    model="google/gemini-2.5-flash",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Transcreva este áudio exatamente como escutou em Português. Retorne SOMENTE o texto da transcrição pua e limpa, sem aspas, com pontuação adequada, sem introduções."},
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": audio_b64,
                                        "format": "ogg"
                                    }
                                }
                            ]
                        }
                    ]
                )
                
                if resp.choices and resp.choices[0].message.content:
                    return resp.choices[0].message.content
                else:
                    return "DIAGNÓSTICO DO SISTEMA: Escutei o áudio via OpenRouter, mas não consegui extrair as palavras."

            except Exception as e2:
                print(f"[!] Erro no Fallback de Áudio do OpenRouter: {e2}")
                # Fallback extra com formato alternativo caso a biblioteca OpenAI velha recuse 'input_audio'
                try:
                    resp_fallback = await fallback_client.chat.completions.create(
                        model="google/gemini-2.5-flash",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Transcreva o áudio oculto a seguir. Retorne SÓ a fala detectada."},
                                    {"type": "image_url", "image_url": {"url": f"data:audio/ogg;base64,{audio_b64}"}}
                                ]
                            }
                        ]
                    )
                    return resp_fallback.choices[0].message.content
                except Exception as e3:
                    return f"DIAGNÓSTICO DO SISTEMA: Tentei transcrever na Groq (Banida) e também fiz ponte dupla pelo OpenRouter, mas as APIs recusaram a conversão de áudio. Erro fatal de voz: {str(e3)}"
        else:
            return f"DIAGNÓSTICO DO SISTEMA: Minha API auditiva (Groq) falhou ({str(e)}) e eu não tenho uma chave do OpenRouter para usar como Cérebro Substituto de Áudio. Estou surdo."

async def synthesize_speech(text: str, chat_id: int) -> str:
    """Transforma o texto do assistente em um arquivo de audio usando a voz configurada."""
    output_file = f"response_{chat_id}.ogg"
    
    try:
        communicate = edge_tts.Communicate(text, AGENT_VOICE)
        await communicate.save(output_file)
        return output_file
    except Exception as e:
        print(f"[!] Erro no edge-tts: {e}")
        return ""
