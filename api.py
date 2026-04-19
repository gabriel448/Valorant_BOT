import aiohttp
import urllib.parse
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()
HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')

async def _fazer_requisicao_get(url: str):
    """
    TIMEOUT
    Aplica o timeout de 30s e lida com os erros para não travar o bot caso a api nao responder nunca.
    """
    timeout_api = aiohttp.ClientTimeout(total=30)
    cabecalhos = {"Authorization": HENRIK_API_KEY}

    try:
        async with aiohttp.ClientSession(timeout=timeout_api, headers=cabecalhos) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"⚠️ Erro {response.status} na API HenrikDev para a URL: {url}")
                    return None
                    
    except asyncio.TimeoutError:
        print(f"⚠️ Timeout: A API demorou mais de 15s para responder. Ignorando...")
        return None
    except Exception as e:
        print(f"⚠️ Erro crítico de conexão na API: {e}")
        return None

async def obter_puuid_henrik(nome: str, tag: str):
    """
    Faz uma chamada assíncrona na API do HenrikDev para pegar o PUUID do jogador.
    """
    # URL da rota da API para conversão de Nome/Tag em dados da conta
    nome_formatado = urllib.parse.quote(nome)
    url = f"https://api.henrikdev.xyz/valorant/v1/account/{nome_formatado}/{tag}"
    
    dados = await _fazer_requisicao_get(url)

    if dados and 'data' in dados:
        return dados['data']['puuid']
    print('⚠️ dados veio sem "data" ou chegou corrompido ')
    return 

async def pegar_partidas_recentes(puuid: str):
        """
        Consulta Rasa (Fase 1): Agora retorna a lista completa das últimas 5 partidas 
        para podermos calcular o histórico do que aconteceu enquanto o bot estava offline.
        """
        url = f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/br/{puuid}"
        dados = await _fazer_requisicao_get(url)

        
        if dados and 'data' in dados:
            return dados.get('data', []) # Retorna a lista de partidas
        
        print(f'⚠️ Erro ao carregar ultimas partidas')
        return []
        
async def obter_detalhes_partida(match_id: str):
    """
    pega o MatchDTO completo da partida retorna um json gigante com todas as informacoes da partida
    """

    url = f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}"
    dados = await _fazer_requisicao_get(url)
    
    if dados:
        return dados
    
    print(f"⚠️ Erro ao buscar detalhes da partida")
    return None

async def obter_mmr_jogador(puuid: str):
    """
    Busca o Elo (MMR) atualizado do jogador em tempo real, após a partida.
    """
    url = f"https://api.henrikdev.xyz/valorant/v1/by-puuid/mmr/br/{puuid}"
    dados = await _fazer_requisicao_get(url)

    if dados:
        return dados
    
    print(f"⚠️ Erro ao buscar MMR atualizado")
    return None
    