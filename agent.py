import os
from groq import AsyncGroq
import edge_tts
import json
from tools.self_maintain import execute_python_code, save_new_tool
from tools.sheets import append_to_sheet
from telemetry import send_telemetry

# Chave fornecida pelo usuario (usa variavel de ambiente no Render, hardcoded como fallback local)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "Léo")
AGENT_VOICE = os.environ.get("AGENT_VOICE", "pt-BR-AntonioNeural")

# Utilizando cliente assíncrono para aguentar o Telegram sem travar
client = AsyncGroq(api_key=GROQ_API_KEY)

# Dict para guardar o contexto de conversa por chat_id
user_histories = {}

async def process_message(user_text: str, chat_id: int) -> str:
    """Envia o texto do usuario para Llama 3 via Groq e retorna a resposta instantanea."""
    
    if chat_id not in user_histories:
        user_histories[chat_id] = [
            {"role": "system", "content": f"Seu nome é {AGENT_NAME}. Você é um assistente pessoal ultra-rápido, prático e direto. Você opera no Telegram e tem as capacidades de um agente inteligente executando na nuvem. Responda em português do Brasil, de forma extremamente conversacional e natural."}
        ]
    
    # Adicionamos a fala do usuario
    user_histories[chat_id].append({"role": "user", "content": user_text})
    
    # Manter o tamanho do historico seguro para nao estourar os tokens (System + ultimas 20 mensagens para acomodar tool calls)
    if len(user_histories[chat_id]) > 21:
        user_histories[chat_id] = [user_histories[chat_id][0]] + user_histories[chat_id][-20:]
        
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
            # llama-3.1-8b-instant suporta Tool Calling / Function Calling nativo
            response = await client.chat.completions.create(
                messages=user_histories[chat_id],
                model="llama-3.1-8b-instant",
                temperature=0.5,
                max_tokens=1024,
                tools=groq_tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            user_histories[chat_id].append(response_message) # Append the complete message object for tool state
            
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
        print(f"[!] Erro de comunicacao com a Groq API: {e}")
        return "Desculpe, minha mente Llama 3 acabou de ter um tropeço na conexão com os servidores."

async def transcribe_audio(file_path: str) -> str:
    """Envia o arquivo de audio para o modelo Whisper da Groq para transcriçao super rapida."""
    try:
        with open(file_path, "rb") as file:
            transcription = await client.audio.transcriptions.create(
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
