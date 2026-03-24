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

async def pegar_ultimo_match_id(puuid: str):
    """
    pega o ultimo id de uma partida (um str)
    """

    url = f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/br/{puuid}"

    cabecalhos = {"Authorization": HENRIK_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=cabecalhos) as response:
            if response.status == 200:
                dados = await response.json()

                #a API retorna uma lista 'data'que pegamos a partida indice 0 (a mais recente) e extraimos o 'matchid' dela.

                if len(dados['data']) > 0:
                    return dados['data'][0]['metadata']['matchid']
            print(f"Erro em capturar o ultimo matchID -- PUUID: {puuid} STATUS: {response.status}")
            return None
        
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
    