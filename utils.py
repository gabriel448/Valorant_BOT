from database import atualizar_match_id, atualizar_loss_streak,atualizar_tier_jogador
from api import obter_mmr_jogador
import asyncio
import discord
from msg import gerar_humilhacao, gerar_elogio
from io import StringIO
from datetime import datetime

def calcular_elo_explanator(pontos):
    """Converte os pontos do Explanator em um nome de Elo do Valorant."""
    # Lista com todos os 25 ranks do Valorant em ordem (Ferro 1 até Radiante)
    elos = [
        "Ferro 1", "Ferro 2", "Ferro 3",
        "Bronze 1", "Bronze 2", "Bronze 3",
        "Prata 1", "Prata 2", "Prata 3",
        "Ouro 1", "Ouro 2", "Ouro 3",
        "Platina 1", "Platina 2", "Platina 3",
        "Diamante 1", "Diamante 2", "Diamante 3",
        "Ascendente 1", "Ascendente 2", "Ascendente 3",
        "Imortal 1", "Imortal 2", "Imortal 3",
        "Radiante"
    ]
    
    # Divide os pontos por 3 para achar o índice. Ex: 7 pontos // 3 = 2 (Ferro 3)
    indice = pontos // 3
    
    # Se o cara for um Deus da Ruindade e passar do limite, trava no Radiante
    if indice >= len(elos):
        return elos[-1]
        
    return elos[indice]

def ajuste_fuso_horario(hora:str, diferenca:int):
    """
    Faz o ajuste do fusorario e retorna uma string com as horas ajustadas
    """
    
    if ':' in hora:
        horas, minutos = hora.split(":")
        try:
            hora_correta = (int(horas) - diferenca) % 24
            return f"{str(hora_correta).zfill(2)}:{minutos}"
        except ValueError:
            print("Erro: formato de hora inválido.")
            return None
    return None
    

async def verificar_novo_match_id(dados):
    """
    verifica se o matchID retornado pela API eh novo e se ja nao esta no cache de partidas vistas, se for realmente uma nova partida
    ele atualiza no banco de dados
    RETORNA True se for uma partida nova e False se for uma ja conhecida ou nula
    """
    novo_matchID = dados['novo_match_id']
    ultimo_match_salvo = dados['ultimo_match_salvo']
    nome_jogador = dados['nome_jogador']
    cache_partidas_vistas = dados['cache_partidas_vistas']
    puuid = dados['puuid']

    if novo_matchID:
        #Compara se o ID mudou
        if novo_matchID != ultimo_match_salvo and novo_matchID not in cache_partidas_vistas:
            print(f"🚨 NOVA PARTIDA DETECTADA para {nome_jogador}!")
            print(f"Match ID antigo: {ultimo_match_salvo} | Novo: {novo_matchID}")
            
            # Atualiza o matchID no banco de dados
            await atualizar_match_id(puuid, novo_matchID)
            print(f"Match id atualizado para {nome_jogador}")
            return True
        else:
            # Nenhuma partida nova ocorreu
            return False
    else:
        print('Erro, novo MatchID Nulo')
        return False


async def verificar_ultimas_partidas(dados):
    """
    Verifica as ultimas 5 partidas do jogador pra verificar e atualizar seu losstreak
    """

    partidas_recentes = dados['partidas_recentes']
    ultimo_match_salvo = dados['ultimo_match_salvo']
    puuid = dados['puuid']
    nome_jogador = dados['nome_jogador']
    streak_atual = dados['streak_atual']

    novas_partidas = []
    for partida in partidas_recentes:
        # O .get() puxa o metadata. Se a chave não existir ou for nula, a variável vira None silenciosamente.
        metadata = partida.get('metadata')
        
        # Se não tem metadata, ou se tem metadata mas não tem o matchid dentro dele:
        if not metadata or not metadata.get('matchid'):
            print("Aviso: A API entregou uma partida corrompida/vazia. Ignorando...")
            continue 
            
        # 100% de certeza que metadata existe e tem um matchid seguro para comparar
        if metadata['matchid'] == ultimo_match_salvo:
            break # chegou onde o bot conhecia
            
        novas_partidas.append(partida)

    novas_partidas.reverse()
    
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
    
    # Atualiza o loss streak no banco de dados
    await atualizar_loss_streak(puuid, streak_atual)
    print(f"Lossstreak atualizado para {nome_jogador}")

