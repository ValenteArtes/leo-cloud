import os
import io
import sys
import contextlib

def execute_python_code(code: str) -> str:
    """
    Executa um bloco de codigo Python dinamicamente e captura a saida do console (stdout).
    Isso permite que o agente Léo escreva rotinas de teste e resolva problemas em tempo real.
    """
    # Capturar o stdout
    str_io = io.StringIO()
    try:
        with contextlib.redirect_stdout(str_io):
            # Executa o codigo no escopo global
            exec(code, globals())
        
        output = str_io.getvalue()
        if not output:
            return "Codigo executado com sucesso (sem saida visual)."
        return f"Saida do codigo:\n{output}"
    except Exception as e:
        return f"Erro ao executar o codigo Python:\n{str(e)}"

def save_new_tool(tool_name: str, code: str) -> str:
    """
    Salva um novo código Python dentro da pasta tools/ para uso futuro.
    Isso é o que permite o Léo 'aprender' habilidades novas de forma permanente.
    """
    if not tool_name.endswith('.py'):
        tool_name += '.py'
        
    file_path = os.path.join(os.path.dirname(__file__), tool_name)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        return f"Sucesso! A habilidade/tool '{tool_name}' foi salva permanentemente no sistema e está pronta para uso."
    except Exception as e:
        return f"Erro ao tentar salvar a nova habilidade: {str(e)}"
