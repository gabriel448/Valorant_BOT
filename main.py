import discord
from discord.ext import commands, tasks
import os
import asyncio
from dotenv import load_dotenv
from io import StringIO
from discord import app_commands
import aiohttp

from msg import gerar_humilhacao, gerar_elogio
from database import pegar_top_bagres,alterar_pontos_explanator,pegar_dono_do_alvo,configurar_modo_ia,iniciar_banco,remover_alvo_bd, configurar_cargo_alerta, pegar_todos_canais_configurados, cadastrar_alvo_bd, pegar_todos_alvos, atualizar_match_id,pegar_canais_e_cargos_do_jogador,configurar_canal_alerta, atualizar_tier_jogador, atualizar_loss_streak
from api import obter_puuid_henrik, pegar_partidas_recentes, obter_detalhes_partida, obter_mmr_jogador
from collections import deque
from imagem_builder import criar_imagem_leaderboard
from utils import calcular_elo_explanator

# Cria uma memória global que guarda os últimos 500 Match IDs que o bot viu
cache_partidas_vistas = deque(maxlen=500)

#pega o token do bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')

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

    # Alimenta a memória do bot com as últimas partidas do banco de dados
    jogadores = await pegar_todos_alvos()
    for jogador in jogadores:
        if jogador['last_match_id']:
            cache_partidas_vistas.append(jogador['last_match_id'])

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
    await interaction.response.defer()

    #pega o ID do server
    id_servidor = interaction.guild.id
    id_canal = interaction.channel.id

    #salva no banco de dados
    await configurar_canal_alerta(id_servidor, id_canal)

    await interaction.followup.send(f"✅ **Canal Configurado!** O Explanator agora enviará os alertas de exclusivamente neste canal: <#{id_canal}>.")

@ativar_esse_canal.error
async def ativar_esse_canal_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if interaction.response.is_done():
            await interaction.followup.send("❌ Você não tem permissão para isso!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Você não tem permissão para isso!", ephemeral=True)
    else:
        print(f"🚨 ERRO: {error}")

@bot.tree.command(name="patch-notes", description="[DEV] Dispara o anúncio de atualização para todos os servidores.")
async def patch_notes(interaction: discord.Interaction):
    # Só eu posso rodar isso
    MEU_ID_DISCORD = 473895740960407552
    
    if interaction.user.id != MEU_ID_DISCORD:
        await interaction.response.send_message("❌ Apenas o desenvolvedor supremo pode usar este comando.", ephemeral=True)
        return

    # Avisa ao Discord que o bot está "pensando"
    await interaction.response.defer(ephemeral=True)
    
    # montando o embed
    embed = discord.Embed(
        title="📢 PATCH NOTES!",
        description="O explanator é justo! Chegou a hora de exaltar os heróis e expor os verdadeiros bagres do servidor com a nova atualização.",
        color=0x00BFFF # Azul claro/Cyan para notas de atualização
    )
    
    # Campo 1: Elogios e Subida de Rank
    embed.add_field(
        name="🏆 1. O Sistema de elogios", 
        value="Se você destruir na partida, o explanator vai te reconhecer publicamente:\n"
              "**• Subir de Elo:** O bot comemora a sua promoção no chat com a imagem oficial do seu novo elo!\n"
              "**• Amassar o Lobby:** Fez mais de 20 abates e K/D acima de 2.0? O explanator vai te exaltar no chat.", 
        inline=False
    )
    
    # Campo 2: Leaderboard de Bagres
    embed.add_field(
        name="📉 2. O 'Anti-Rank' do Explanator (`/top-bagres`)", 
        value="A Parede da Vergonha foi inaugurada! Transformamos a ruindade em uma tabela de liderança competitiva.\n"
              "**• A Dinâmica:** Foi humilhado pelo bot? Ganha 1 ponto. Foi elogiado? Perde 1 ponto.\n"
              "**• Os Elos:** A cada 3 pontos acumulados, você sobe de Elo no nosso ranking (indo do Ferro ao Radiante do explanator).\n"
              "**• O Comando:** Use `/top-bagres` para gerar uma imagem com o Top 10 dos piores do servidor, puxando os Banners do jogo ao vivo!", 
        inline=False
    )
    
    embed.set_footer(text="Desenvolvido com ódio e Python. Bom jogo!")

    # dispara pra todos os servidores
    canais = await pegar_todos_canais_configurados()
    enviados = 0
    
    for id_canal in canais:
        try:
            canal = await bot.fetch_channel(int(id_canal))
            await canal.send(embed=embed)
            enviados += 1
        except discord.errors.NotFound:
            print(f"Canal {id_canal} não encontrado.")
        except discord.errors.Forbidden:
            print(f"Sem permissão no canal {id_canal}.")
            
    # Confirmação apenas para você
    await interaction.followup.send(f"✅ Anúncio disparado com sucesso para {enviados} servidores!")