async def pegar_dados_do_jogador(dados_partida, puuid, jogador):
    """
    RECEBE os parametros e solta um dicionario com os dados do desempenho do jogador na partida
    """
    nome_jogador = jogador['riot_game_name']

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
        
        # Proteção estrutural: Evita erro de divisão por zero se ele não morreu nenhuma vez
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
        
        dados_jogador = {
            'estatisticas_alvo': estatisticas_alvo,
            'elo_banco_int': elo_banco_int,
            'dados_mmr': dados_mmr,
            'e_mono_sniper': e_mono_sniper,
            'kd_ratio': kd_ratio,
            'porcentagem_peito': porcentagem_peito,
            'kills': kills,
            'deaths': deaths,
            'assists': assists,
            'headshots': headshots,
            'bodyshots': bodyshots,
            'legshots': legshots,
            'rounds_jogados': rounds_jogados,
            'puuid': puuid
        }

        return dados_jogador
    print(f'Jogador {nome_jogador} nao encontrado na partida')
    return None

async def pegar_dados_do_elo(dados_mmr):
    """
    Pega os dados crus do mmr do jogador e RETORNA um dicionario com alguns dados do elo atual do jogador
    """
    elo_imagem = None
    if dados_mmr and 'data' in dados_mmr:
        elo_atual_int = dados_mmr['data']['currenttier']
        elo_atual_nome = dados_mmr['data']['currenttierpatched']
        elo_imagem = dados_mmr.get('data', {}).get('images', {}).get('large')
        if not elo_imagem:
            print('Erro ao carregar imagem do elo atual')
        dados_elo = {
            'elo_atual_int': elo_atual_int,
            'elo_atual_nome': elo_atual_nome,
            'elo_atual_imagem': elo_imagem
        }
        return dados_elo
    
    print('Erro ao pegar dados de mmr, Nulo ou sem "data"')
    return None

async def verificar_regras_punicao(dados_elo,dados_jogador,streak_atual):
    """
    Pega os dados adquiridos anteriormente e verifica se se encaixa em alguma punicao
    RETORNA um dicionario com: punitivo(bool), motivos_punicao(list[str]), motivos_punicao_IA(list[str])
    """
    punitivo = False
    motivos_punicao = []
    motivos_punicao_IA = []

    if dados_elo['elo_atual_int'] < dados_jogador['elo_banco_int']:
        punitivo = True
        motivos_punicao.append(f'Caiu pro {dados_elo["elo_atual_nome"]} kkk')
        motivos_punicao.append(f'CAIU DE ELO, AGORA O JOGADOR ESTA {dados_elo["elo_atual_nome"]}')
    
    if dados_elo['elo_atual_int'] != dados_jogador['elo_banco_int']:
        await atualizar_tier_jogador(dados_jogador['puuid'], dados_elo['elo_atual_int'])

    if dados_jogador['rounds_jogados'] >= 10 and dados_jogador['kills'] == 0:
        punitivo = True
        motivos_punicao.append(f"jogou {dados_jogador['rounds_jogados']} rounds e fez ZERO abates.")
        motivos_punicao_IA.append(f"JOGADOR JOGOU {dados_jogador['rounds_jogados']} E FEZ ZERO ABATES")
        
    elif dados_jogador['kd_ratio'] <= 0.5:
        punitivo = True
        motivos_punicao.append(f"K/D de {dados_jogador['kd_ratio']:.2f} ({dados_jogador['kills']}/{dados_jogador['deaths']}/{dados_jogador['assists']}).")
        motivos_punicao_IA.append(f"K/D de {dados_jogador['kd_ratio']:.2f} ({dados_jogador['kills']}/{dados_jogador['deaths']}/{dados_jogador['assists']}). JOGADOR OBTEVE UM PESSIMO KD NESSA PARTIDA")
    
    if streak_atual >=4:
        punitivo = True
        motivos_punicao.append(f'{streak_atual} derrotas seguidas e contando')
        motivos_punicao_IA.append(f'JOGADOR CHEGOU NA SEQUENCIA DE {streak_atual} DERRTOAS SEGUIDAS')

    if dados_jogador['porcentagem_peito'] >= 84 and not dados_jogador['e_mono_sniper']:
        punitivo = True
        motivos_punicao.append(f'**{dados_jogador["porcentagem_peito"]:.1f}%** dos tiros foi no peito')
        motivos_punicao_IA.append(f'**{dados_jogador["porcentagem_peito"]:.1f}%** DOS TIROS DADOS PELO JOGADOR NESSA PARTIDA ACERTARAM O PEITO DOS INIMIGOS, ELE NAO SABE MIRAR NA CABECA')
    
    punicao = {
        'punitivo': punitivo,
        'motivos_punicao': motivos_punicao,
        'motivos_punicao_IA': motivos_punicao_IA
    }
    return punicao
    

