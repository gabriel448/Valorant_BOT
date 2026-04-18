import discord
from discord.ext import commands, tasks
import os
import asyncio
from dotenv import load_dotenv
from io import StringIO
from discord import app_commands
from datetime import datetime

from msg import gerar_humilhacao, gerar_elogio
from database import alterar_pontos_explanator, iniciar_banco, pegar_todos_alvos, atualizar_match_id,pegar_canais_e_cargos_do_jogador, atualizar_tier_jogador, atualizar_loss_streak
from api import pegar_partidas_recentes, obter_detalhes_partida, obter_mmr_jogador
from collections import deque
from comandos import configurar_comandos


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
        configurar_comandos(self.tree, self)
        
        # 3. Sincroniza os comandos com o Discord
        #await self.tree.sync()
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
            puuid = jogador['riot_puuid']
            ultimo_match_salvo = jogador['last_match_id']
            discord_id = jogador['discord_user_id']
            nome_jogador = jogador['riot_game_name']
            
            partidas_recentes = await pegar_partidas_recentes(puuid)
            if len(partidas_recentes) == 0:
                print('Nenhuma partida recente encontrada pela API, proximo ...')
                continue

            metadata_recente = partidas_recentes[0].get('metadata')
            if not metadata_recente or not metadata_recente.get('matchid'):
                print('Metadata corrompida ou vazia, indo para proximo jogador...')
                continue

            novo_match_id = partidas_recentes[0]['metadata']['matchid']
            
            if novo_match_id:
                #Compara se o ID mudou
                if novo_match_id != ultimo_match_salvo and novo_match_id not in cache_partidas_vistas:
                    print(f"🚨 NOVA PARTIDA DETECTADA para {nome_jogador}!")
                    print(f"Match ID antigo: {ultimo_match_salvo} | Novo: {novo_match_id}")
                    
                    novas_partidas = []
                    for partida in partidas_recentes:
                        # O .get() puxa o metadata. Se a chave não existir ou for nula, a variável vira None silenciosamente.
                        metadata = partida.get('metadata')
                        
                        # Se não tem metadata, ou se tem metadata mas não tem o matchid dentro dele:
                        if not metadata or not metadata.get('matchid'):
                            print("Aviso: A API entregou uma partida corrompida/vazia. Ignorando...")
                            continue 
                            
                        # Agora temos 100% de certeza que metadata existe e tem um matchid seguro para comparar
                        if metadata['matchid'] == ultimo_match_salvo:
                            break # chegou onde o bot conhecia
                            
                        novas_partidas.append(partida)

                    novas_partidas.reverse()
                    streak_atual = jogador['loss_streak']
                    #Verificando as ultimas 5 partidas jogadas
                    for partida in novas_partidas:
                        if partida['metadata']['mode'] == 'Competitive':
                            time_jogador = None
                            for p in partida['players']['all_players']:
                                if p['puuid'] == puuid:
                                    time_jogador = p['team']
                                    break
                            
                            time_minusculo = time_jogador.lower()
                            if time_jogador:
                                dados_time = partida['teams'].get(time_minusculo, {})
                                rounds_ganhos = dados_time.get('rounds_won', 0)
                                rounds_perdidos = dados_time.get('rounds_lost', 0)
                                if 'has_won' in partida['teams'][time_minusculo]:
                                    venceu = partida['teams'][time_minusculo]['has_won']
                                    if venceu:
                                        streak_atual = 0
                                    elif rounds_ganhos == rounds_perdidos:
                                        print(f"[{nome_jogador}] Empate/Remake detectado ({rounds_ganhos} a {rounds_perdidos}). Loss streak ignorada.")
                                    else:
                                        streak_atual += 1
                                else:
                                    print("Erro: 'has_won' nao eh um item de partida")
                    


                    # Atualiza o match id e a loss streak no banco de dados
                    await atualizar_loss_streak(puuid, streak_atual)
                    print(f"Lossstreak atualizado para {nome_jogador}")
                    await atualizar_match_id(puuid, novo_match_id)
                    print(f"Match id atualizado para {nome_jogador}")
                    dados_partida = await obter_detalhes_partida(novo_match_id)
                    try:
                        modo = dados_partida['data']['metadata']['mode']
                    except:
                        modo = None
                    if modo != "Competitive":
                        print(f"Era apenas um {modo}")
                    elif dados_partida:
                        # Pega a duração da partida em rounds 
                        rounds_jogados = dados_partida['data']['metadata']['rounds_played']
                        
                        # Procura o jogador dentro da lista de jogadores da partida 
                        estatisticas_alvo = None
                        for player in dados_partida['data']['players']['all_players']:
                            if player['puuid'] == puuid:
                                estatisticas_alvo = player
                                break
                        
                        # Se achou o jogador na partida, vamos julgar os dados 
                        if estatisticas_alvo:
                            kills = estatisticas_alvo['stats']['kills']
                            deaths = estatisticas_alvo['stats']['deaths']
                            assists = estatisticas_alvo['stats']['assists']

                            #Precisao de tiro
                            
                            headshots = estatisticas_alvo['stats']['headshots']
                            bodyshots = estatisticas_alvo['stats']['bodyshots']
                            legshots = estatisticas_alvo['stats']['legshots']

                            #Prevencao de divisao por zero 
                            total_tiros = headshots + bodyshots + legshots
                            porcentagem_peito = (bodyshots / total_tiros * 100) if total_tiros > 0 else 0
                            
                            # Proteção estrutural: Evita erro de divisão por zero se ele não morreu nenhuma vez [cite: 103]
                            kd_ratio = kills / deaths if deaths > 0 else kills
                            
                            #logica de perdoar os snipers
                            armas_perdoadas = ["Operator", "Outlaw", "Marshal", "Tour De Force"]
                            kills_com_armas_perdoadas = 0
                            kill_events = dados_partida.get('data', {}).get('kills', [])
                            
                            for kill in kill_events:
                                if kill.get('killer_puuid') == puuid:
                                    arma_usada = kill.get('weapon_name')
                                    if arma_usada in armas_perdoadas:
                                        kills_com_armas_perdoadas += 1

                            e_mono_sniper = False
                            if kills > 0:
                                porcentagem_kills_sniper = (kills_com_armas_perdoadas/kills) * 100
                                if porcentagem_kills_sniper >= 50:
                                    e_mono_sniper = True
                                    print(f"[{nome_jogador}] Ganhou perdao de Sniper: {porcentagem_kills_sniper:.1f}% das kills.")


                            #elo apos o jogo
                            dados_mmr = await obter_mmr_jogador(puuid)

                            #elo no banco de dados
                            elo_banco_int = jogador['current_tier_int']

                            
                            punitivo = False
                            motivos_punicao = []

                            merece_elogio = False
                            motivos_elogio = []
                            rank_up = False
                            elo_imagem = None
                            
                            if dados_mmr and 'data' in dados_mmr:
                                elo_atual_int = dados_mmr['data']['currenttier']
                                elo_atual_nome = dados_mmr['data']['currenttierpatched']
                                elo_imagem = dados_mmr.get('data', {}).get('images', {}).get('large')

                            if elo_banco_int == 0:
                                #primeira vez que o bot ve esse cara jogar. apenas salva no banco de dados o elo "novo"
                                print(f"[{nome_jogador}] Elo base registrado: {elo_atual_nome} ({elo_atual_int})")

                            #----REGRAS DE PUNICAO----
                            elif elo_atual_int < elo_banco_int:
                                punitivo = True
                                motivos_punicao.append(f'Caiu pro {elo_atual_nome} kkk')
                            
                            if elo_atual_int != elo_banco_int:
                                await atualizar_tier_jogador(puuid, elo_atual_int)

                            if rounds_jogados >= 10 and kills == 0:
                                punitivo = True
                                motivos_punicao.append(f"jogou {rounds_jogados} rounds e fez ZERO abates.")
                                
                            elif kd_ratio <= 0.5:
                                punitivo = True
                                motivos_punicao.append(f"K/D de {kd_ratio:.2f} ({kills}/{deaths}/{assists}).")
                            
                            if streak_atual >=4:
                                punitivo = True
                                motivos_punicao.append(f'{streak_atual} derrotas seguidas e contando')

                            if porcentagem_peito >= 84 and not e_mono_sniper:
                                punitivo = True
                                motivos_punicao.append(f'**{porcentagem_peito:.1f}%** dos tiros foi no peito')
                            
                            #----REGRAS DE ELOGIO----
                            if elo_atual_int > elo_banco_int and elo_banco_int != 0:
                                rank_up = True
                                merece_elogio = True
                                motivos_elogio.append(f'subiu pro {elo_atual_nome}')

                            if kd_ratio >= 2.0 and kills >= 20:
                                merece_elogio = True
                                motivos_elogio.append(f'K/D de {kd_ratio:.2f} ({kills}/{deaths}/{assists}).')

                            foto_agente = None
                            banner_jogador = None
                            nome_agente = None
                            mapa = None
                            destinos = None
                            if punitivo or merece_elogio:
                                foto_agente = estatisticas_alvo['assets']['agent']['small']
                                banner_jogador = estatisticas_alvo['assets']['card']['wide']
                                nome_agente = estatisticas_alvo['character']
                                mapa = dados_partida['data']['metadata']['map']

                                destinos = await pegar_canais_e_cargos_do_jogador(discord_id)
                            # se ele deve ser punido que assim seja
                            if punitivo:
                                await alterar_pontos_explanator(puuid, 1)

                                print("Gerando texto com a IA...")
                                
                                msg = StringIO()
                                for m in motivos_punicao:
                                    msg.write(f"- {m}\n")
                                
                                if not destinos:
                                    print(f"O jogador {nome_jogador} fez vexame, mas nenhum servidor tem canal configurado.")
                                
                                embeds_gerados = {}

                                for destino in destinos:
                                    id_canal = destino['canal']
                                    id_cargo = destino['cargo']
                                    modo_ia = destino['modo_ia']

                                    if not id_canal:
                                        print(f'Cargo configurado mas canal nao configurado')
                                        continue
                                    
                                    if modo_ia not in embeds_gerados:
                                        print(f"Gerando IA e montando o Embed do Modo {modo_ia} para {nome_jogador}...")
                                        
                                        # 1. Gera o texto na IA
                                        texto_ia = await gerar_humilhacao(nome_jogador, nome_agente, mapa, motivos_punicao, modo_ia)
                                        
                                        # 2. Constrói o Embed UMA ÚNICA VEZ para este modo
                                        embed = discord.Embed(
                                            title="🚨 ALERTA DE BAGRE 🚨",
                                            description=texto_ia,
                                            color=0xFF0000 
                                        )
                                            
                                        embed.add_field(name="Ficha Criminal:", value=msg.getvalue(), inline=False)
                                        embed.add_field(name="K / D / A", value=f"{kills} / {deaths} / {assists}", inline=True)
                                        embed.set_thumbnail(url=foto_agente)
                                        embed.set_image(url=banner_jogador)  
                                        
                                        # 3. Salva o Embed prontinho no Cache!
                                        embeds_gerados[modo_ia] = embed

                                    try:
                                        canal = await client.fetch_channel(int(id_canal))

                                        #monta o texto de mecao de forma inteligente
                                        texto_ping = f"<@{discord_id}>"
                                        if id_cargo:
                                            texto_ping += f"<@&{id_cargo}>"
                                        
                                        await canal.send(content=texto_ping, embed=embeds_gerados[modo_ia])
                                        print(f"Notificação de punição enviada para {nome_jogador} (Modo {modo_ia}) no canal {id_canal}!!")   
                                    except discord.errors.NotFound:
                                        print(f"Erro: O canal com ID {id_canal} foi deletado.")
                                    except discord.errors.Forbidden:
                                        print(f"Erro: Sem permissão no canal {id_canal}.")
                            if merece_elogio:
                                await alterar_pontos_explanator(puuid, -1)

                                texto_ia_elogio = await gerar_elogio(nome_jogador, nome_agente, mapa, motivos_elogio)

                                msg_elogio = StringIO()
                                for m in motivos_elogio:
                                    msg_elogio.write(f"- {m}\n")
                                
                                for destino in destinos:
                                    id_canal = destino['canal']
                                    id_cargo = destino['cargo']
                                    if not id_canal: continue
                                    
                                    # Design do Embed de Elogio
                                    embed_vitoria = discord.Embed(
                                        description=texto_ia_elogio,
                                        color=0xFFD700 # Cor Dourada (Gold)
                                    )
                                    embed_vitoria.add_field(name="Feitos:", value=msg_elogio.getvalue(), inline=False)
                                    
                                    # Se subiu de elo, o título é especial e a foto principal é o novo Rank
                                    if rank_up and elo_imagem:
                                        embed_vitoria.title = "🎉 SUBIU DE ELO 🎉"
                                        embed_vitoria.set_thumbnail(url=elo_imagem) 
                                        embed_vitoria.set_image(url=banner_jogador)
                                    else:
                                        # Se foi só K/D bom, foto do agente padrão
                                        embed_vitoria.title = "🔥 ALERTA TOPII 🔥"
                                        embed_vitoria.set_thumbnail(url=foto_agente)
                                    
                                    try:
                                        canal = await client.fetch_channel(int(id_canal))
                                        # Para elogios, decidi pingar só a pessoa, e não o cargo do servidor inteiro, 
                                        # mas você pode adicionar o <@&cargo> se quiser fazer barulho!
                                        await canal.send(content=f"<@{discord_id}> <@&{id_cargo}>", embed=embed_vitoria)
                                    except Exception as e:
                                        print(f"Erro ao enviar elogio: {e}")
                                
                                # Pequena pausa para evitar rate limit do Discord
                                await asyncio.sleep(5)
                                        
                            else:
                                print(f"{nome_jogador} jogou bem (ou medianamente). Nenhuma punição necessária.")
                            await asyncio.sleep(5)
                        
                else:
                    # Nenhuma partida nova ocorreu
                    print(f"Nenhuma nova partida para {nome_jogador}")
                    pass 
                
            await asyncio.sleep(1.5)

        # Atualiza o status do bot no Discord para mostrar que ele está vivo
        agora = datetime.now().strftime("%H:%M")
        atividade = discord.Activity(
            type=discord.ActivityType.watching, 
            name=f"{len(jogadores)} alvos | Última checagem: {agora}"
        )
        await client.change_presence(status=discord.Status.online, activity=atividade)

        segundos = 15
        print(f'Ciclo de sondagem terminado esperando {segundos}')
        await asyncio.sleep(segundos)

#roda o bota com o token que esta no .env
if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')

    if not token:
        print("🚨 ERRO CRÍTICO: O Docker não conseguiu ler o DISCORD_TOKEN do arquivo .env!")
    else:    
        token_limpo = token.strip()
        client.run(token_limpo)