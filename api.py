import aiohttp
import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()
HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')

async def obter_puuid_henrik(nome: str, tag: str):
    """
    Faz uma chamada assíncrona na API do HenrikDev para pegar o PUUID do jogador.
    """
    # URL da rota da API para conversão de Nome/Tag em dados da conta
    nome_formatado = urllib.parse.quote(nome)
    url = f"https://api.henrikdev.xyz/valorant/v1/account/{nome_formatado}/{tag}"
    
    cabecalhos = {
        "Authorization": HENRIK_API_KEY
    }

    # Abrimos uma 'sessão' de internet assíncrona com aiohttp
    async with aiohttp.ClientSession() as session:
        # Fazemos a requisição GET (pedindo os dados)
        async with session.get(url, headers=cabecalhos) as response:
            if response.status == 200: # 200 significa "OK, deu tudo certo!"
                # Convertemos a resposta de JSON para um dicionário Python
                dados = await response.json()
                
                # Entramos no JSON e pescamos apenas o PUUID
                return dados['data']['puuid']
            else:
                # Se o jogador não existir ou a API cair, retornamos vazio
                return None

async def obter_detalhes_partida(match_id: str):
    """
    Baixa o MatchDTO completo da partida.
    """
    # Rota da API do Henrik para buscar os detalhes específicos de UMA partida
    url = f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}"
    
    cabecalhos = {"Authorization": HENRIK_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=cabecalhos) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Erro ao buscar detalhes da partida: {response.status}")
                return None

async def pegar_partidas_recentes(puuid: str):
        """
        Consulta Rasa (Fase 1): Agora retorna a lista completa das últimas 5 partidas 
        para podermos calcular o histórico do que aconteceu enquanto o bot estava offline.
        """
        url = f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/br/{puuid}"
        cabecalhos = {"Authorization": HENRIK_API_KEY}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=cabecalhos) as response:
                if response.status == 200:
                    dados = await response.json()
                    return dados.get('data', []) # Retorna a lista de partidas
                else:
                    print(f'Erro ao carregar ultimas partidas: {response.status}')
                return []
        
async def obter_detalhes_partida(match_id: str):
    """
    pega o MatchDTO completo da partida retorna um json gigante com todas as informacoes da partida
    """

    url = f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}"

    cabecalhos = {"Authorization": HENRIK_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=cabecalhos) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Erro ao buscar detalhes da partida: {response.status}")
                return None

async def obter_mmr_jogador(puuid: str):
    """
    Busca o Elo (MMR) atualizado do jogador em tempo real, após a partida.
    """
    url = f"https://api.henrikdev.xyz/valorant/v1/by-puuid/mmr/br/{puuid}"
    cabecalhos = {"Authorization": HENRIK_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=cabecalhos) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Erro ao buscar MMR atualizado: {response.status}")
                return None
    