import os

def generate_document(content: str, filename: str, fmt: str) -> str:
    """
    Cria fisicamente um documento no formato TXT, MD ou CSV dentro dos discos do servidor Cloud,
    retornando uma TAG que obriga o backend principal a enviar este arquivo como Documento no Telegram.
    """
    # Limpa nomes bizarros para não causar Directory Traversal
    filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c==' ' or c=='_']).strip().replace(" ", "_")
    if not filename: 
        filename = "exportacao_leo"
        
    fmt = fmt.lower()
    if fmt not in ["txt", "md", "csv"]: 
        fmt = "txt"
        
    filepath = f"{filename}.{fmt}"
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Retorna a instrução secreta pro Cérebro Gemini
        return (f"Operação concluída com sucesso! Para que o usuario receba o download no Telegram, "
                f"VOCÊ DEVE DEVOLVER a frase secreta EXATAMENTE ASSIM no final do seu texto resposta final: "
                f"<FILE_GENERATED>{filepath}</FILE_GENERATED>")
                
    except Exception as e:
        return f"Falha sistêmica ao gravar o arquivo físico no HD: {str(e)}"
