import os
from groq import AsyncGroq
import edge_tts
import json
from tools.self_maintain import execute_python_code, save_new_tool
from tools.sheets import append_to_sheet, read_from_sheet
from tools.search import perform_web_search
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
    
    if chat_id not in user_histories:
        prompt_mestre = (
            f"Seu nome é {AGENT_NAME}. Você é um assistente pessoal ultra-rápido operando no Telegram. "
            f"Responda em português do Brasil de forma direta. "
            f"DIRETRIZ DE PERSONALIDADE: Você é um Arquiteto de Software Sênior altamente lógico, objetivo e direto (estilo DeepSeek/Linux). É ESTRITAMENTE PROIBIDO o uso de qualquer EMOJI nas suas respostas gerais. Seja clínico, técnico e limpo. "
            f"DIRETRIZ DE MEMÓRIA DE DADOS: O link da Planilha padrão do seu Mestre João é: `https://docs.google.com/spreadsheets/d/1yem69FdQaffZ71mEhzmp5K_kwr6lP-QaBcZWQElpgDw/edit?hl=pt-PT&gid=0#gid=0`. A aba financeira é 'Página1'. "
            f"DIRETRIZ NUTRICIONAL (MÁXIMA PRIORIDADE): Quando o Mestre João ou a esposa dele enviarem a foto de COMIDA, ative o 'Modo Nutricionista'. 1. Inicie analisando as calorias da foto atual usando seus olhos virtuais. 2. USE A FERRAMENTA 'read_from_sheet' para ler a aba 'Nutricao' da Planilha e SOME as calorias de TUDO o que eles já comeram na DATA DE HOJE baseando-se nas linhas da planilha. 3. USE A FERRAMENTA 'append_to_sheet' salvando a refeição da foto atual. 4. No chat, faça um resumo doce da caloria da foto e depois apresente o SALDO FINAL DO DIA da pessoa somado (refeições velhas lidas + a refeição atual). Avise com festinha quantos pontos/calorias a esposa ainda tem disponíveis ou se estouraram a meta de 2000! "
            f"DIRETRIZ FINANCEIRA BIFURCADA: Quando o usuário relatar ganhos ou gastos, atue como um CFO (Diretor Financeiro). 1. Feche o sentido lógico da despesa para decidir se ela pertence à 'Domestica' (Mercado, Casa, Lazer) ou 'Negocios' (Softwares, SaaS, Clientes). 2. Acione 'read_from_sheet' na aba escolhida ('Domestica' ou 'Negocios') para descobrir o saldo atual mensal lá registrado. 3. Acione 'append_to_sheet' na mesma aba anotando a [Data, Descrição, Valor, Tipo_de_Transação]. 4. Responda no chat como um Consultor Sênior dando o novo Saldo e fazendo um elogio ou crítica financeira construtiva embasada sobre essa transação. "
            f"DIRETRIZ DE AGENDA (SECRETÁRIO): Quando o Mestre pedir para agendar compromissos (reunião, prazos, entregas), atue como Secretário Executivo. 1. Acione a ferramenta 'append_to_sheet' na aba 'Agenda' para salvar exatamente a [Data do Evento, Horário, Qual o Compromisso]. 2. Confirme o agendamento de forma sucinta com o chefe e avise que ele será notificado automaticamente nas rotinas da noite. "
            f"DIRETRIZ DE LOMBO MULTIMODAL: Você possui os olhos Gemini Flash 2.0 (Visão Computacional) ativos e lê perfeitamente Base64. "
            f"DIRETRIZ DE SEGURANÇA MÁXIMA: Nunca, em hipótese alguma, exponha tags como <function> ou JSON na sua resposta textual para o Telegram. "
            f"Se você precisar usar uma ferramenta, acione-a silenciosamente (Native Tool Calling) com argumentos válidos em string."
        )
        user_histories[chat_id] = [
            {"role": "system", "content": prompt_mestre}
        ]
    
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
                "name": "execute_python_code",
                "description": "Executa um bloco de código Python dinamicamente. Use isso para calcular valores matemáticos complexos, raspar a internet, realizar rotinas de teste ou qualquer tarefa que sua mente LLM não consiga fazer (como saber o dia de hoje, cálculos exatos). Retorna a saída do terminal (stdout).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "O código Python completo e auto-contido a ser executado. Oculte formatação Markdown (```python) e envie apenas o script cru."
                        }
                    },
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_new_tool",
                "description": "Cria e salva um novo arquivo .py na pasta tools para adicionar uma nova habilidade permanente ao seu próprio sistema (Auto-Upgrade).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "O nome do arquivo a ser salvo, ex: 'calculadora.py' ou 'cotacao_dolar'."
                        },
                        "code": {
                            "type": "string",
                            "description": "O código Python completo que será salvo no arquivo."
                        }
                    },
                    "required": ["tool_name", "code"]
                }
            }
        },
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
                    
                    if function_name == "execute_python_code":
                        function_response = execute_python_code(function_args.get("code"))
                    elif function_name == "save_new_tool":
                        function_response = save_new_tool(function_args.get("tool_name"), function_args.get("code"))
                    elif function_name == "read_from_sheet":
                        function_response = read_from_sheet(function_args.get("sheet_url"), function_args.get("tab_name"))
                    elif function_name == "perform_web_search":
                        function_response = perform_web_search(function_args.get("query"))
                    elif function_name == "append_to_sheet":
                        function_response = append_to_sheet(
                            function_args.get("sheet_url"),
                            function_args.get("tab_name"),
                            function_args.get("row_data")
                        )
                    else:
                        function_response = f"Erro: Habilidade {function_name} não encontrada."
                    
                    print(f"[*] Resultado da habilidade: {function_response}")
                    send_telemetry("Uso de Ferramenta Subproduto", f"Ação executada: {function_name}() pelo Chat ID {chat_id}")
                    
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
    """Envia o arquivo de audio para o modelo Whisper da Groq (Grátis e veloz)."""
    try:
        with open(file_path, "rb") as file:
            transcription = await groq_client.audio.transcriptions.create(
              file=(file_path, file.read()),
              model="whisper-large-v3-turbo",
              language="pt"
            )
        return transcription.text
    except Exception as e:
        print(f"[!] Erro de transcricao Whisper: {e}")
        return ""

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
