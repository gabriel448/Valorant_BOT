import discord
from discord import app_commands
import aiohttp
import os
from io import StringIO

from utils import gerar_embed
from api import obter_puuid_henrik
from database import cadastrar_alvo_bd, configurar_canal_alerta, pegar_todos_canais_configurados, configurar_cargo_alerta, pegar_dono_do_alvo, remover_alvo_bd, configurar_modo_ia,pegar_top_bagres
from utils import calcular_elo_explanator, pegar_temporada_atual, pegar_url_elo
from imagem_builder import criar_imagem_leaderboard
from dotenv import load_dotenv

load_dotenv()

class MenuMotivos(discord.ui.Select):
        def __init__(self, tipo_aviso, jogador, agente, mapa, client):
            self.tipo_aviso = tipo_aviso
            self.jogador = jogador
            self.agente = agente
            self.mapa = mapa
            self.client = client
            
            # Define as "Checkboxes" (Opções do Menu) dependendo do tipo
            opcoes = []
            if tipo_aviso == 'punicao':
                opcoes = [
                    discord.SelectOption(label="Caiu de Elo", description="Simula a queda para o Prata 1", value="caiu"),
                    discord.SelectOption(label="Zero Kills", description="Jogou 13 rounds e não matou ninguém", value="zero"),
                    discord.SelectOption(label="K/D Horrível", description="Simula um K/D de 0.2", value="kd"),
                    discord.SelectOption(label="Loss Streak", description="Simula 5 derrotas seguidas", value="streak"),
                    discord.SelectOption(label="Só atira no peito", description="Simula 85% de bodyshot", value="peito")
                ]
            else:
                opcoes = [
                    discord.SelectOption(label="Subiu de Elo", description="Simula a subida para o Diamante 1", value="subiu"),
                    discord.SelectOption(label="Amasou o Lobby (MVP)", description="Simula K/D 2.5 com 25 kills", value="mvp")
                ]

            # max_values permite selecionar vários motivos ao mesmo tempo
            super().__init__(placeholder="Selecione os motivos (pode marcar vários)...", min_values=1, max_values=len(opcoes), options=opcoes)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            # 1. Preparando as listas de motivos baseadas nas escolhas
            motivos = []
            motivos_IA = []
            rank_up = False
            
            # Valores falsos genéricos para preencher o visual
            kills, deaths, assists = 5, 20, 2
            
            if self.tipo_aviso == 'punicao':
                if "caiu" in self.values:
                    motivos.append("Caiu pro Prata 1 kkk")
                    motivos_IA.append("CAIU DE ELO, AGORA O JOGADOR ESTA Prata 1")
                if "zero" in self.values:
                    motivos.append("jogou 13 rounds e fez ZERO abates.")
                    motivos_IA.append("JOGADOR JOGOU 13 E FEZ ZERO ABATES")
                    kills = 0
                if "kd" in self.values:
                    motivos.append("K/D de 0.25 (5/20/2).")
                    motivos_IA.append("K/D de 0.25 (5/20/2). JOGADOR OBTEVE UM PESSIMO KD NESSA PARTIDA")
                if "streak" in self.values:
                    motivos.append("5 derrotas seguidas e contando")
                    motivos_IA.append("JOGADOR CHEGOU NA SEQUENCIA DE 5 DERRTOAS SEGUIDAS")
                if "peito" in self.values:
                    motivos.append("**85.0%** dos tiros foi no peito")
                    motivos_IA.append("**85.0%** DOS TIROS DADOS PELO JOGADOR NESSA PARTIDA ACERTARAM O PEITO DOS INIMIGOS, ELE NAO SABE MIRAR NA CABECA")
            else:
                kills, deaths, assists = 25, 10, 5
                if "subiu" in self.values:
                    motivos.append("subiu pro Diamante 1")
                    motivos_IA.append("JOGADOR SUBIU DE ELO, AGORA ESTA NO ELO Diamante 1")
                    rank_up = True
                if "mvp" in self.values:
                    motivos.append("K/D de 2.50 (25/10/5).")
                    motivos_IA.append("K/D de 2.50 (25/10/5). JOGADOR OBTEVE UM OTIMO KD NESSA PARTIDA, NAO FOI CARREGADO")

            temporada_atual = await pegar_temporada_atual()
            elo_imagem = pegar_url_elo(18, temporada_atual)

            # 2. Criando o "Objeto Falso" (Mock) idêntico ao que o seu loop geraria
            dados_envio_falso = {
                'punicao': {'punitivo': self.tipo_aviso == 'punicao', 'motivos_punicao': motivos, 'motivos_punicao_IA': motivos_IA},
                'elogio': {'merece_elogio': self.tipo_aviso == 'elogio', 'motivos_elogio': motivos, 'motivos_elogio_IA': motivos_IA, 'rank_up': rank_up},
                'dados_embed': {
                    'nome_agente': self.agente,
                    'mapa': self.mapa,
                    'foto_agente': "https://media.valorant-api.com/agents/320b2a48-4d9b-a075-30f1-1f93a9b638fa/displayicon.png", # Imagem Sova
                    'banner_jogador': "https://media.valorant-api.com/playercards/fc209787-414b-10d0-dcac-048323c8f59b/wideart.png",
                    'elo_imagem': elo_imagem # Imagem dima 1
                },
                'dados_jogador': {'kills': kills, 'deaths': deaths, 'assists': assists},
                'nome_jogador': self.jogador,
                'client': self.client,
                'destinos': [], 
                'discord_id': interaction.user.id
            }

            # 3. Formata os motivos em string usando seu padrão
            msg = StringIO()
            for m in motivos:
                msg.write(f"- {m}\n")

            # 4. Chama a função real de gerar o Embed e aciona a IA
            modo_teste = 1 if self.tipo_aviso == 'punicao' else 'elogio'
            embed_gerado = await gerar_embed(dados_envio_falso, modo_teste, msg)

            # 5. Envia o resultado APENAS para você ver
            await interaction.followup.send(content="🔧 **Resultado do Teste:**", embed=embed_gerado, ephemeral=True)


