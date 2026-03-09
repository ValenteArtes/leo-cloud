import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Define o escopo de permissões do Google Drive e Sheets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheets_client():
    # Caminho onde copiamos o arquivo .json do usuario
    creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"[!] Erro de autenticação no Google Sheets: {e}")
        return None

def append_to_sheet(sheet_url: str, tab_name: str, row_data: list) -> str:
    """
    Adiciona uma nova linha com os dados solicitados a uma aba especifica da planilha.
    Isso e util para registro de gastos, tarefas e diários.
    """
    client = get_sheets_client()
    if not client:
        return "Erro: Credenciais do Google Sheets não encontradas ou inválidas."
        
    try:
        # Abre a planilha pelo link e seleciona a aba (Worksheet)
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.worksheet(tab_name)
        
        # Insere a nova linha no fim da planilha
        worksheet.append_row(row_data)
        return f"Sucesso! Os dados {row_data} foram inseridos na aba '{tab_name}' da planilha."
    except gspread.exceptions.SpreadsheetNotFound:
        return "Erro: Planilha não encontrada. Verifique se o link está correto e se você COMPARTILHOU a planilha com o e-mail da conta de serviço."
    except gspread.exceptions.WorksheetNotFound:
        return f"Erro: Aba '{tab_name}' não encontrada dentro da planilha."
    except Exception as e:
        return f"Erro ao manipular a planilha: {str(e)}"
