import os
from datetime import datetime
from jinja2 import Template
from xhtml2pdf import pisa

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page { size: A4; margin: 2cm; }
    body { font-family: Helvetica, Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.5; }
    .header { text-align: center; border-bottom: 2px solid #1a73e8; padding-bottom: 20px; margin-bottom: 20px; }
    .logo { max-height: 80px; margin-bottom: 10px; }
    h1 { color: #1a73e8; font-size: 24px; margin: 0; }
    .client-box { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 30px; }
    .content-box { margin-bottom: 30px; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 20px; }
    th { background-color: #1a73e8; color: white; padding: 10px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #dddddd; }
    .total-box { text-align: right; font-size: 20px; font-weight: bold; margin-top: 20px; color: #28a745; border-top: 2px solid #28a745; padding-top: 15px; }
    .footer { text-align: center; font-size: 10px; color: #777777; margin-top: 50px; border-top: 1px solid #eeeeee; padding-top: 10px; }
</style>
</head>
<body>
    <div class="header">
        {% if logo_url %}
        <img src="{{ logo_url }}" class="logo"><br>
        {% endif %}
        <h1>PROPOSTA COMERCIAL</h1>
    </div>
    
    <div class="client-box">
        <strong>Para:</strong> {{ client_name }}<br>
        <strong>Emissão:</strong> {{ date }}<br>
        <strong>Referência:</strong> Orçamento de Serviços / Produtos
    </div>
    
    <div class="content-box">
        {{ content }}
    </div>
    
    <div class="total-box">
        TOTAL APROVADO: {{ total_price }}
    </div>
    
    <div class="footer">
        Gerado automaticamente pela Inteligência Artificial do Léo Cloud SaaS.<br>
        Documento válido por 15 dias corridos a partir da data de emissão.
    </div>
</body>
</html>
"""

def generate_pdf_quote(client_name: str, content_html: str, total_price: str, filename: str, logo_url: str = "") -> str:
    """Ferramenta de design de layout Python que empacota orçamentos HTML em PDFs lindos com formatação nativa."""
    
    # Sanitiza o nome arquivo para nao quebrar paths
    filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c=='_' or c=='-']).strip()
    if not filename: filename = "orcamento"
    filepath = f"{filename}.pdf"
    
    hoje = datetime.now().strftime("%d/%m/%Y")
    
    # O motor de Templates da Nuvem (Jinja) substitui variaveis magicamente no HTML
    template = Template(HTML_TEMPLATE)
    html_ready = template.render(
        logo_url=logo_url,
        client_name=client_name,
        date=hoje,
        content=content_html,
        total_price=total_price
    )
    
    # Motor Pesado do xhtml2pdf assume o rendering binário na nuvem!
    try:
        with open(filepath, "w+b") as result_file:
            pisa_status = pisa.CreatePDF(html_ready, dest=result_file)
            
        if pisa_status.err:
            return "Ocorreu um erro matemático ao quebrar a página PDF com a Biblioteca."
            
        return (f"A fatura/orçamento PDF com Logo foi injetada no disco principal com sucesso! "
                f"Avise seu Chefe que a fatura PDF está ponta e imprima esta tag obrigatoriamente (crua, como está) no seu chat: "
                f"<FILE_GENERATED>{filepath}</FILE_GENERATED>")
    except Exception as e:
        return f"Erro destrutivo ao converter design layout para PDF binário: {str(e)}"
