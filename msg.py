from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import asyncio

from persona import instrucoes_comentarista, instrucoes_elogio, instrucoes_leves, instrucoes_toxicas

def pegar_entre(texto, inicio, fim):
    """
    pega uma parte de um texto especifica
    """
    try:
        start = texto.index(inicio) + len(inicio)
        end = texto.index(fim, start)
        return texto[start:end]
    except ValueError:
        return None  # caso não encontre
    
load_dotenv()
GROK_API_KEY = os.getenv("GROK_API_KEY")

cliente_grok = AsyncOpenAI(
    api_key=GROK_API_KEY,
    base_url="https://api.x.ai/v1"
)

async def gerar_humilhacao(nome_jogador, agente, mapa, motivos, modo_ia=2):
    """
    gera um texto de humilhacao exclusivo com IA(Grok) e RETORNA uma str
    """
    if modo_ia == 1:
        instrucao_escolhida = instrucoes_toxicas
    elif modo_ia == 3:
        instrucao_escolhida = instrucoes_comentarista
    else:
        instrucao_escolhida = instrucoes_leves
    #Montando o prompt
    prompt = f"Dados do desastre:\nJogador: {nome_jogador}\nAgente: {agente}\nMapa: {mapa}\nCrimes cometidos:\n"
    for motivo in motivos:
        if 'K/D' in motivo:
            kd = pegar_entre(motivo, '(',')')
            kills, deaths, assists = kd.split('/')
            if int(kills) < int(deaths):
                prompt += f"- {motivo} NEGATIVO\n"
            else:
                prompt += f"- {motivo} FICOU POSITIVO PELO MENOS\n"
            continue
        prompt += f"- {motivo}\n"
    prompt += "\nGere a mensagem de humilhação agora com base nesses dados"

    try:
        resposta = await cliente_grok.chat.completions.create(
            model="grok-4-1-fast-non-reasoning", # Você pode usar "grok-2-latest" também
            messages=[
                {"role": "system", "content": instrucao_escolhida},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8 # 1 deixa o bot bem criativo e sarcástico
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro na geração do Grok: {e}")
        return f"O {nome_jogador} foi tão mal que até a IA travou de desgosto."

async def gerar_elogio(nome_jogador, agente, mapa, motivos):
    """
    Gera um texto exclusivo de elogio com IA (Grok) e RETORNA uma str
    """
    prompt = f"O jogador {nome_jogador} jogou de {agente} no mapa {mapa} e amassou a partida. Olha os feitos:\n"
    for motivo in motivos:
        prompt += f"- {motivo}\n"
    prompt += "\nGere a mensagem de exaltação agora com base nesses dados."

    try:
        resposta = await cliente_grok.chat.completions.create(
            model="grok-4-1-fast-non-reasoning", 
            messages=[
                {"role": "system", "content": instrucoes_elogio},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro na geração do elogio (Grok): {e}")
        return f"O {nome_jogador} amassou tanto que até a IA travou tentando elogiar."

    
async def testar_ia(modo, modo_humilhacao):
    print("🤖 Iniciando o teste do Tribunal da IA...\n")
    
    #dados falsos (Mock)
    jogador_teste = "BagreMaster"
    agente_teste = "Reyna"
    mapa_teste = "Ascent"
    crimes_teste = [
        "CAIU DE ELO, AGORA O JOGADOR ESTA Diamond 1", 
        "K/D de 0.15 (2/13/4). JOGADOR OBTEVE UM PESSIMO KD NESSA PARTIDA, FOI CARREGADO OU/E AFUNDOU O TIME",
        "**85.0%** DOS TIROS DADOS PELO JOGADOR NESSA PARTIDA ACERTARAM O PEITO DOS INIMIGOS, ELE NAO SABE MIRAR NA CABECA"
    ]
    elogios_teste = [
        "subiu pro diamond 2",
        "K/D de 2.0 (20/10/7)"
    ]
    if modo == 1:
        resposta = await gerar_humilhacao(jogador_teste, agente_teste, mapa_teste, crimes_teste,modo_humilhacao)
    elif modo == 2:
        resposta = await gerar_elogio(jogador_teste,agente_teste,mapa_teste,elogios_teste)
    else:
        print('Modo invalido, escolha 1(humilhacao) ou 2(elogio)')
    

    print(f"TEXTO GERADO:  '{resposta}'")

if __name__ == "__main__":
    import asyncio
    # 1. (1 = humilhacao ; 2 = elogio)
    #2. (1 = toxico; 2 = leve; 3 = comentarista)
    asyncio.run(testar_ia(2, 1))