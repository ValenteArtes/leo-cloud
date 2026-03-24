import gspread, json, os
from oauth2client.service_account import ServiceAccountCredentials

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("C:/Users/jbati/.gemini/antigravity/playground/leo-cloud/credentials.json", scopes)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1yem69FdQaffZ71mEhzmp5K_kwr6lP-QaBcZWQElpgDw/edit?hl=pt-PT&gid=0#gid=0")
print("ABAS ENCONTRADAS:")
for ws in sheet.worksheets():
    print("-", ws.title)

print("\nTENTANDO A ABA NUTRICAO:")
try:
    ws = sheet.worksheet("Nutricao")
    print("Valores:", ws.get_all_values())
except Exception as e:
    print("ERRO Nutricao:", type(e), e)
