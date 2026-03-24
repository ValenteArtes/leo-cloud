import requests
from bs4 import BeautifulSoup
import json

def perform_web_search(query: str, max_results: int = 3) -> str:
    """Busca web multi-camadas rodando com Scraping direto para burlar Rate Limits do DuckDuckGo vindo de Nuvem."""
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    # 1º Tentativa: Usar Motores SearxNG (APIs públicas de privacidade, burla bloqueios do datacenter do Render)
    instances = [
        "https://searx.be/search",
        "https://searx.tiekoetter.com/search",
        "https://search.mdosch.de/search",
        "https://paulgo.io/search"
    ]
    
    for url in instances:
        try:
            res = requests.get(url, params={"q": query, "format": "json"}, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                if results:
                    best = results[:max_results]
                    return "Resultados Atualizados da Web:\n\n" + "\n\n".join([f"Título: {r.get('title')}\nURL: {r.get('url')}\nResumo: {r.get('content')}" for r in best])
        except Exception:
            continue # Tenta a próxima se uma falhar
            
    # 2º Tentativa (Fallback Brutal): Raspar HTML Crú do DuckDuckGo Lite
    try:
        data = {"q": query}
        res = requests.post("https://lite.duckduckgo.com/lite/", data=data, headers=headers, timeout=10)
        
        if res.status_code == 200 and "If this error persists" not in res.text:
            soup = BeautifulSoup(res.text, "html.parser")
            results = []
            
            for tr in soup.find_all("tr"):
                td = tr.find("td", class_="result-snippet")
                if td:
                    snippet = td.get_text(strip=True)
                    # O titulo da busca do DuckLite fica numa <tr> anterior à do snippet
                    try:
                        title_a = tr.previous_sibling.previous_sibling.find("a", class_="result-title") 
                        title = title_a.get_text(strip=True) if title_a else "Resultado"
                        link = title_a["href"] if title_a and title_a.has_attr("href") else ""
                    except AttributeError:
                        title = "Resultado"
                        link = ""
                        
                    results.append(f"Título: {title}\nURL: {link}\nResumo: {snippet}")
                    if len(results) >= max_results: 
                        break
                        
            if results: 
                return "Resultados Atualizados do DuckDuckGo:\n\n" + "\n\n".join(results)
    except Exception:
        pass
        
    return "Todas as 5 alternativas de pesquisa na Internet falharam simultaneamente. Os IPs do Render estão duramente bloqueados (Blacklist) agora pelas políticas de Anti-Bot e Limite de Taxa da Web. Tente novamente mais tarde."
