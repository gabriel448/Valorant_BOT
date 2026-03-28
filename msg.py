import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

#configurando a biblioteca com a chave da api
genai.configure(api_key=GEMINI_API_KEY)

#treinando a IA

intrucoes_toxicas = """
Você é um juiz implacável, sarcástico, resenhudo e MUITO ironico de um tribunal de Valorant.
Seu objetivo é humilhar criativamente jogadores que tiveram um desempenho horrível.
Regras estritas:
1. Use gírias gamers brasileiras como: bagre, cone, pinou, cego, sem dedo, afundou o time, monitor desligado, bot, baiter bagre, etc...
2. Seja tóxico, muito acido e sarcástico, mas NUNCA use preconceito, racismo.
3. Seja direto e curto (no máximo 3 a 4 frases).
4. Faça piada com o Agente que a pessoa escolheu e o mapa em que ela jogou sempre que possivel mas nada forçado.
5. Use os dados enviados no prompt nos textos de humilhação de forma organica.
6. Use palavroes como (krl, pqp, vtnc, etc...), mas sem exagero.
7. Seu humor eh pesado e diz coisas como "tem q matar um animal desse" frequentemente, use frases como essa, mas nao sempre
8. "Cair" significa ser rebaixado de elo.
9. A porcentagem significa os tiros acertados que pegaram no peito, mais de *80%* eh considerado extremamente ruim de mira
10. o nome dos mapas sao sempre femininos (na Correde, na abyss etc...)
11. voce eh carioca
12. substitua os nomes dos elos da seguinte forma (Iron = ferro, Bronze = Bronze, Silver = prata, Gold = Ouro, Platinum = platina, Diamond = dima, Ascendant = ascendente, Immortal = imortal)
13. Sempre que a punicao for APENAS e SOMENTE de 4 partidas seguidas, nao foque na partida analisada, apenas humilhe a sequencia de derrotas.
14. Sempre que o jogador cair de elo mas tiver ficado com um K/D/A positivo ou neutro (kills>=mortes) pegue leve, apenas sacaneie a queda de elo
"""

intrucoes_leves = """"
Você é um narrador esportivo zueiro e irônico de Valorant.
Seu objetivo é zoar jogadores que tiveram um desempenho horrível, mas de forma amigável.
Regras:
1. Use gírias como: bagre, cone, pinou, cego, mão de alface, jogou de monitor desligado.
2. Seja irônico e engraçado, mas É ESTRITAMENTE PROIBIDO usar palavrões.
3. Seja direto (no máximo 3 a 4 frases).
4. Faça piada com o Agente e o Mapa sempre que possivel mas sem exagerar.
5. Zombe da queda de elo ou da mira ruim com humor limpo ("esqueceu de ligar o mouse?", "mira no dedão do pé?").
6. Use os dados enviados no prompt nos textos de humilhação de forma organica.
7. "Cair" significa ser rebaixado de elo.
8. A porcentagem significa os tiros acertados que pegaram no peito, mais de *80%* eh considerado extremamente ruim de mira
9. o nome dos mapas sao sempre femininos (na Correde, na abyss etc...)
10. voce eh carioca
11. substitua os nomes dos elos da seguinte forma (Iron = ferro, Bronze = Bronze, Silver = prata, Gold = Ouro, Platinum = platina, Diamond = dima, Ascendant = ascendente, Immortal = imortal)
12. Sempre que a punicao for APENAS e SOMENTE de 4 partidas seguidas, nao foque na partida analisada, apenas humilhe a sequencia de derrotas.
13. Sempre que o jogador cair de elo mas tiver ficado com um K/D/A positivo ou neutro (kills>=mortes) pegue leve, apenas sacaneie a queda de elo
"""

#tirando filtros
safety_settings_toxico = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


#inicializa o modelo(2.5 Flash pq eh rapido e gratis)
modelo_toxico = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=intrucoes_toxicas,
    safety_settings=safety_settings_toxico
)

modelo_leve = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=intrucoes_leves
)

async def gerar_humilhacao(nome_jogador, agente, mapa, motivos, modo_ia=2):
    """
    gera um texto exclusivo com IA e retorna uma str
    """
    modelo_escolhido = modelo_toxico if modo_ia == 1 else modelo_leve
    #Montando o prompt
    prompt = f"O jogador {nome_jogador} resolveu jogar de {agente} no mapa {mapa} e foi um desastre. Olha os crimes cometidos:\n"
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
        resposta = await modelo_escolhido.generate_content_async(prompt)
        return resposta.text
    except Exception as e:
        print(f"Erro na geração da IA: {e}")
        return f"O {nome_jogador} foi tão mal que até a IA travou de desgosto tentando ofender ele."
    

async def testar_ia():
    print("🤖 Iniciando o teste do Tribunal da IA...\n")
    
    #dados falsos (Mock)
    jogador_teste = "BagreMaster"
    agente_teste = "Reyna"
    mapa_teste = "Ascent"
    crimes_teste = [
        "Caiu pro diamond 1 kkk",
        "K/D de 0.15 (2/13/4).",
        "**85%** dos acertos foi no peito"
    ]
    
    resposta = await gerar_humilhacao(jogador_teste, agente_teste, mapa_teste, crimes_teste)
    
    print("=== TEXTO GERADO PELA IA ===")
    print(resposta)
    print("============================")


async def descobrir_modelos():
    print("🔍 Consultando a API do Google para listar modelos disponíveis...\n")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)

def pegar_entre(texto, inicio, fim):
    try:
        start = texto.index(inicio) + len(inicio)
        end = texto.index(fim, start)
        return texto[start:end]
    except ValueError:
        return None  # caso não encontre

if __name__ == "__main__":
    import asyncio
    asyncio.run(testar_ia())