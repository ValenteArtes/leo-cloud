from duckduckgo_search import DDGS

def perform_web_search(query: str, max_results: int = 3) -> str:
    """
    Ferramenta para buscar informações em tempo real na internet usando o motor de busca DuckDuckGo (sem necessidade de chaves de API extras).
    Retorna título, link e um pequeno resumo dos melhores resultados da web.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
        if not results:
            return "A busca não retornou nenhum resultado útil na internet."
            
        formatted_results = []
        for i, res in enumerate(results):
            formatted_results.append(f"Resultado {i+1} [Fonte: {res.get('href')}]:\nTítulo: {res.get('title')}\nResumo: {res.get('body')}")
            
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Erro ao tentar acessar os servidores da web para buscar '{query}': {str(e)}"
