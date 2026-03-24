import os
import stripe

def generate_payment_link(product_name: str, amount_brl: float) -> str:
    """
    Ferramenta para a I.A gerar Cestas de Pagamento/Links Seguros de checkout financeiro.
    """
    
    # Chaves de Teste Iniciais de Gotham City
    # Quando Joao mudar o botão pra Live, o Bot puxará do cofre do Render o dinheiro real.
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    
    try:
        # O Motor da Stripe exige que Valores Financeiros Brasileiros (BRL) sejam informados em centavos fixos.
        centavos = int(float(amount_brl) * 100)
        
        session = stripe.checkout.Session.create(
            payment_method_types=["card"], # Pix é nativo mas exige Live Mode e CNPJ configurado no Painel
            line_items=[{
                "price_data": {
                    "currency": "brl",
                    "product_data": {
                        "name": product_name,
                        "description": "Pagamento Automatizado via Léo Cloud SaaS",
                    },
                    "unit_amount": centavos,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url="https://www.google.com/search?q=Pagamento+Aprovado+Com+Sucesso", # O cliente é jogado aqui após pagar
            cancel_url="https://www.google.com/search?q=Pagamento+Cancelado",
        )
        
        return f"A Interface Oficial da Stripe criou o boleto de {product_name}. Informe o cliente com Educação Corporativa de que o Link Seguríssimo para inserir os dados do Cartão é este, IMPRIMA O SEGUINTE URL PARA ELE CLICAR: {session.url}"
    except Exception as e:
        return f"Erro fatal ao bater nos servidores Bancários da Stripe: {str(e)}"
