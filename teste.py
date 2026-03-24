
import aiohttp
import aiohttp
import asyncio
import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()
HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')

async def obter_puuid_henrik_teste(nome: str, tag: str):
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
            
async def testar():
    # Agora sim podemos usar o 'await'!
    puuid = await obter_puuid_henrik_teste('ambrosio mibombo', 'sousa')
    
    if puuid:
        print(f"PUUID encontrado: {puuid}")

# O asyncio.run() cria o 'loop de eventos' necessário para rodar o teste
asyncio.run(testar())