async def verificar_regras_elogio(dados_elo, dados_jogador):
    """
    Pega os dados adquiridos anteriormente e verifica se se encaixa em algum elogio
    RETORNA um dicionario com: merece_elogio(bool), motivos_elogio(list[str]), motivos_elogio_IA(list[str]), rank_up(bool)
    """
    merece_elogio = False
    motivos_elogio = []
    motivos_elogio_IA = []
    rank_up = False

    if dados_elo['elo_atual_int'] > dados_jogador['elo_banco_int'] and dados_jogador['elo_banco_int'] != 0:
        rank_up = True
        merece_elogio = True
        motivos_elogio.append(f'subiu pro {dados_elo["elo_atual_nome"]}')
        motivos_elogio_IA.append(f'JOGADOR SUBIU DE ELO, AGORA ESTA NO ELO {dados_elo["elo_atual_nome"]}')

    if dados_jogador['kd_ratio'] >= 2.0 and dados_jogador['kills'] >= 20:
        merece_elogio = True
        motivos_elogio.append(f"K/D de {dados_jogador['kd_ratio']:.2f} ({dados_jogador['kills']}/{dados_jogador['deaths']}/{dados_jogador['assists']}).")
        motivos_elogio_IA.append(f"K/D de {dados_jogador['kd_ratio']:.2f} ({dados_jogador['kills']}/{dados_jogador['deaths']}/{dados_jogador['assists']}). JOGADOR OBTEVE UM OTIMO KD NESSA PARTIDA, NAO FOI CARREGADO")

    elogio = {
        'merece_elogio': merece_elogio,
        'motivos_elogio': motivos_elogio,
        'motivos_elogio_IA': motivos_elogio_IA,
        'rank_up': rank_up
    }
    return elogio

def pegar_dados_para_o_embed(dados_jogador,dados_partida):
    """
    Pega os dados especificos de dados_jogador e dados_partida que servirao pra montar o embed do discord (colocando aqui pra deixar o main mais organizado)
    RETORNA um dicionario com: foto_agente(url(eu acho)), bannr_jogador(url(tbm acho)), nome_jogador(str), mapa(str)
    """

    foto_agente = None
    banner_jogador = None
    nome_agente = None
    mapa = None

    foto_agente = dados_jogador['estatisticas_alvo']['assets']['agent']['small']
    banner_jogador = dados_jogador['estatisticas_alvo']['assets']['card']['wide']
    nome_agente = dados_jogador['estatisticas_alvo']['character']
    mapa = dados_partida['data']['metadata']['map']
    elo_imagem = dados_jogador.get('dados_mmr', {}).get('data', {}).get('images', {}).get('large')
    dados_embed = {
        'foto_agente': foto_agente,
        'banner_jogador': banner_jogador,
        'nome_agente': nome_agente,
        'mapa': mapa,
        'elo_imagem': elo_imagem
    }

    return dados_embed

