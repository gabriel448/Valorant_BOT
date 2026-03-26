import discord
from discord.ext import commands, tasks
import os
import asyncio
from dotenv import load_dotenv
from io import StringIO
from discord import app_commands

from database import iniciar_banco, cadastrar_alvo_bd, pegar_todos_alvos, atualizar_match_id,pegar_canais_alerta_do_jogador,configurar_canal_alerta, atualizar_tier_jogador
from api import obter_puuid_henrik, pegar_ultimo_match_id, obter_detalhes_partida

#pega o token do bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CANAL_DE_ALERTA_ID = os.getenv('CANAL_DE_ALERTA_ID')

#config das permissoes do bot
intents = discord.Intents.default()
intents.message_content = True #permite ler o texto das mensagens
intents.members = True #permite ver a lista de membros do servidor

#criando a instancia do bot
bot = commands.Bot(command_prefix='!', intents=intents)

#eventos depois do bot ligar
@bot.event
async def on_ready():
    #inicia o banco de dados
    await iniciar_banco()

    await bot.tree.sync()

    #liga o loop de verificacao
    if not monitoramento_continuo.is_running():
        monitoramento_continuo.start()

    print(f'Sucesso - Bot {bot.user.name} acordou e esta online no Discord')
    print('Aguardando informacaoes')

@bot.tree.command(name="cadastrar-alvo", description="Cadastra um amigo para o monitoramento de baitamento no Valorant.")
async def cadastrar_alvo(interaction: discord.Interaction, baiter: discord.Member, riot_id: str):
    
    await interaction.response.defer()
    
    try:
        nome, tag = riot_id.split('#')
    except ValueError:
        await interaction.followup.send("⚠️ Formato inválido! Você precisa usar Nome#Tag (ex: Sacy#BR1).")
        return

    # Vamos buscar o tal do PUUID na API
    puuid = await obter_puuid_henrik(nome, tag)
    
    if not puuid:
        await interaction.followup.send(f"❌ Não consegui achar o jogador **{riot_id}** na API do Valorant. Tem certeza que escreveu certo?")
        return
        
    # Se achou na API, salva no banco de dados
    await cadastrar_alvo_bd(
        discord_user_id=baiter.id, 
        guild_id=interaction.guild.id, 
        riot_puuid=puuid, 
        riot_game_name=nome, 
        riot_tag_line=tag,
    )
    
    await interaction.followup.send(f"🎯 **baiter na mira** O jogador {baiter.mention} ({riot_id}) foi cadastrado com o PUUID e será monitorado neste canal.")


@bot.tree.command(name="ativar-esse-canal", description="[ADMIN] Define este canal como o oficial para os Alertas de Bagre.")
@app_commands.checks.has_permissions(administrator=True) #so adms
async def ativar_esse_canal(interaction: discord.Interaction):

    #pega o ID do server
    id_servidor = interaction.guild.id
    id_canal = interaction.channel.id

    #salva no banco de dados
    await configurar_canal_alerta(id_servidor, id_canal)

    await interaction.response.send_message(f"✅ **Canal Configurado!** O Explanator agora enviará os alertas de exclusivamente neste canal: <#{id_canal}>.")

@ativar_esse_canal.error
async def ativar_esse_canal_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Você não tem permissão de administrador para usar este comando!", ephemeral=True)


