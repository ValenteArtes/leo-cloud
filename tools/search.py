import os
from tavily import TavilyClient

def perform_web_search(query: str, max_results: int = 3) -> str:
    """Busca web rodando via Tavily Search API (Acesso corporativo para Agentes de I.A)."""
    
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return "Erro Fatal de Integração: A chave secreta 'TAVILY_API_KEY' não foi instalada nas Gavetas Environment do Render. A ferramenta cibernética de pesquisa está acorrentada e impossibilitada de operar online."
        
    try:
        tavily = TavilyClient(api_key=tavily_key)
        # O buscador de Rastreio em modo 'basic' entrega textos atualizados ultrarrápidos para o contexto do Agent LLM.
        response = tavily.search(query=query, max_results=max_results, search_depth="basic")
        
        results = response.get("results", [])
        if not results:
            return "A varredura global do Tavily não gerou nenhum resultado conclusivo para o radar do bot."
            
        formatted_results = []
        for i, res in enumerate(results):
            formatted_results.append(f"**Resultado Indexado {i+1}:**\nTítulo: {res.get('title', '')}\nURL Fonte: {res.get('url', '')}\nSinopse Direta: {res.get('content', '')}")
            
        return "Aqui estão os dados interceptados na Web de Última Geração (Tavily Network):\n\n" + "\n\n".join(formatted_results)
    except Exception as e:
        return f"A Máquina Corporativa Tavily API reportou um log de crash sistêmico ao investigar a string '{query}': {str(e)}"