async def enviar_embeds(dados_envio):
    """
    pega todos os destinos da notificacao, manda fazer os embeds e depois envia
    """
    embeds_gerados = {}
    destinos = dados_envio['destinos']
    punicao = dados_envio['punicao']
    elogio = dados_envio['elogio']
    nome_jogador = dados_envio['nome_jogador']
    discord_id = dados_envio['discord_id']
    client = dados_envio['client']

    for destino in destinos:
        id_canal = destino['canal']
        id_cargo = destino['cargo']
        if not id_canal : continue
        modo_ia = destino['modo_ia']
        modo = None

        if not id_canal:
            print(f'Cargo configurado mas canal nao configurado')
            continue
        
        if punicao['punitivo']:
            msg = StringIO()
            for m in punicao['motivos_punicao']:
                msg.write(f"- {m}\n")

            if modo_ia not in embeds_gerados:

                embeds_gerados[modo_ia] = await gerar_embed(dados_envio, modo_ia, msg)
            modo = 'Punicao ' + str(modo_ia)

        if elogio['merece_elogio']:
            msg = StringIO()
            for m in elogio['motivos_elogio']:
                msg.write(f"- {m}\n")

            if 'elogio' not in embeds_gerados:
                embeds_gerados['elogio'] = await gerar_embed(dados_envio, 'elogio', msg)
            modo = 'Elogio'

        try:
            canal = await client.fetch_channel(int(id_canal))

            #monta o texto de mecao de forma inteligente
            texto_ping = f"<@{discord_id}>"
            if id_cargo:
                texto_ping += f"<@&{id_cargo}>"
            
            if punicao['punitivo']:
                await canal.send(content=texto_ping, embed=embeds_gerados[modo_ia])
            if elogio['merece_elogio']:
                await canal.send(content=texto_ping, embed=embeds_gerados['elogio'])
            await asyncio.sleep(2.5)

            print(f"Notificação de punição enviada para {nome_jogador} (Modo {modo}) no canal {id_canal}!!")   
        except discord.errors.NotFound:
            print(f"Erro: O canal com ID {id_canal} foi deletado.")
        except discord.errors.Forbidden:
            print(f"Erro: Sem permissão no canal {id_canal}.")

async def gerar_embed(dados_envio, modo, msg):
    """
    recebe os dados e constroi o embed do tipo pedido (punicao ou elogio)
    """
    embed = None

    punicao = dados_envio['punicao']
    elogio = dados_envio['elogio']
    dados_embed = dados_envio['dados_embed']
    dados_jogador = dados_envio['dados_jogador']
    nome_jogador = dados_envio['nome_jogador']

    kills = dados_jogador['kills']
    deaths = dados_jogador['deaths']
    assists = dados_jogador['assists']
    nome_agente = dados_embed['nome_agente']
    mapa = dados_embed['mapa']
    foto_agente = dados_embed['foto_agente']
    banner_jogador = dados_embed['banner_jogador']
    elo_imagem = dados_embed['elo_imagem']
    rank_up = elogio['rank_up']

    if modo == 'elogio':
        print(f"Gerando IA e montando o Embed do Modo Elogio para {nome_jogador}...")
        texto_ia_elogio = await gerar_elogio(nome_jogador, nome_agente, mapa, elogio['motivos_elogio_IA'])
        
        embed_vitoria = discord.Embed(
            description=texto_ia_elogio,
            color=0xFFD700 # Cor Dourada (Gold)
        )
        embed_vitoria.add_field(name="Feitos:", value=msg.getvalue(), inline=False)
        
        # Se subiu de elo, o título é especial e a foto principal é o novo Rank
        if rank_up and elo_imagem:
            embed_vitoria.title = "🎉 SUBIU DE ELO 🎉"
            embed_vitoria.set_thumbnail(url=elo_imagem) 
            embed_vitoria.set_image(url=banner_jogador)
        else:
            # Se foi só K/D bom, foto do agente padrão
            embed_vitoria.title = "🔥 ALERTA TOPII 🔥"
            embed_vitoria.set_thumbnail(url=foto_agente)

        embed = embed_vitoria
    else:

        print(f"Gerando IA e montando o Embed do Modo {modo} para {nome_jogador}...")
        
        # 1. Gera o texto na IA
        texto_ia = await gerar_humilhacao(nome_jogador, nome_agente, mapa, punicao['motivos_punicao_IA'],modo)
        
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
    
    return embed

async def atualizar_status_discord(client, jogadores):
    agora = datetime.now().strftime("%H:%M")
    hora_correta = ajuste_fuso_horario(agora, 3)

    atividade = discord.Activity(
        type=discord.ActivityType.watching, 
        name=f"{len(jogadores)} alvos | Última checagem: {hora_correta}"
    )
    await client.change_presence(status=discord.Status.online, activity=atividade)