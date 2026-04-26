import discord

import os
import asyncio
from dotenv import load_dotenv
from discord import app_commands
import time
import random

from database import alterar_pontos_explanator, iniciar_banco, pegar_todos_alvos, pegar_canais_e_cargos_do_jogador, atualizar_match_id
from api import pegar_partidas_recentes, obter_detalhes_partida
from collections import deque
from comandos import configurar_comandos
from utils import atualizar_status_discord, verificar_ultimas_partidas, pegar_dados_do_jogador,pegar_dados_do_elo,verificar_regras_punicao, verificar_regras_elogio, pegar_dados_para_o_embed, enviar_embeds, avisos_ativos
from msg import gerar_resposta_rebate


# Cria uma memória global que guarda os últimos 500 Match IDs que o bot viu
cache_partidas_vistas = deque(maxlen=500)

#pega o token do bot
load_dotenv()

class MeuBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # 2. Chama a função instaladora passando a árvore (tree) e o bot (self)
        configurar_comandos(self.tree, self, cache_partidas_vistas)
        
        # 3. Sincroniza os comandos com o Discord
        await self.tree.sync()
        print("✅ Comandos carregados e sincronizados com sucesso!")

client = MeuBot()

#eventos depois do bot ligar
@client.event
async def on_ready():
    #inicia o banco de dados
    await iniciar_banco()

    # Alimenta a memória do bot com as últimas partidas do banco de dados
    jogadores = await pegar_todos_alvos()
    for jogador in jogadores:
        if jogador['last_match_id']:
            cache_partidas_vistas.append(jogador['last_match_id'])

    print(f'Sucesso - Bot {client.user.name} acordou e esta online no Discord')
    print('Aguardando informacaoes')

    client.loop.create_task(monitoramento_continuo())#COMENTE ESSA LINHA CASO ESTEJA FAZENDO APENAS TESTES


async def monitoramento_continuo():
    await client.wait_until_ready()
    while not client.is_closed():
        print("🔄 Iniciando ciclo de sondagem (Consulta Rasa)...")
        
        jogadores = await pegar_todos_alvos()
        
        for jogador in jogadores:
            try:

                puuid = jogador['riot_puuid']
                ultimo_match_salvo = jogador['last_match_id']
                discord_id = jogador['discord_user_id']
                nome_jogador = jogador['riot_game_name']
                streak_atual = jogador['loss_streak']

                partidas_recentes = await pegar_partidas_recentes(puuid)
                if len(partidas_recentes) == 0:
                    print('Nenhuma partida recente encontrada pela API, proximo ...')
                    continue
                
                partidas_nao_vistas = []
                for partida in partidas_recentes:
                    mid = partida.get('metadata', {}).get('matchid')
                    if not mid: continue
                    
                    # Chegou na última partida que o bot conhece
                    if mid == ultimo_match_salvo or mid in cache_partidas_vistas:
                        break
                    partidas_nao_vistas.append(partida)

                if len(partidas_nao_vistas) == 0:
                    print(f"Nenhuma nova partida para {nome_jogador}")
                    # Guarda as 5 últimas no cache pra caso a API dê lag no restart
                    for p in partidas_recentes:
                        mid = p.get('metadata', {}).get('matchid')
                        if mid and mid not in cache_partidas_vistas:
                            cache_partidas_vistas.append(mid)
                    await asyncio.sleep(1.5)
                    continue
                print(f"🚨 NOVA PARTIDA DETECTADA para {nome_jogador}!")


                #Pega a partida MAIS ANTIGA dentro das novas para ler na ordem cronológica correta
                partida_alvo = partidas_nao_vistas[-1]
                novo_match_id = partida_alvo['metadata']['matchid']
                print(f"Match ID antigo: {ultimo_match_salvo} | Novo: {novo_match_id}")

                # Atualiza o banco e o cache com ELA (no próximo loop, ele avança pra mais recente se tiver)
                await atualizar_match_id(puuid, novo_match_id)
                print(f"Match id atualizado para {nome_jogador}")
                cache_partidas_vistas.append(novo_match_id)
                
                dados_ultimas_partidas = {
                    'partidas_recentes': partidas_recentes,
                    'ultimo_match_salvo': ultimo_match_salvo,
                    'puuid': puuid,
                    'nome_jogador': nome_jogador,
                    'streak_atual': streak_atual,
                    'cache_partidas_vistas': cache_partidas_vistas
                }

                #olha as ultimas 5 partidas pra atualizar o losstreak
                await verificar_ultimas_partidas(dados_ultimas_partidas)

                dados_partida = await obter_detalhes_partida(novo_match_id)

                try:
                    modo = dados_partida['data']['metadata']['mode']
                except:
                    modo = None

                if modo != "Competitive":
                    print(f"Era apenas um {modo}")
                    continue
                
                if not dados_partida:
                    print(f'Erro: dados da partida do jogador {nome_jogador} Nulos')
                    continue
                
                #pega informacoes do desempenho do jogador na partida para serem julgadas
                dados_jogador = await pegar_dados_do_jogador(dados_partida, puuid, jogador)
                
                if not dados_jogador:
                    print(f'Erro: dados do jogador {nome_jogador} Nulos')
                    continue
                
                #pega informacoes do elo do jogador, como imagem, nome etc...
                dados_elo = await pegar_dados_do_elo(dados_jogador['dados_mmr'])
                
                if not dados_elo:
                    print(f'Erro: nao foi possivel pegar os dados do elo do jogador {nome_jogador}')
                    continue

                if dados_jogador['elo_banco_int'] == 0:
                    #primeira vez que o bot ve esse cara jogar. apenas salva no banco de dados o elo "novo"
                    print(f"[{nome_jogador}] Elo base registrado: {dados_elo['elo_atual_nome']} ({dados_elo['elo_atual_int']})")
                
                #verifica se ele cometeu algum crime, e devolve um dicionario com o relatorio pra gerar a humilhacao
                punicao = await verificar_regras_punicao(dados_elo, dados_jogador, streak_atual)

                #verifica se ele jogou bem e devolve um dicionario ralatorio pra gerar o elogio
                elogio = await verificar_regras_elogio(dados_elo,dados_jogador)

                if punicao['punitivo'] or elogio['merece_elogio']:
                    #pega alguns elementos visuais e escritos pra montar o embed pro discord
                    dados_embed = pegar_dados_para_o_embed(dados_jogador,dados_partida)
                    
                    destinos = await pegar_canais_e_cargos_do_jogador(discord_id)

                    #ajusta a pontuacao do rank do explanator no banco de dados
                    if punicao['punitivo']:
                        await alterar_pontos_explanator(puuid, 1)
                    if elogio['merece_elogio']:
                        await alterar_pontos_explanator(puuid, -1)
                    
                    if not destinos:
                            print(f"O jogador {nome_jogador} fez vexame, mas nenhum servidor tem canal configurado.")  

                    dados_envio = {
                        'destinos': destinos,
                        'discord_id': discord_id,
                        'dados_jogador': dados_jogador,
                        'nome_jogador': nome_jogador,
                        'dados_embed' : dados_embed,
                        'punicao': punicao,
                        'elogio': elogio,
                        'client': client
                    }

                    #aqui faz bastante coisa, pega todos os canais que eh pra mandar o aviso, gera os tipos de embeds necessarios
                    #depois envie pra todos os canais
                    await enviar_embeds(dados_envio)       
                        
                else:
                    print(f"{nome_jogador} jogou bem (ou medianamente). Nenhuma punição necessária.")
                await asyncio.sleep(5)

            except Exception as e:
                print(f"Erro inesperado ao processar {nome_jogador}: {e}")
                continue
    
        # Atualiza o status do bot no Discord para mostrar que ele está vivo
        await atualizar_status_discord(client, jogadores)
        

        segundos = 15
        print(f'Ciclo de sondagem terminado esperando {segundos}')
        await asyncio.sleep(segundos)