@tasks.loop(seconds=90)
async def monitoramento_continuo():
    print("🔄 Iniciando ciclo de sondagem (Consulta Rasa)...")
    
    jogadores = await pegar_todos_alvos()
    
    for jogador in jogadores:
        puuid = jogador['riot_puuid']
        ultimo_match_salvo = jogador['last_match_id']
        discord_id = jogador['discord_user_id']
        nome_jogador = jogador['riot_game_name']
        
        # Fazemos a Consulta Rasa na API
        novo_match_id = await pegar_ultimo_match_id(puuid)
        
        if novo_match_id:
            #Compara se o ID mudou
            if novo_match_id != ultimo_match_salvo:
                print(f"🚨 NOVA PARTIDA DETECTADA para {nome_jogador}!")
                print(f"Match ID antigo: {ultimo_match_salvo} | Novo: {novo_match_id}")
                
                # Atualiza no banco para não verificarmos de novo
                await atualizar_match_id(puuid, novo_match_id)
                
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
                    
                    # Se achou o jogadoro na partida, vamos julgar os dados 
                    if estatisticas_alvo:
                        kills = estatisticas_alvo['stats']['kills']
                        deaths = estatisticas_alvo['stats']['deaths']
                        assists = estatisticas_alvo['stats']['assists']
                        
                        # Proteção estrutural: Evita erro de divisão por zero se ele não morreu nenhuma vez [cite: 103]
                        kd_ratio = kills / deaths if deaths > 0 else kills
                        
                        #elo no jogo
                        elo_atual_int = estatisticas_alvo['currenttier']
                        elo_atual_nome = estatisticas_alvo['currenttier_patched']

                        #elo no banco de dados
                        elo_banco_int = jogador['current_tier_int']

                        
                        punitivo = False
                        motivos = []
                        
                        if elo_banco_int == 0:
                            #primeira vez que o bot ve esse cara jogar. apenas salva no banco de dados o elo "novo"
                            await atualizar_tier_jogador(puuid, elo_atual_int)
                            print(f"[{nome_jogador}] Elo base registrado: {elo_atual_nome} ({elo_atual_int})")
                        elif elo_atual_int < elo_banco_int:
                            punitivo = True
                            motivos.append(f'Caiu pro {elo_atual_nome} kkk')
                        

                        # Regra 1: Gate do Zero-Kill 
                        if rounds_jogados >= 10 and kills == 0:
                            punitivo = True
                            motivos.append(f"O pacifista jogou {rounds_jogados} rounds e fez ZERO abates.")
                            
                        # Regra 2: Desastre de K/D 
                        elif kd_ratio <= 0.5:
                            punitivo = True
                            motivos.append(f"K/D de {kd_ratio:.2f} ({kills}/{deaths}/{assists}).")
                        
                        # Se ele cometeu um crime contra o Valorant, enviamos a notificação [cite: 105]
                        if punitivo:
                            msg = StringIO()
                            for motivo in motivos:
                                msg.write(f"- {motivo}\n")
                            try:
                                # Pescando as URLs das imagens e dados estéticos do JSON
                                foto_agente = estatisticas_alvo['assets']['agent']['small']
                                banner_jogador = estatisticas_alvo['assets']['card']['wide']
                                nome_agente = estatisticas_alvo['character']
                                mapa = dados_partida['data']['metadata']['map']
                                
                                # Criando o Quadro (Embed)
                                # O hexadecimal 0xFF0000 é a cor vermelha (código cromático punitivo)
                                embed = discord.Embed(
                                    title="🚨 ALERTA DE BAGRE 🚨",
                                    description=f"O baiter do {nome_jogador} jogou de **{nome_agente}** numa **{mapa}** se liga na lenda.",
                                    color=0xFF0000 
                                )
                                
                                # Adicionando os campos de texto com as estatísticas
                                embed.add_field(name="Proezas:", value=msg.getvalue(), inline=False)
                                embed.add_field(name="K / D / A", value=f"{kills} / {deaths} / {assists}", inline=True)
                                
                                # Injetando as imagens
                                embed.set_thumbnail(url=foto_agente) # Fotinha pequena no canto superior direito
                                embed.set_image(url=banner_jogador)  # Imagem grande esticada no fundo
                                
                                canais_ids = await pegar_canais_alerta_do_jogador(discord_id)

                                if not canais_ids:
                                    print(f'O jogador {nome_jogador} fez vexame, mas nenhum servidor dele tem um canal configurado')

                                cargo = 1485793489332731985
                                for id_canal in canais_ids:
                                    try:
                                         # Buscando o canal
                                        canal = await bot.fetch_channel(int(id_canal))

                                        # Enviamos o "ping" (content) solto para o Discord apitar, e anexamos o embed
                                        await canal.send(content=f"<@{discord_id}> <@&{cargo}>", embed=embed)
                                        print(f"Notificação visual enviada para {nome_jogador}!")
                                    except discord.errors.NotFound:
                                        print(f"Erro: O canal com ID {id_canal} foi deletado do servidor.")
                                    except discord.erros.Forbidden:
                                        print(f"Erro: Sem permissão para enviar mensagem no canal {id_canal}.")

                                
                                print(f"Notificação de punição enviada para {nome_jogador}!")
                                    
                            except discord.errors.NotFound:
                                # Tratamento de exceção caso você tenha deletado o canal do servidor
                                print(f"Erro: O canal com ID {CANAL_DE_ALERTA_ID} não existe mais no Discord.")
                            except discord.errors.Forbidden:
                                # Tratamento caso o bot não tenha permissão de ler/escrever naquele canal
                                print("Erro: O bot não tem permissão para enviar mensagens nesse canal.")
                        else:
                            print(f"{nome_jogador} jogou bem (ou medianamente). Nenhuma punição necessária.")
                        await asyncio.sleep(28)
                    
            else:
                # Nenhuma partida nova ocorreu
                print(f"Nenhuma nova partida para {nome_jogador}")
                pass 
            
        #Dorme 2 segundos antes de olhar o próximo jogador
        # Isso salva o bot de tomar bloqueio por Rate Limit!
        await asyncio.sleep(2)

#roda o bota com o token que esta no .env
if __name__ == '__main__':
    bot.run(TOKEN)