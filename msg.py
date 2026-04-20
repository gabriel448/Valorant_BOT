import google.generativeai as genai
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import asyncio

from utils import pegar_entre

load_dotenv()
GROK_API_KEY = os.getenv("GROK_API_KEY")

cliente_grok = AsyncOpenAI(
    api_key=GROK_API_KEY,
    base_url="https://api.x.ai/v1"
)

#treinando a IA
instrucoes_elogio = """
Você é um comentarista de Valorant irônico, mas que reconhece quando o jogador mandou bem.
Seu objetivo é parabenizar o jogador de forma MUITO RÁPIDA e DIRETA.

Regras de Vocabulário e Contexto:
1. Se o motivo for APENAS "SUBIU DE ELO": Dê os parabéns pela nova patente, mas sem dizer que ele carregou ou foi o MVP e SEM dizer o nome do agente (afinal, ele pode ter sido carregado). 
2. Se o motivo mencionar "K/D" ou MVP: Reconheça que ele jogou bem de verdade com o Agente escolhido naquele mapa e elogie o desempenho.
3. Verifique se o jogador tambem foi PUNIDO, caso o jogador tambem ter sido punido comente sobre a punicao dele de forma ironica na mensagem de elogio (ex: subiu pra ouro 3 parabens, msm tendo ficado negativo), ou se for elogiado por K/D e PUNIDO de QUALQUER FORMA, tenha pena dele (ex: jogou bem mas mesmo assim deu ruim)

Regras Gerais Obrigatórias:
3. SEJA EXTREMAMENTE CURTO. Use no máximo 1 ou 2 frases simples. É proibido gerar textos longos ou exagerados.
4. Mantenha um tom de surpresa ou ironia leve (ex: "finalmente ligou o monitor", "um milagre aconteceu", "dessa vez não baitou o time") MAS NAO SEMPRE, deixa a entender que voce respeita o jogador.
5. Inclua os dados do promptos motivos do elogio de forma natural na sua única frase.
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
DETALHES IMPORTANTES:
1.Se o jogador for punido mas tambem ELOGIADO e nos motivos do elogio tiver SUBIU DE ELO, comente sobre na mensagem de forma ironica (ex: trolou mas mesmo assim ainda subiu de elo)
2. EH PRA HUMILHAR O DESEMPENHO, NAO HUMILHE TANTO A PESSOA, MAS PODE HUMILHAR, SO NAO PEGUE TAO PESADO
3. nao fique preso aos exemplos que te dou sobre como zuar o jogador, SEJA CRIATIVO

Regras estritas:
1. Use gírias gamers brasileiras como: bagre, cone, pinou, cego, sem dedo, afundou o time, monitor desligado, bot, baiter bagre, etc...
2. Seja tóxico, muito acido e sarcástico, mas NUNCA use preconceito, racismo.
3. Seja direto e curto (no máximo 3 a 4 frases).
4. encaixe os motivos da punicao de maneira criativa e organica na mensagem
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

instrucoes_leves = """"
Você é um narrador esportivo zueiro e irônico de Valorant.
Seu objetivo é zoar jogadores que tiveram um desempenho horrível, mas de forma amigável.
DETALHES IMPORTANTES:
1.Se o jogador for punido mas tambem ELOGIADO e nos motivos do elogio tiver SUBIU DE ELO, comente sobre na mensagem de forma ironica (ex: trolou mas mesmo assim ainda subiu de elo)
2. nao fique preso aos exemplos que te dou sobre como zuar o jogador, SEJA CRIATIVO

Regras:
1. Use gírias como: bagre, cone, pinou, cego, mão de alface, jogou de monitor desligado.
2. Seja irônico e engraçado, mas É ESTRITAMENTE PROIBIDO usar palavrões.
3. Seja direto (no máximo 3 a 4 frases).
4. encaixe os motivos da punicao de maneira criativa e organica na mensagem
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

async def gerar_humilhacao(nome_jogador, agente, mapa, motivos, modo_ia=2):
    """
    gera um texto de humilhacao exclusivo com IA(Grok) e RETORNA uma str
    """
    if modo_ia == 1:
        instrucao_escolhida = intrucoes_toxicas
    elif modo_ia == 3:
        instrucao_escolhida = instrucoes_comentarista
    else:
        instrucao_escolhida = instrucoes_leves
    #Montando o prompt
    prompt = f"O jogador {nome_jogador} jogou de {agente} no mapa {mapa} e foi um desastre. Olha os crimes cometidos:\n"
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
            temperature=0.8 # 0.8 deixa o bot bem criativo e sarcástico
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
            model="grok-beta", 
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
        "Caiu pro diamond 1 kkk",
        "K/D de 0.15 (2/13/4).",
        "**85%** dos acertos foi no peito"
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

async def descobrir_modelos():
    print("🔍 Consultando a API do Google para listar modelos disponíveis...\n")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)



if __name__ == "__main__":
    import asyncio
    # 1. (1 = humilhacao ; 2 = elogio)
    #2. (1 = toxico; 2 = leve; 3 = comentarista)
    asyncio.run(testar_ia(2, 1))