@bot.tree.command(name="ativar-esse-cargo", description="[ADMIN] Define qual cargo será marcado nos avisos.")
@app_commands.describe(cargo="Selecione o cargo para ser marcado")
@app_commands.checks.has_permissions(administrator=True)
async def ativar_esse_cargo(interaction: discord.Interaction, cargo: discord.Role):
    await interaction.response.defer()

    id_servidor = interaction.guild.id
    id_cargo = cargo.id
    
    sucesso = await configurar_cargo_alerta(id_servidor, id_cargo)
    
    if sucesso:
        await interaction.followup.send(f"✅ **cargo configurado** O bot agora vai marcar o cargo {cargo.mention} nos alertas de bagre deste servidor.")
    else:
        await interaction.followup.send("❌ **Calma lá!** Você precisa configurar o canal primeiro usando `/ativar-esse-canal` antes de tentar definir um cargo.")
        print("Erro: Canal não estava configurado.")

@ativar_esse_cargo.error
async def ativar_esse_cargo_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if interaction.response.is_done():
            await interaction.followup.send("❌ Você não tem permissão para isso!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Você não tem permissão para isso!", ephemeral=True)
    else:
        print(f"🚨 ERRO: {error}")

@bot.tree.command(name='remover-alvo', description="Remove um jogador do monitoramento do Tribunal." )
@app_commands.describe(riot_id="O Riot ID do jogador (ex: Sacy#BR1)")
async def remover_alvo(interaction: discord.Interaction, riot_id: str):
    #evitando timeout
    await interaction.response.defer()

    try:
        nome, tag = riot_id.split('#')
    except ValueError:
        await interaction.followup.send("⚠️ Formato inválido! Você precisa usar Nome#Tag (ex: Sacy#BR1).")
        return
    
    dono_id = await pegar_dono_do_alvo(nome, tag)

    if not dono_id:
        await interaction.followup.send(f"❌ Não encontrei nenhum jogador com o Riot ID **{riot_id}** no banco de dados.", ephemeral=True)
        return
    
    # Verifica se a pessoa executando o comando é Administradora do servidor
    eh_admin = interaction.user.guild_permissions.administrator

    # Verifica se a pessoa executando o comando é a mesma que foi cadastrada no banco
    eh_o_dono = (interaction.user.id == dono_id)

    if not (eh_admin or eh_o_dono):
        await interaction.followup.send("❌ **Acesso Negado!** Você só pode remover a SUA PRÓPRIA conta do monitoramento (ou pedir para um Administrador fazer isso).", ephemeral=True)
        return
    #apaga do banco
    sucesso = await remover_alvo_bd(nome, tag)

    if sucesso:
        quem_removeu = "O administrador" if eh_admin and not eh_o_dono else "O próprio jogador"
        await interaction.followup.send(f"✅ **Alvo Abortado!** {quem_removeu} removeu os registros de **{riot_id}**. Ele não será mais explanado.")
        print(f"Jogador {riot_id} deletado do banco por {interaction.user.name}.")
    else:
        await interaction.followup.send(f"❌ Não encontrei nenhum jogador com o Riot ID **{riot_id}** no banco de dados. Tem certeza que o nome e a tag estão certos?", ephemeral=True)
@remover_alvo.error
async def remover_alvo_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if interaction.response.is_done():
            await interaction.followup.send("❌ Somente administradores podem perdoar um bagre e remover ele do sistema!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Somente administradores podem perdoar um bagre e remover ele do sistema!", ephemeral=True)
    else:
        print(f"🚨 ERRO NO COMANDO DE REMOVER: {error}")

