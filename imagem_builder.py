from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp

async def baixar_imagem(url):
    """Baixa uma imagem da internet e transforma em formato Pillow."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                return Image.open(io.BytesIO(data)).convert("RGBA")
    return None

async def criar_imagem_leaderboard(jogadores, titulo="LEADERBOARD"):
    """
    Constrói a imagem com banners, gradientes e os avatares.
    'jogadores' deve ser uma lista de dicts: [{'nome': 'Sacy', 'rank': 'Ouro 1', 'banner_url': '...', 'icon_url': '...'}]
    """
    
    largura = 1200 
    
    altura_linha = 100
    espaco = 10
    altura_total = (altura_linha + espaco) * len(jogadores) + 120 # +120 pro título
    
    # Cria o canvas de fundo escuro
    fundo = Image.new('RGBA', (largura, altura_total), (30, 30, 30, 255))
    draw = ImageDraw.Draw(fundo)
    
    # Tenta carregar fontes (se não achar, usa padrões claros)
    try:
        fonte_titulo = ImageFont.truetype("LiberationSans-Bold.ttf", 35) # Maior e mais negrito
        fonte_texto = ImageFont.truetype("LiberationSans-Regular.ttf", 35)
    except:
        fonte_titulo = ImageFont.load_default()
        fonte_texto = ImageFont.load_default()
        
    # Desenha o Título 'RANKING EXPLANATOR - [Nome do Servidor]'
    draw.text((largura//2, 60), f"{titulo}", font=fonte_titulo, fill=(255, 255, 255), anchor="mm")
    
    y_atual = 120 # Ajustado para baixo do título
    
    for posicao, jog in enumerate(jogadores, start=1):
        # Baixa assets (em produção, cachearia ou buscaria na API)
        # Para demonstração, usamos imagens de exemplo
        banner = await baixar_imagem(jog['banner_url'])
        icone_elo = await baixar_imagem(jog['icon_url']) # Ícone do Rank Explanator
        
        linha = Image.new('RGBA', (largura, altura_linha), (0, 0, 0, 0))
        draw_linha = ImageDraw.Draw(linha)
        
        if banner:
            # Redimensiona o banner e recorta o meio
            banner = banner.resize((largura, int(largura * banner.height / banner.width)))
            banner = banner.crop((0, banner.height//2 - altura_linha//2, largura, banner.height//2 + altura_linha//2))
            
            # --- GRADIENTE CORRIGIDO ---
            # Cria uma máscara que começa sólida e escura e desaparece suavemente.
            gradiente = Image.new('L', (largura, altura_linha))
            ponto_transparencia_comeca = int(largura * 0.4) # Começa a desaparecer a 40% da largura
            for x in range(largura):
                if x < ponto_transparencia_comeca:
                    alpha = 255 # Sólido na esquerda
                else:
                    # Alpha diminui linearmente até 0 no final
                    alpha = int(255 - ((x - ponto_transparencia_comeca) / (largura - ponto_transparencia_comeca)) * 255)
                for y in range(altura_linha):
                    gradiente.putpixel((x, y), alpha)
            
            fundo_escuro_solido = Image.new('RGBA', (largura, altura_linha), (20, 20, 20, 255))
            # Mescla o banner com o fundo escuro sólido usando a máscara de gradiente corrigida
            linha.paste(banner, (0, 0))
            linha.paste(fundo_escuro_solido, (0, 0), mask=gradiente)
            
        # --- TEXTO FORMATADO ---
        # Posicao | Nome
        posicao_texto = f"#{posicao}"
        draw_linha.text((30, altura_linha//2), posicao_texto, font=fonte_texto, fill=(50, 200, 255), anchor="lm") # Azul claro Valorant
        
        nome_texto = f"{jog['nome']}"
        draw_linha.text((120, altura_linha//2), nome_texto, font=fonte_texto, fill=(255, 255, 255), anchor="lm")
        
        # --- ÍCONE DE ELO VISÍVEL ---
        if icone_elo:
            icone_elo = icone_elo.resize((80, 80)).convert("RGBA")
            linha.paste(icone_elo, (largura - 120, 10), mask=icone_elo)
            
        # Cola a linha construída no fundo principal
        fundo.paste(linha, (0, y_atual), mask=linha)
        y_atual += altura_linha + espaco
        
    # Converte para Bytes para enviar pelo Discord
    buffer = io.BytesIO()
    fundo.save(buffer, format="PNG")
    buffer.seek(0)
    
    return buffer

async def criar_imagem_comparacao(vencedor_url, perdedor_url, nome_vencedor, nome_perdedor):
    """
    Cria uma imagem de 'versus' ou superioridade entre dois jogadores.
    """
    largura = 800
    altura = 400
    
    fundo = Image.new('RGBA', (largura, altura), (15, 15, 15, 255))
    draw = ImageDraw.Draw(fundo)
    
    try:
        fonte_vitoria = ImageFont.truetype("LiberationSans-Bold.ttf", 40)
        fonte_vs = ImageFont.truetype("LiberationSans-Bold.ttf", 60)
        fonte_nomes = ImageFont.truetype("LiberationSans-Regular.ttf", 25)
    except:
        fonte_vitoria = ImageFont.load_default()
        fonte_vs = ImageFont.load_default()
        fonte_nomes = ImageFont.load_default()

    # Baixar Avatares
    img_vencedor = await baixar_imagem(vencedor_url) if vencedor_url else None
    img_perdedor = await baixar_imagem(perdedor_url) if perdedor_url else None

    # Desenhar Círculos/Fundos para os avatares
    # Vencedor (Esquerda)
    if img_vencedor:
        img_vencedor = img_vencedor.resize((200, 200))
        # Criar máscara circular
        mask = Image.new('L', (200, 200), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 200, 200), fill=255)
        
        # Borda dourada para o vencedor
        draw.ellipse((45, 95, 255, 305), outline=(255, 215, 0), width=8)
        fundo.paste(img_vencedor, (50, 100), mask=mask)
        draw.text((150, 330), nome_vencedor, font=fonte_nomes, fill=(255, 255, 255), anchor="mm")
        draw.text((150, 70), "O MAIOR", font=fonte_vitoria, fill=(255, 215, 0), anchor="mm")

    # Texto VS no meio
    draw.text((largura // 2, altura // 2), "VS", font=fonte_vs, fill=(200, 0, 0), anchor="mm")

    # Perdedor (Direita) - Menor e talvez preto e branco?
    if img_perdedor:
        img_perdedor = img_perdedor.resize((140, 140))
        # Converte para preto e branco para simbolizar a derrota/inferioridade no explanator
        img_perdedor = img_perdedor.convert("L").convert("RGBA")
        
        mask_p = Image.new('L', (140, 140), 0)
        draw_mask_p = ImageDraw.Draw(mask_p)
        draw_mask_p.ellipse((0, 0, 140, 140), fill=255)
        
        # Borda cinza
        draw.ellipse((largura - 215, 125, largura - 65, 275), outline=(100, 100, 100), width=4)
        fundo.paste(img_perdedor, (largura - 210, 130), mask=mask_p)
        draw.text((largura - 140, 300), nome_perdedor, font=fonte_nomes, fill=(150, 150, 150), anchor="mm")
        draw.text((largura - 140, 100), "O BAGRE", font=fonte_nomes, fill=(150, 150, 150), anchor="mm")

    # Linhas de efeito
    draw.line((largura // 2, 50, largura // 2, 120), fill=(100, 100, 100), width=2)
    draw.line((largura // 2, 280, largura // 2, 350), fill=(100, 100, 100), width=2)

    buffer = io.BytesIO()
    fundo.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def criar_imagem_tabela_comparativa(p1_data, p2_data, categorias, vencedor_nome, titulo="DUELO DE ESTATÍSTICAS"):
    """
    Cria uma tabela visual comparando estatísticas de dois jogadores. (Escalado em +150% para Máximo Impacto)
    """
    largura = 1500
    altura_cabecalho = 550
    altura_linha = 180
    altura_total = altura_cabecalho + (len(categorias) * altura_linha) + 100
    
    fundo = Image.new('RGBA', (largura, altura_total), (10, 10, 10, 255))
    draw = ImageDraw.Draw(fundo)
    
    try:
        # Fontes em Escala Massiva
        fonte_titulo = ImageFont.truetype("LiberationSans-Bold.ttf", 80)
        fonte_nomes_win = ImageFont.truetype("LiberationSans-Bold.ttf", 60)
        fonte_nomes_loss = ImageFont.truetype("LiberationSans-Bold.ttf", 40)
        fonte_labels = ImageFont.truetype("LiberationSans-Bold.ttf", 45)
        fonte_valores_win = ImageFont.truetype("LiberationSans-Bold.ttf", 65)
        fonte_valores_loss = ImageFont.truetype("LiberationSans-Bold.ttf", 40)
    except:
        fonte_titulo = ImageFont.load_default()
        fonte_nomes_win = ImageFont.load_default()
        fonte_nomes_loss = ImageFont.load_default()
        fonte_labels = ImageFont.load_default()
        fonte_valores_win = ImageFont.load_default()
        fonte_valores_loss = ImageFont.load_default()

    # Título no topo
    draw.text((largura // 2, 80), titulo, font=fonte_titulo, fill=(255, 255, 255), anchor="mm")

    # --- CABEÇALHO ---
    is_p1_vencedor = p1_data['nome'] == vencedor_nome
    av1 = await baixar_imagem(p1_data['avatar_url'])
    av2 = await baixar_imagem(p2_data['avatar_url'])

    def paste_avatar(img, pos, size, winner=True):
        if not img: return
        img = img.resize((size, size))
        if not winner:
            img = img.convert("L").convert("RGBA")
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        
        borda_cor = (255, 215, 0) if winner else (100, 100, 100)
        espessura = 15 if winner else 8
        draw.ellipse((pos[0]-10, pos[1]-10, pos[0]+size+10, pos[1]+size+10), outline=borda_cor, width=espessura)
        fundo.paste(img, pos, mask=mask)

    # Avatares Massivos: Vencedor 350px, Perdedor 250px
    paste_avatar(av1, (200 if is_p1_vencedor else 230, 150 if is_p1_vencedor else 180), 350 if is_p1_vencedor else 250, winner=is_p1_vencedor)
    paste_avatar(av2, (largura - 550 if not is_p1_vencedor else largura - 520, 150 if not is_p1_vencedor else 180), 350 if not is_p1_vencedor else 250, winner=not is_p1_vencedor)

    # Nomes
    draw.text((375 if is_p1_vencedor else 355, 520), p1_data['nome'], font=fonte_nomes_win if is_p1_vencedor else fonte_nomes_loss, fill=(255, 215, 0) if is_p1_vencedor else (150, 150, 150), anchor="mm")
    draw.text((largura - 375 if not is_p1_vencedor else largura - 355, 520), p2_data['nome'], font=fonte_nomes_win if not is_p1_vencedor else fonte_nomes_loss, fill=(255, 215, 0) if not is_p1_vencedor else (150, 150, 150), anchor="mm")

    # VS Central
    draw.text((largura // 2, 320), "VS", font=fonte_titulo, fill=(255, 50, 50), anchor="mm")

    # --- TABELA DE ESTATÍSTICAS ---
    y_atual = altura_cabecalho + 80
    for cat in categorias:
        idx = categorias.index(cat)
        cor_linha = (25, 25, 25, 255) if idx % 2 == 0 else (18, 18, 18, 255)
        draw.rectangle([80, y_atual, largura - 80, y_atual + altura_linha - 25], fill=cor_linha, outline=(70, 70, 70), width=2)
        
        # Categoria (Centro)
        draw.text((largura // 2, y_atual + (altura_linha // 2) - 12), cat, font=fonte_labels, fill=(200, 200, 200), anchor="mm")
        
        v1_raw, win1, icon1 = p1_data['stats'].get(cat, ("-", False, None))
        v2_raw, win2, icon2 = p2_data['stats'].get(cat, ("-", False, None))
        
        # Jogador 1 (Esquerda)
        pos_x1 = 300
        if icon1:
            ico1 = await baixar_imagem(icon1)
            if ico1:
                size_ico = 130 if win1 else 90
                ico1 = ico1.resize((size_ico, size_ico))
                fundo.paste(ico1, (pos_x1 - (size_ico//2), y_atual + (altura_linha // 2) - (size_ico//2) - 10), mask=ico1)
        else:
            txt1 = str(v1_raw)
            clr1 = (0, 255, 127) if win1 else (220, 80, 80)
            draw.text((pos_x1, y_atual + (altura_linha // 2) - 12), txt1, font=fonte_valores_win if win1 else fonte_valores_loss, fill=clr1, anchor="mm")
            if not win1 and win2: 
                 draw.text((pos_x1 + 130, y_atual + (altura_linha // 2) - 12), "✘", font=fonte_labels, fill=(255, 0, 0), anchor="mm")

        # Jogador 2 (Direita)
        pos_x2 = largura - 300
        if icon2:
            ico2 = await baixar_imagem(icon2)
            if ico2:
                size_ico = 130 if win2 else 90
                ico2 = ico2.resize((size_ico, size_ico))
                fundo.paste(ico2, (pos_x2 - (size_ico//2), y_atual + (altura_linha // 2) - (size_ico//2) - 10), mask=ico2)
        else:
            txt2 = str(v2_raw)
            clr2 = (0, 255, 127) if win2 else (220, 80, 80)
            draw.text((pos_x2, y_atual + (altura_linha // 2) - 12), txt2, font=fonte_valores_win if win2 else fonte_valores_loss, fill=clr2, anchor="mm")
            if not win2 and win1: 
                 draw.text((pos_x2 - 130, y_atual + (altura_linha // 2) - 12), "✘", font=fonte_labels, fill=(255, 0, 0), anchor="mm")
        
        y_atual += altura_linha

    buffer = io.BytesIO()
    fundo.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

    buffer = io.BytesIO()
    fundo.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def criar_imagem_progresso_explanator(pontos, rank_atual, rank_anterior, rank_proximo, icon_atual_url, icon_anterior_url, icon_proximo_url):
    """
    Cria uma barra de progresso visual mostrando o quão longe o jogador está de subir ou descer de rank.
    """
    largura = 600
    altura = 250
    
    # Cores
    cor_fundo = (20, 20, 20, 255)
    cor_barra_vazia = (50, 50, 50, 255)
    cor_progresso = (0, 255, 127, 255) # Verde Primavera
    
    fundo = Image.new('RGBA', (largura, altura), cor_fundo)
    draw = ImageDraw.Draw(fundo)
    
    try:
        fonte_media = ImageFont.truetype("LiberationSans-Bold.ttf", 20)
        fonte_pequena = ImageFont.truetype("LiberationSans-Regular.ttf", 16)
    except:
        fonte_media = ImageFont.load_default()
        fonte_pequena = ImageFont.load_default()

    # Baixar ícones
    icon_atual = await baixar_imagem(icon_atual_url) if icon_atual_url else None
    icon_anterior = await baixar_imagem(icon_anterior_url) if icon_anterior_url else None
    icon_proximo = await baixar_imagem(icon_proximo_url) if icon_proximo_url else None

    # Desenhar Ícones e Nomes
    y_icones = 60
    espacamento_lateral = 80
    
    if icon_anterior:
        icon_anterior = icon_anterior.resize((60, 60))
        fundo.paste(icon_anterior, (espacamento_lateral - 30, y_icones), mask=icon_anterior)
        draw.text((espacamento_lateral, y_icones + 75), rank_anterior, font=fonte_pequena, fill=(180, 180, 180), anchor="mm")

    if icon_proximo:
        icon_proximo = icon_proximo.resize((60, 60))
        fundo.paste(icon_proximo, (largura - espacamento_lateral - 30, y_icones), mask=icon_proximo)
        draw.text((largura - espacamento_lateral, y_icones + 75), rank_proximo, font=fonte_pequena, fill=(180, 180, 180), anchor="mm")

    if icon_atual:
        icon_atual = icon_atual.resize((90, 90))
        fundo.paste(icon_atual, (largura // 2 - 45, y_icones - 15), mask=icon_atual)
        draw.text((largura // 2, y_icones + 90), rank_atual, font=fonte_media, fill=(255, 255, 255), anchor="mm")

    # Desenhar Barra de Progresso
    y_barra = 180
    altura_barra = 20
    margem_barra = 100
    largura_util = largura - (2 * margem_barra)
    
    # Background da barra
    draw.rounded_rectangle([margem_barra, y_barra, largura - margem_barra, y_barra + altura_barra], radius=10, fill=cor_barra_vazia)
    
    # Progresso (pontos % 3)
    progresso_num = pontos % 3
    # Mapeia 0, 1, 2 para larguras da barra. 
    # 0 pontos = 15% (quase caindo)
    # 1 ponto = 50% (meio)
    # 2 pontos = 85% (quase subindo)
    progresso_map = {0: 0.15, 1: 0.50, 2: 0.85}
    porcentagem = progresso_map.get(progresso_num, 0.5)
    
    largura_progresso = int(largura_util * porcentagem)
    if largura_progresso > 5:
        draw.rounded_rectangle([margem_barra, y_barra, margem_barra + largura_progresso, y_barra + altura_barra], radius=10, fill=cor_progresso)

    # Texto de pontos
    draw.text((largura // 2, y_barra + 40), f"Pontos: {pontos} ({progresso_num}/3)", font=fonte_pequena, fill=(200, 200, 200), anchor="mm")

    buffer = io.BytesIO()
    fundo.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def criar_banner_status_valorant(nome, avatar_url, elo_nome, elo_icon_url, stats):
    """
    Cria um banner de status para o Valorant com estética premium (Vermelho/Branco/Preto).
    stats: {'kd': float, 'hs': float, 'win': float, 'dmg': float}
    """
    largura = 700
    altura = 350
    fundo = Image.new('RGBA', (largura, altura), (10, 10, 10, 255))
    draw = ImageDraw.Draw(fundo)
    
    try:
        fonte_nome = ImageFont.truetype("LiberationSans-Bold.ttf", 36)
        fonte_elo = ImageFont.truetype("LiberationSans-Bold.ttf", 26)
        fonte_stats_label = ImageFont.truetype("LiberationSans-Bold.ttf", 16)
        fonte_stats_val = ImageFont.truetype("LiberationSans-Bold.ttf", 34)
    except:
        fonte_nome = ImageFont.load_default()
        fonte_elo = ImageFont.load_default()
        fonte_stats_label = ImageFont.load_default()
        fonte_stats_val = ImageFont.load_default()

    # Detalhe visual lateral (Vermelho Valorant)
    draw.rectangle([0, 0, 15, altura], fill=(253, 69, 86, 255))

    # Avatar
    av = await baixar_imagem(avatar_url)
    if av:
        av = av.resize((160, 160))
        mask = Image.new('L', (160, 160), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 160, 160), fill=255)
        fundo.paste(av, (50, 50), mask=mask)
        # Borda do avatar
        draw.ellipse((45, 45, 215, 215), outline=(253, 69, 86), width=5)

    # Nome do Jogador
    draw.text((240, 60), nome, font=fonte_nome, fill=(255, 255, 255))

    # Elo Icon e Nome
    elo_ico = await baixar_imagem(elo_icon_url)
    if elo_ico:
        elo_ico = elo_ico.resize((90, 90))
        fundo.paste(elo_ico, (240, 110), mask=elo_ico)
        draw.text((345, 155), elo_nome, font=fonte_elo, fill=(253, 69, 86), anchor="lm")

    # Linha divisória
    draw.line([240, 220, largura - 40, 220], fill=(50, 50, 50), width=2)

    # Estatísticas (Grid horizontal)
    x_stats = 60
    y_stats = 250
    espacamento_x = 160
    
    stats_list = [
        ("K/D RATIO", f"{stats['kd']:.2f}"),
        ("% HS", f"{stats['hs']:.1f}%"),
        ("% WINRATE", f"{stats['win']:.1f}%"),
        ("DMG/ROUND", f"{stats['dmg']:.1f}")
    ]

    for i, (label, val) in enumerate(stats_list):
        curr_x = x_stats + (i * espacamento_x)
        
        # Label
        draw.text((curr_x, y_stats), label, font=fonte_stats_label, fill=(150, 150, 150))
        # Valor
        draw.text((curr_x, y_stats + 30), val, font=fonte_stats_val, fill=(255, 255, 255))

    buffer = io.BytesIO()
    fundo.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer