import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Define o escopo de permissões do Google Drive e Sheets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

import json

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1yem69FdQaffZ71mEhzmp5K_kwr6lP-QaBcZWQElpgDw/edit?hl=pt-PT&gid=0#gid=0"

def get_sheets_client():
    # Verifica primeiro se foi passado via variavel de ambiente (Deploy Rapido Render)
    env_creds = os.environ.get("GOOGLE_CREDENTIALS")
    
    try:
        if env_creds and env_creds.strip():
            creds_dict = json.loads(env_creds)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
        else:
            # Fallback para o modo antigo de arquivo local
            creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scopes)
            
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"[!] Erro de autenticação no Google Sheets: {e}")
        return None

def _get_or_create_worksheet(sheet, tab_name: str):
    import unicodedata
    def norm(s):
        return ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn').lower().strip()
    
    target = norm(tab_name)
    
    # 1. Procura pela coincidencia exata (com acentos)
    try:
        return sheet.worksheet(tab_name)
    except:
        pass
        
    # 2. Procura pela normalizada ignorando Ç e acentos
    for ws in sheet.worksheets():
        if norm(ws.title) == target:
            return ws
            
    # 3. A aba não existe me nenhum formato. O sistema CRIA SOZINHO.
    return sheet.add_worksheet(title=tab_name.replace("ç", "c").replace("ã", "a"), rows=200, cols=10)

def append_to_sheet(sheet_url: str, tab_name: str, row_data: list) -> str:
    """
    Adiciona uma nova linha com os dados solicitados a uma aba especifica da planilha.
    Isso e util para registro de gastos, tarefas e diários.
    """
    if not sheet_url or "google.com" not in sheet_url:
        sheet_url = DEFAULT_SHEET_URL
        
    client = get_sheets_client()
    if not client:
        return "Erro: Credenciais do Google Sheets não encontradas ou inválidas."
        
    try:
        # Abre a planilha pelo link e seleciona a aba (auto-criando se João esquecer)
        sheet = client.open_by_url(sheet_url)
        worksheet = _get_or_create_worksheet(sheet, tab_name)
        
        # Insere a nova linha no fim da planilha
        worksheet.append_row(row_data)
        return f"Sucesso! Os dados {row_data} foram inseridos na aba '{worksheet.title}'."
    except gspread.exceptions.SpreadsheetNotFound:
        return "Erro: Planilha não encontrada. O link pode estar errado ou faltou compartilhar com o e-mail do bot."
    except Exception as e:
        return f"Erro ao manipular a planilha: {str(e)}"

def read_from_sheet(sheet_url: str, tab_name: str) -> str:
    """
    Ferramenta para ler todos os dados acumulados (histórico) na aba do Google Sheets.
    """
    if not sheet_url or "google.com" not in sheet_url:
        sheet_url = DEFAULT_SHEET_URL
        
    client = get_sheets_client()
    if not client:
        return "Erro: Credenciais do Google Sheets não encontradas ou inválidas."
        
    try:
        sheet = client.open_by_url(sheet_url)
        worksheet = _get_or_create_worksheet(sheet, tab_name)
        
        records = worksheet.get_all_values()
        if not records or len(records) == 0:
            return "Aba vazia. Nenhum histórico salvo ainda."
            
        return json.dumps(records, ensure_ascii=False)
    except Exception as e:
        return f"Erro na leitura da aba do Sheets: {str(e)}"