@client.event
async def on_message(message):
    # 1. Ignora se a mensagem for do próprio bot
    if message.author == client.user:
        return

    # 2. Verifica se o usuário está respondendo a alguma mensagem (Reply)
    if message.reference is not None:
        msg_id_referencia = message.reference.message_id
        
        # 3. Verifica se a mensagem respondida é um aviso recente do Explanator
        if msg_id_referencia in avisos_ativos:
            aviso = avisos_ativos[msg_id_referencia]
            agora = time.time()
            
            # 4. Verifica se já se passaram 5 minutos (300 segundos)
            if agora - aviso["tempo"] > 300:
                #Apaga da memória para economizar espaço
                del avisos_ativos[msg_id_referencia]
                return # Ignora silenciosamente
                
            # 5. Lógica de Interações (2 chances)
            user_id = message.author.id
            
            # Pega quantas vezes esse usuário já respondeu a ESTE aviso (começa com 0)
            vezes_respondidas = aviso["interacoes"].get(user_id, 0)
            
            if vezes_respondidas == 0:
                # PRIMEIRA CHANCE: O Bot argumenta de volta
                aviso["interacoes"][user_id] = 1 # Atualiza o contador
                
                # Mostra o status "Digitando..." no Discord
                async with message.channel.typing():
                    await asyncio.sleep(1)
                    resposta_ia = await gerar_resposta_rebate(message.author.name, message.content, aviso["contexto"])

                    msg_resposta_bot = await message.reply(resposta_ia)
                    
                    avisos_ativos[msg_resposta_bot.id] = aviso
            elif vezes_respondidas == 1:
                # SEGUNDA CHANCE: O Bot ignora com deboche
                aviso["interacoes"][user_id] = 2 # Atualiza o contador
                
                emojis_deboche = ["💤", "🥱", "🤡", "🤫", "😴"]
                emoji_escolhido = random.choice(emojis_deboche)
                
                # manda um emoji como resposta
                await message.reply(emoji_escolhido)
                
            else:
                # TERCEIRA EM DIANTE: Ignora totalmente (Shadowban do aviso)
                pass

    # Garante que os comandos de barra (/) continuem funcionando!
    await client.process_commands(message)

#roda o bota com o token que esta no .env
if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')

    if not token:
        print("🚨 ERRO CRÍTICO: O Docker não conseguiu ler o DISCORD_TOKEN do arquivo .env!")
    else:    
        token_limpo = token.strip()
        client.run(token_limpo)