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
from utils import ajuste_fuso_horario, verificar_novo_match_id, verificar_ultimas_partidas, pegar_dados_do_jogador,pegar_dados_do_elo,verificar_regras_punicao, verificar_regras_elogio, pegar_dados_para_o_embed, enviar_embeds

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
            streak_atual = jogador['loss_streak']

            partidas_recentes = await pegar_partidas_recentes(puuid)
            if len(partidas_recentes) == 0:
                print('Nenhuma partida recente encontrada pela API, proximo ...')
                continue

            metadata_recente = partidas_recentes[0].get('metadata')
            if not metadata_recente or not metadata_recente.get('matchid'):
                print('Metadata corrompida ou vazia, indo para proximo jogador...')
                continue

            novo_match_id = partidas_recentes[0]['metadata']['matchid']
            
            nova_partida = await verificar_novo_match_id(novo_match_id,ultimo_match_salvo,nome_jogador,cache_partidas_vistas,puuid)

            if not nova_partida:
                pass
            
            await verificar_ultimas_partidas(partidas_recentes, ultimo_match_salvo, puuid, nome_jogador)

            dados_partida = await obter_detalhes_partida(novo_match_id)

            try:
                modo = dados_partida['data']['metadata']['mode']
            except:
                modo = None
            if modo != "Competitive":
                print(f"Era apenas um {modo}")
                pass
            
            if not dados_partida:
                pass

            dados_jogador = await pegar_dados_do_jogador(dados_partida, puuid, jogador)
            
            if not dados_jogador:
                pass

            dados_elo = await pegar_dados_do_elo(dados_jogador['dados_mmr'])
            
            if not dados_elo:
                pass

            if dados_jogador['elo_banco_int'] == 0:
                #primeira vez que o bot ve esse cara jogar. apenas salva no banco de dados o elo "novo"
                print(f"[{nome_jogador}] Elo base registrado: {dados_elo['elo_atual_nome']} ({dados_elo['elo_atual_int']})")


            punicao = await verificar_regras_punicao(dados_elo, dados_jogador, streak_atual)

            elogio = await verificar_regras_elogio(dados_elo,dados_jogador)

            if punicao['punitivo'] or elogio['merece_elogio']:

                dados_embed = pegar_dados_para_o_embed(dados_jogador,dados_partida)
                
                destinos = await pegar_canais_e_cargos_do_jogador(discord_id)

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
                    'elogio': elogio
                }
                await enviar_embeds(dados_envio)       
                            

                            
            
                            
                            
                            

                            

                            
                            
                            

                            
                            
                            

                                
                            
                                
                                
                            if merece_elogio:
                                

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
                                        await canal.send(content=f"<@{discord_id}> <@&{id_cargo}>", embed=embed_vitoria)
                                    except Exception as e:
                                        print(f"Erro ao enviar elogio: {e}")
                                
                                # Pequena pausa para evitar rate limit do Discord
                                await asyncio.sleep(5)
                                        
                            else:
                                print(f"{nome_jogador} jogou bem (ou medianamente). Nenhuma punição necessária.")
                            await asyncio.sleep(5)
                
            await asyncio.sleep(1.5)

        # Atualiza o status do bot no Discord para mostrar que ele está vivo
        agora = datetime.now().strftime("%H:%M")
        hora_correta = ajuste_fuso_horario(agora, 3)

        atividade = discord.Activity(
            type=discord.ActivityType.watching, 
            name=f"{len(jogadores)} alvos | Última checagem: {hora_correta}"
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