class ViewTestes(discord.ui.View):
    def __init__(self, tipo_aviso, jogador, agente, mapa, client):
        super().__init__(timeout=60)
        self.add_item(MenuMotivos(tipo_aviso, jogador, agente, mapa, client))

class PaginacaoHelp(discord.ui.View):
    def __init__(self, embed_guia, embeds_paginas):
        super().__init__(timeout=180) # Os botões param de funcionar após 3 minutos para não pesar a memória
        self.embed_guia = embed_guia
        self.embeds_paginas = embeds_paginas
        self.pagina_atual = 0

    # Botão Voltar
    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.secondary, disabled=True)
    async def botao_anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_atual -= 1
        await self.atualizar_mensagem(interaction)

    # Botão Avançar
    @discord.ui.button(label="Próximo ▶️", style=discord.ButtonStyle.primary)
    async def botao_proximo(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.pagina_atual += 1
        await self.atualizar_mensagem(interaction)

    async def atualizar_mensagem(self, interaction: discord.Interaction):
        # Desativa o botão "Anterior" se estiver na primeira página
        self.children[0].disabled = (self.pagina_atual == 0)
        # Desativa o botão "Próximo" se estiver na última página
        self.children[1].disabled = (self.pagina_atual == len(self.embeds_paginas) - 1)
        
        # Edita a mensagem mantendo o Guia Fixo e trocando só a página de comandos
        await interaction.response.edit_message(
            embeds=[self.embed_guia, self.embeds_paginas[self.pagina_atual]], 
            view=self
        )

HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')
MEU_ID_DISCORD = int(os.getenv('MEU_ID_DISCORD'))
def configurar_comandos(tree: app_commands.CommandTree, client: discord.Client, cache_partidas):

    # ----- CADASTRAR ALVO -----
    @tree.command(name="cadastrar-alvo", description="Cadastra um amigo para o monitoramento de baitamento no Valorant.")
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


    # ----- ATIVAR O CHAT DE TEXTO -----
    @tree.command(name="ativar-esse-canal", description="[ADMIN] Define este canal como o oficial para os Alertas de Bagre.")
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

    
    # ----- PATCH NOTES -----
    @tree.command(name="patch-notes", description="[DEV] Dispara o anúncio de atualização para todos os servidores.")
    async def patch_notes(interaction: discord.Interaction):
        # Só eu posso rodar isso
        
        if interaction.user.id != MEU_ID_DISCORD:
            await interaction.response.send_message("❌ Apenas o desenvolvedor supremo pode usar este comando.", ephemeral=True)
            return

        # Avisa ao Discord que o bot está "pensando"
        await interaction.response.defer(ephemeral=True)
        
        # montando o embed
        embed = discord.Embed(
            title="💎 AGRADECIMENTOS - PROJETO GROK",
            description=(
                "dev Sousa aqui dnv, **batemos a meta pro projeto do grok em menos de 1 dia!!** voces sao fodas."
                "Graças a vocês, o bot terá um cérebro novo, mais rápido e com bem mais personalidade, obrigado por tornarem isso possivel."
                "Isso me incentiva dms a continuar trabalhando todo dia pra **melhorar cada vez mais o explanator.**"
            ),
            color=0x00BFFF # Azul Cyan para diferenciar do dourado da arrecadação
        )

        #Lista de Colaboradores (Adicione os nomes aqui)
        colaboradores = [
            "• gust9391",
            "• smoothzx",
            "• addeoru.",
            "• rifas1829",
            "• vampwide",
            "• vampwide"
            # Adicione mais nomes seguindo este padrão
        ]
        
        lista_nomes = "\n".join(colaboradores)
        
        embed.add_field(
            name="👑 Colaboradores", 
            value=lista_nomes, 
            inline=False
        )

        embed.set_thumbnail(url=client.user.avatar.url)
        embed.set_footer(text="O explanator não para. Obrigado, tropa!")
        
        #embed.set_footer(text="Desenvolvido com ódio e Python. Bom jogo!")

        # dispara pra todos os servidores
        canais = await pegar_todos_canais_configurados()
        enviados = 0
        
        for id_canal in canais:
            try:
                canal = await client.fetch_channel(int(id_canal))
                await canal.send(embed=embed)
                enviados += 1
            except discord.errors.NotFound:
                print(f"Canal {id_canal} não encontrado.")
            except discord.errors.Forbidden:
                print(f"Sem permissão no canal {id_canal}.")
                
        # Confirmação apenas para você
        await interaction.followup.send(f"✅ Anúncio disparado com sucesso para {enviados} servidores!")
    

    # ----- CADASTRAR CARGO -----
    @tree.command(name="ativar-esse-cargo", description="[ADMIN] Define qual cargo será marcado nos avisos.")
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
    

    # ----- REMOVER ALVO -----
    @tree.command(name='remover-alvo', description="Remove um jogador do monitoramento do Tribunal." )
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
    

    # ----- MODO DA IA -----
    @tree.command(name="modo-ia", description="[ADMIN] Define a personalidade da IA neste servidor.")
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

    
    # ----- TABELA DE LIDERANCA -----
    @tree.command(name="top-explanados", description="Exibe o ranking dos maiores bagres deste servidor (Rank Explanator).")
    async def top_bagres(interaction: discord.Interaction):
        await interaction.response.defer()

        # 1. Busca os dados no banco
        top_jogadores = await pegar_top_bagres(interaction.guild.id)
        
        if not top_jogadores:
            await interaction.followup.send("📭 Nenhum jogador cadastrado neste servidor ainda.")
            return

        lista_para_imagem = []
        
        temporada_atual = await pegar_temporada_atual()
        
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
            icon_url = pegar_url_elo(indice_api, temporada_atual)
            
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

    # ----- HELP -----
    @tree.command(name="help", description="Guia de iniciação e lista de comandos do Explanator.")
    async def help_cmd(interaction: discord.Interaction):
        
        # 1. EMBED FIXO (Get Started)
        embed_guia = discord.Embed(
            title="🚀 PRIMEIROS PASSOS",
            description="Acabou de convidar o Explanator? Siga a ordem abaixo para o bot começar a monitorar os jogadores do servidor:",
            color=0xFFD700 # Dourado
        )
        embed_guia.add_field(name="1️⃣ Configure o Canal (Obrigatório)", value="Use `/ativar-esse-canal` no chat onde você quer que o bot envie as notificações.", inline=False)
        embed_guia.add_field(name="2️⃣ Configure o Cargo (Opcional)", value="Quer que todo mundo seja pingado quando alguém for explanado? Use `/ativar-esse-cargo` e marque o cargo da galera do Explanator.", inline=False)
        embed_guia.add_field(name="3️⃣ Cadastre o jogador", value="Use `/cadastrar-alvo` marcando o seu amigo e passando o Riot ID dele (ex: Sacy#BR1). A partir desse momento, ele será monitorado 24h por dia.", inline=False)
        embed_guia.set_thumbnail(url=client.user.avatar.url if client.user.avatar else None)

        # 2. LISTA DE COMANDOS (Banco de dados de textos)
        comandos_info = [
            {"nome": "🎯 `/cadastrar-alvo [usuario] [riot_id]`", "desc": "Coloca um jogador na mira do Explanator. Toda vez que ele terminar uma partida, a IA vai julgar o desempenho dele."},
            {"nome": "🗑️ `/remover-alvo [riot_id]`", "desc": "Deleta a existência de um jogador do banco de dados. Você só pode remover a si mesmo (Administradores podem remover qualquer um)."},
            {"nome": "📢 `/ativar-esse-canal`", "desc": "[Admin] Trava o bot para enviar mensagens, alertas e imagens exclusivamente no canal de texto onde o comando foi digitado."},
            {"nome": "🔔 `/ativar-esse-cargo [cargo]`", "desc": "[Admin] Escolhe qual cargo do servidor será mencionado (pingado) nos alertas do bot. Precisa configurar o canal primeiro."},
            {"nome": "🧠 `/modo-ia [nivel]`", "desc": "[Admin] Altera a personalidade do narrador. Escolha entre Tóxico (pesado), Leve (sem palavrões) ou Comentarista (auto explicativo)."},
            {"nome": "📉 `/top-explanados`", "desc": "Gera a Parede da Vergonha! Uma imagem com o ranking dos maiores bagres do servidor, ordenado por quem tem mais pontos de punição."},
            {"nome": "❓ `/help`", "desc": "Mostra este menu de ajuda que você está lendo agora mesmo."},
            {"nome": "✉️ `/convite`", "desc": "Link para adicionar o bot ao seu servidor"}
        ]

        # 3. FATIADOR DE PÁGINAS (4 comandos por página)
        embeds_paginas = []
        comandos_por_pagina = 4
        
        # Um pequeno truque de matemática para criar blocos de 4 em 4
        for i in range(0, len(comandos_info), comandos_por_pagina):
            pagina = comandos_info[i:i + comandos_por_pagina]
            
            embed_pagina = discord.Embed(
                title=f"📚 Manual de Comandos (Página {len(embeds_paginas) + 1})",
                color=0x00BFFF # Azul
            )
            
            for cmd in pagina:
                embed_pagina.add_field(name=cmd["nome"], value=cmd["desc"], inline=False)
                
            embed_pagina.set_footer(text="Use os botões abaixo para navegar.")
            embeds_paginas.append(embed_pagina)

        # 4. ENVIA A MENSAGEM COM OS BOTÕES
        # Passamos o Guia e a lista de Páginas para a nossa classe gerenciadora
        view_paginacao = PaginacaoHelp(embed_guia, embeds_paginas)
        
        await interaction.response.send_message(
            embeds=[embed_guia, embeds_paginas[0]], 
            view=view_paginacao
        )
    
    # ----- COMANDO CONVITE (PROVISÓRIO) -----
    @tree.command(name="convite", description="Receba o link para adicionar o Explanator no seu servidor.")
    async def convite_cmd(interaction: discord.Interaction):
        
        link_convite = "https://discord.com/oauth2/authorize?client_id=1485752489520136362&permissions=8&integration_type=0&scope=bot+applications.commands"
        
        embed = discord.Embed(
            title="⚖️ Leve o Explanator para o seu Servidor",
            description="Nosso site oficial está em construção! Enquanto isso, use o botão abaixo para convidar o bot e começar a julgar os bagres dos seus amigos.",
            color=0x5865F2 # Azul padrão do Discord
        )
        
        embed.set_thumbnail(url=client.user.avatar.url)

        # Cria um botão de link nativo
        view = discord.ui.View()
        botao = discord.ui.Button(
            label="Adicionar ao Servidor", 
            url=link_convite, 
            style=discord.ButtonStyle.link
        )
        view.add_item(botao)
        
        # Envia a mensagem (ephemeral=True para não poluir o chat do servidor)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # ----- LIMPAR CACHE -----
    @tree.command(name="limpar-cache", description="[DEV] Esvazia a memória RAM de partidas do bot.")
    async def limpar_cache_cmd(interaction: discord.Interaction):
        # Proteção de segurança
    
        if interaction.user.id != MEU_ID_DISCORD:
            await interaction.response.send_message("❌ Apenas o desenvolvedor pode limpar o cache.", ephemeral=True)
            return
            
        tamanho_antes = len(cache_partidas)
        cache_partidas.clear()
        
        await interaction.response.send_message(
            f"🧹 **Cache Limpo!** {tamanho_antes} partidas foram apagadas da memória RAM.", 
            ephemeral=True
        )

    @tree.command(name="notificacao-teste", description="[DEV] Gera um alerta de teste (ninguém mais vê).")
    @app_commands.choices(tipo_aviso=[
        app_commands.Choice(name="Punição", value="punicao"),
        app_commands.Choice(name="Elogio", value="elogio")
    ])
    async def notificacao_teste_cmd(interaction: discord.Interaction, tipo_aviso: app_commands.Choice[str], jogador: str, agente: str, mapa: str):
        
        if interaction.user.id != MEU_ID_DISCORD:
            await interaction.response.send_message("❌ Acesso Negado. Este comando é apenas para manutenção.", ephemeral=True)
            return

        view = ViewTestes(tipo_aviso.value, jogador, agente, mapa, client)
        
        # Envia a interface de botões apenas para você
        await interaction.response.send_message(
            f"🛠️ **Painel de Teste:** Configure os motivos do aviso para **{jogador}** de **{agente}** na **{mapa}**.", 
            view=view, 
            ephemeral=True
        )