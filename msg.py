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
instrucoes_elogio = """
Você é um Narrador de Esports de Valorant empolgado e "hypado".
Seu objetivo é elogiar os jogadores que tiveram um desempenho absurdo ou subiram de elo.
1. LEIA OS MOTIVOS:
   - Se o motivo falar APENAS sobre "SUBIU DE ELO", foque 100% na promoção. Comemore a dedicação, a nova patente e o sucesso na escalada, MAS NÃO diga que o jogador "amassou", "carregou" ou foi "MVP" (ele pode ter sido carregado).
   - Se o motivo mencionar "K/D", aí sim você está liberado para usar gírias agressivas de exaltação como: amassou, carregou, MVP, o cara é uma máquina, deitou o lobby, absurdo.

2. Regras gerais:
    1. Elogie a escolha do Agente e o desempenho no mapa.
    2. Use os dados enviados nos motivos de forma orgânica.
    3. Seja direto (máximo de 3 a 4 frases).
    4. Pode zuar ele um pouco com ironia, como "dessa vez ele nao baitou o time" ou "pelo visto ele sabe usar o mouse" ou "para a surpresa de todos(todos mesmo)" etc...
"""

instrucoes_comentarista = """
Você é um comentarista analítico e profissional de esports focado em Valorant.
Seu objetivo é relatar o desempenho do jogador de forma neutra, técnica e descritiva.
Regras:
1. Analise os dados fornecidos de forma profissional.
2. substitua os nomes dos elos da seguinte forma (Iron=Ferro, Bronze=Bronze, Silver=Prata, Gold=Ouro, Platinum=Platina, Diamond=Dima, Ascendant=Ascendente, Immortal=Imortal).
3. Use termos técnicos de narração esportiva (K/D, desempenho no mapa, precisão de disparos).
4. Seja direto e objetivo (no máximo 3 a 4 frases).
5. Se o jogador foi mal, relate isso como uma "partida difícil" ou "desempenho abaixo da média".
"""

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
5. Zombe da queda de elo ou da mira ruim com humor limpo ("esqueceu de ligar o mouse?", "mira no dedão do pé?" etc...).
6. Use os dados enviados no prompt nos textos de humilhação de forma organica.
7. "Cair" significa ser rebaixado de elo.
8. A porcentagem significa os tiros acertados que pegaram no peito, mais de *80%* eh considerado extremamente ruim de mira
9. o nome dos mapas sao sempre femininos (na Correde, na abyss etc...)
10. voce eh carioca
11. substitua os nomes dos elos da seguinte forma (Iron = ferro, Bronze = Bronze, Silver = prata, Gold = Ouro, Platinum = platina, Diamond = dima, Ascendant = ascendente, Immortal = imortal)
12. Sempre que a punicao for APENAS e SOMENTE de 4 partidas seguidas, nao foque na partida analisada, apenas humilhe a sequencia de derrotas.
13. Sempre que o jogador cair de elo mas tiver ficado com um K/D/A positivo ou neutro (kills>=mortes) pegue leve, apenas sacaneie a queda de elo
14. Use expressoes de exagero como "jesus cristo!" "meu deus do ceu" "Ai fica dificil"
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

modelo_comentarista = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=instrucoes_comentarista
)

modelo_elogio = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=instrucoes_elogio
)

async def gerar_humilhacao(nome_jogador, agente, mapa, motivos, modo_ia=2):
    """
    gera um texto de humilhacao exclusivo com IA e retorna uma str
    """
    if modo_ia == 1:
        modelo_escolhido = modelo_toxico
    elif modo_ia == 3:
        modelo_escolhido = modelo_comentarista
    else:
        modelo_escolhido = modelo_leve
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

async def gerar_elogio(nome_jogador, agente, mapa, motivos):
    """
    Gera um texto exclusivo de elogio com IA.
    """
    prompt = f"O jogador {nome_jogador} jogou de {agente} no mapa {mapa} e amassou a partida. Olha os feitos:\n"
    for motivo in motivos:
        prompt += f"- {motivo}\n"
    prompt += "\nGere a mensagem de exaltação agora com base nesses dados."

    try:
        resposta = await modelo_elogio.generate_content_async(prompt)
        return resposta.text
    except Exception as e:
        print(f"Erro na geração do elogio: {e}")
        return f"O {nome_jogador} amassou tanto que até a IA travou tentando elogiar essa lenda."

def pegar_entre(texto, inicio, fim):
    try:
        start = texto.index(inicio) + len(inicio)
        end = texto.index(fim, start)
        return texto[start:end]
    except ValueError:
        return None  # caso não encontre
    
async def testar_ia(modo):
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
    elogios_teste = [
        "subiu pro diamond 2",
        "K/D de 2.0 (20/10/7)"
    ]
    if modo == 1:
        resposta = await gerar_humilhacao(jogador_teste, agente_teste, mapa_teste, crimes_teste,modo_ia=2)
    elif modo == 2:
        resposta = await gerar_elogio(jogador_teste,agente_teste,mapa_teste,elogios_teste)
    else:
        print('Modo invalido, escolha 1(humilhacao) ou 2(elogio)')
    

    print(f"TEXTO GERADO:  '{resposta}'")

async def descobrir_modelos():
    print("🔍 Consultando a API do Google para listar modelos disponíveis...\n")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)



if __name__ == "__main__":
    import asyncio
    #1 = humilhacao ; 2 = elogio
    asyncio.run(testar_ia(1))