@bot.tree.command(name="modo-ia", description="[ADMIN] Define a personalidade da IA neste servidor.")
@app_commands.describe(nivel="Escolha o nível de toxicidade")
@app_commands.choices(nivel=[
    app_commands.Choice(name="1 - Tóxico / Pesado ", value=1),
    app_commands.Choice(name="2 - Leve / Family Friendly", value=2),
    app_commands.Choice(name="3 - Comentarista / Analítico", value=3)
])
@app_commands.checks.has_permissions(administrator=True)
async def modo_ia_cmd(interaction: discord.Interaction, nivel: app_commands.Choice[int]):
    #evitando o timeout
    await interaction.response.defer()

    id_servidor = interaction.guild.id
    valor_escolhido = nivel.value

    sucesso = await configurar_modo_ia(id_servidor,valor_escolhido)

    if sucesso:
        tipo = ''
        if valor_escolhido == 1:
            tipo = "TÓXICO ☢️"
        elif valor_escolhido == 3:
            tipo = "COMENTARISTA 🎙️"
        else:
            tipo = "LEVE 🕊️"
        await interaction.followup.send(f"✅ **Modo alterado!** A IA neste servidor agora operará no modo **{tipo}**.")
    else:
        await interaction.followup.send("❌ Você precisa configurar o `/ativar-esse-canal` primeiro!")

@bot.tree.command(name="top-explanados", description="Exibe o ranking dos maiores bagres deste servidor (Rank Explanator).")
async def top_bagres(interaction: discord.Interaction):
    await interaction.response.defer()

    # 1. Busca os dados no banco
    top_jogadores = await pegar_top_bagres(interaction.guild.id)
    
    if not top_jogadores:
        await interaction.followup.send("📭 Nenhum jogador cadastrado neste servidor ainda.")
        return

    lista_para_imagem = []
    
    async with aiohttp.ClientSession() as session:
        async with session.get("https://valorant-api.com/v1/competitivetiers") as resp:
            if resp.status == 200:
                dados_tiers = await resp.json()
                # O [-1] pega a temporada competitiva mais recente!
                temporada_atual = dados_tiers['data'][-1]['tiers'] 
            else:
                temporada_atual = []
    
    # 2. Prepara os dados e busca assets (Banner e Ícone do Anti-Rank)
    for jogador in top_jogadores:
        puuid = jogador['riot_puuid']
        pontos = jogador['pontos_explanator']
        nome_completo = f"{jogador['riot_game_name']}"
        
        # Calcula o rank do Explanator
        rank_nome = calcular_elo_explanator(pontos)
        
        # Buscamos o Banner atual do jogador na API do Henrik
        # Usamos o endpoint de conta para pegar o banner (card)
        url_conta = f"https://api.henrikdev.xyz/valorant/v1/by-puuid/account/{puuid}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url_conta, headers={"Authorization": HENRIK_API_KEY}) as resp:
                banner_url = "https://media.valorant-api.com/playercards/fc209787-414b-10d0-dcac-048323c8f59b/wideart.png" # Banner padrão caso falhe
                if resp.status == 200:
                    dados = await resp.json()
                    banner_url = dados['data']['card']['wide']

        # Mapeamento simples de Rank para ID de ícone (valorant-api.com)
        # O índice do rank (pontos // 3) + 3 costuma bater com os IDs da API (Ferro 1 = 3, etc)
        indice_api = (pontos // 3) + 3 
        if indice_api > 27: indice_api = 27 # Limite do Radiante
        icon_url = None
        if temporada_atual and indice_api < len(temporada_atual):
            icon_url = temporada_atual[indice_api].get('largeIcon')

        lista_para_imagem.append({
            'nome': nome_completo,
            'rank': rank_nome,
            'banner_url': banner_url,
            'icon_url': icon_url
        })

    # 3. Chama o construtor de imagem que você definiu
    try:
        imagem_final = await criar_imagem_leaderboard(lista_para_imagem, titulo=f"RANKING EXPLANATOR - {interaction.guild.name}")
        
        # 4. Envia o arquivo para o Discord
        arquivo = discord.File(fp=imagem_final, filename="leaderboard.png")
        await interaction.followup.send(content="🏆 **TABELA DOS BAGRES:**", file=arquivo)
    except Exception as e:
        print(f"Erro ao gerar imagem: {e}")
        await interaction.followup.send("❌ Tive um problema técnico ao pintar o quadro dos bagres.")

@tasks.loop(seconds=90)
async def monitoramento_continuo():
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
                        if elo_atual_int > elo_banco_int:
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
                                    canal = await bot.fetch_channel(int(id_canal))

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
                                    canal = await bot.fetch_channel(int(id_canal))
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
            
        #Dorme 2 segundos antes de olhar o próximo jogador
        # Isso salva o bot de tomar bloqueio por Rate Limit!
        await asyncio.sleep(1.5)

#roda o bota com o token que esta no .env
if __name__ == '__main__':
    bot.run(TOKEN)