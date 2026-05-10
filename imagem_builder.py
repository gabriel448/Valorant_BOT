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
    Cria uma tabela visual comparando estatísticas de dois jogadores com estética Valorant.
    """
    largura = 1500
    altura_cabecalho = 670
    altura_linha = 185
    altura_total = altura_cabecalho + (len(categorias) * altura_linha) + 55

    # ── PALETA VALORANT ──────────────────────────────────────────────────────
    RED         = (255, 70, 85)
    RED_DARK    = (130, 25, 35)
    GOLD        = (255, 205, 50)
    GOLD_DIM    = (160, 120, 10)
    BG          = (8, 8, 14)
    PANEL_A     = (22, 22, 35)
    PANEL_B     = (14, 14, 22)
    WHITE       = (238, 238, 252)
    GRAY        = (105, 105, 128)
    GREEN       = (50, 230, 140)
    LOSER_COL   = (90, 90, 112)
    ACCENT_LINE = (45, 45, 62)

    fundo = Image.new('RGBA', (largura, altura_total), BG + (255,))
    draw  = ImageDraw.Draw(fundo)

    # ── FONTES ───────────────────────────────────────────────────────────────
    try:
        f_title  = ImageFont.truetype("LiberationSans-Bold.ttf",    52)
        f_badge  = ImageFont.truetype("LiberationSans-Bold.ttf",    30)
        f_name_w = ImageFont.truetype("LiberationSans-Bold.ttf",    56)
        f_name_l = ImageFont.truetype("LiberationSans-Regular.ttf", 42)
        f_vs     = ImageFont.truetype("LiberationSans-Bold.ttf",    90)
        f_label  = ImageFont.truetype("LiberationSans-Bold.ttf",    38)
        f_val_w  = ImageFont.truetype("LiberationSans-Bold.ttf",    72)
        f_val_l  = ImageFont.truetype("LiberationSans-Regular.ttf", 62)
    except Exception:
        _fb = ImageFont.load_default()
        f_title = f_badge = f_name_w = f_name_l = f_vs = f_label = f_val_w = f_val_l = _fb

    is_p1_win = p1_data['nome'] == vencedor_nome

    # ── FUNDO COM GRADIENTE VERTICAL ────────────────────────────────────────
    strip = 8
    for y in range(0, altura_total, strip):
        t  = y / altura_total
        r  = int(8  + 6  * (1 - t))
        g  = int(8  + 4  * (1 - t))
        b  = int(14 + 10 * (1 - t))
        draw.rectangle([(0, y), (largura, min(y + strip, altura_total))], fill=(r, g, b, 255))

    draw = ImageDraw.Draw(fundo)

    # ── BORDA SUPERIOR ───────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (largura, 5)], fill=RED)
    draw.rectangle([(0, 6), (largura, 7)], fill=RED_DARK)

    # ── TRIÂNGULOS DE CANTO (topo) ───────────────────────────────────────────
    tri = 80
    draw.polygon([(0, 0), (tri, 0), (0, tri)], fill=RED)
    draw.polygon([(largura, 0), (largura - tri, 0), (largura, tri)], fill=RED)


    # ── CENTROS DOS JOGADORES ────────────────────────────────────────────────
    X_P1     = 375
    X_P2     = 1125
    Y_AV     = 370   # centro vertical dos avatares
    SIZE_WIN = 300
    SIZE_LOS = 210

    win_x    = X_P1 if is_p1_win else X_P2
    los_x    = X_P2 if is_p1_win else X_P1
    win_nome = p1_data['nome'] if is_p1_win else p2_data['nome']
    los_nome = p2_data['nome'] if is_p1_win else p1_data['nome']

    av1 = await baixar_imagem(p1_data['avatar_url'])
    av2 = await baixar_imagem(p2_data['avatar_url'])
    win_av = av1 if is_p1_win else av2
    los_av = av2 if is_p1_win else av1

    # ── GLOW DOURADO ATRÁS DO VENCEDOR ──────────────────────────────────────
    glow_layers = 10
    for i in range(glow_layers, 0, -1):
        gr    = SIZE_WIN // 2 + i * 15
        alpha = int(70 * (glow_layers - i + 1) / glow_layers)
        draw.ellipse(
            (win_x - gr, Y_AV - gr, win_x + gr, Y_AV + gr),
            fill=GOLD + (alpha,)
        )

    # ── BADGES VITÓRIA / DERROTA ─────────────────────────────────────────────
    def draw_badge(cx, top_y, text, bg_color, font):
        bb2 = draw.textbbox((0, 0), text, font=font)
        tw  = bb2[2] - bb2[0]
        th  = bb2[3] - bb2[1]
        px, py, sk = 28, 13, 18
        w   = tw + px * 2
        h   = th + py * 2
        cy  = top_y + h // 2
        pts = [(cx - w//2 + sk, top_y), (cx + w//2 + sk, top_y),
               (cx + w//2 - sk, top_y + h), (cx - w//2 - sk, top_y + h)]
        draw.polygon(pts, fill=bg_color)
        draw.text((cx, cy), text, font=font, fill=WHITE, anchor="mm")

    badge_top = 135
    draw_badge(win_x, badge_top, "◆  VITÓRIA  ◆", RED,         f_badge)
    draw_badge(los_x, badge_top + 6, "DERROTA",   (50, 50, 65), f_badge)

    # ── AVATARES ─────────────────────────────────────────────────────────────
    def paste_av(img, cx, cy, size, is_winner):
        if not img:
            return
        img2 = img.resize((size, size)).convert("RGBA")
        if not is_winner:
            img2 = img2.convert("L").convert("RGBA")
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        b   = 16 if is_winner else 8
        col = GOLD if is_winner else (60, 60, 80)
        draw.ellipse(
            (cx - size//2 - b, cy - size//2 - b,
             cx + size//2 + b, cy + size//2 + b),
            outline=col, width=b
        )
        fundo.paste(img2, (cx - size//2, cy - size//2), mask=mask)

    paste_av(win_av, win_x, Y_AV, SIZE_WIN, True)
    paste_av(los_av, los_x, Y_AV, SIZE_LOS, False)
    draw = ImageDraw.Draw(fundo)

    # ── VS CENTRAL ───────────────────────────────────────────────────────────
    vs_x = largura // 2
    # Calcula onde as linhas terminam — respeita o raio real de cada avatar
    _gap       = 22
    _borda_win = 16
    _borda_los = 8
    # Avatar esquerdo (X_P1): a linha começa logo após sua borda direita
    _r_esq = (SIZE_WIN if is_p1_win else SIZE_LOS) // 2 + (_borda_win if is_p1_win else _borda_los)
    line_esq = X_P1 + _r_esq + _gap
    # Avatar direito (X_P2): a linha termina logo antes de sua borda esquerda
    _r_dir = (SIZE_WIN if not is_p1_win else SIZE_LOS) // 2 + (_borda_win if not is_p1_win else _borda_los)
    line_dir = X_P2 - _r_dir - _gap
    # Linhas horizontais com caps
    draw.line([(line_esq, Y_AV), (vs_x - 68, Y_AV)], fill=RED, width=3)
    draw.line([(vs_x + 68, Y_AV), (line_dir, Y_AV)], fill=RED, width=3)
    draw.line([(line_esq, Y_AV - 10), (line_esq, Y_AV + 10)], fill=RED, width=3)
    draw.line([(line_dir, Y_AV - 10), (line_dir, Y_AV + 10)], fill=RED, width=3)
    # Diamantes decorativos
    d = 14
    draw.polygon([(vs_x, Y_AV - 92 - d), (vs_x + d, Y_AV - 92),
                  (vs_x, Y_AV - 92 + d), (vs_x - d, Y_AV - 92)], fill=RED)
    draw.polygon([(vs_x, Y_AV + 92 - d), (vs_x + d, Y_AV + 92),
                  (vs_x, Y_AV + 92 + d), (vs_x - d, Y_AV + 92)], fill=RED)
    # Sombra + VS
    draw.text((vs_x + 3, Y_AV + 3), "VS", font=f_vs, fill=RED_DARK, anchor="mm")
    draw.text((vs_x,     Y_AV),     "VS", font=f_vs, fill=RED,      anchor="mm")

    # ── NOMES DOS JOGADORES ──────────────────────────────────────────────────
    y_names = Y_AV + SIZE_WIN // 2 + 62
    draw.text((win_x, y_names), win_nome, font=f_name_w, fill=GOLD, anchor="mm")
    draw.text((los_x, y_names), los_nome, font=f_name_l, fill=GRAY, anchor="mm")

    # ── DIVISOR CABEÇALHO / TABELA ───────────────────────────────────────────
    y_div = altura_cabecalho - 18
    draw.rectangle([(0, y_div), (largura, y_div + 4)], fill=RED)
    # Marcas decorativas pontilhadas no divisor
    for ox in range(0, largura, 55):
        draw.rectangle([(ox, y_div - 7), (ox + 30, y_div - 5)], fill=RED_DARK)

    # ── TRIÂNGULOS DE CANTO (topo da tabela) ─────────────────────────────────
    tri2 = 22
    draw.polygon([(0, y_div + 4), (tri2, y_div + 4), (0, y_div + 4 + tri2)], fill=RED)
    draw.polygon([(largura, y_div + 4), (largura - tri2, y_div + 4),
                  (largura, y_div + 4 + tri2)], fill=RED)

    # ── TABELA DE ESTATÍSTICAS ────────────────────────────────────────────────
    y_at = altura_cabecalho

    for idx, cat in enumerate(categorias):
        bg_c  = PANEL_A if idx % 2 == 0 else PANEL_B
        y0    = y_at + 8
        y1    = y_at + altura_linha - 8
        y_mid = y_at + altura_linha // 2

        # Fundo da linha
        draw.rectangle([(30, y0), (largura - 30, y1)],
                       fill=bg_c, outline=ACCENT_LINE, width=1)

        # Barras de acento lateral (vermelhas)
        draw.rectangle([(30,            y0), (35,            y1)], fill=RED)
        draw.rectangle([(largura - 35,  y0), (largura - 30,  y1)], fill=RED)

        # Painel central da categoria
        lw = 380
        cx = largura // 2
        draw.rectangle([(cx - lw//2, y0 + 14), (cx + lw//2, y1 - 14)],
                       fill=(28, 28, 44))
        draw.rectangle([(cx - lw//2, y0 + 14), (cx + lw//2, y0 + 17)],
                       fill=RED)
        draw.text((cx, y_mid), cat, font=f_label, fill=WHITE, anchor="mm")

        v1_raw, win1, icon1 = p1_data['stats'].get(cat, ("-", False, None))
        v2_raw, win2, icon2 = p2_data['stats'].get(cat, ("-", False, None))

        # ── Valor Jogador 1 (esquerda) ──
        px1 = 255
        if icon1:
            ico = await baixar_imagem(icon1)
            if ico:
                sz  = 125
                ico = ico.resize((sz, sz)).convert("RGBA")
                fundo.paste(ico, (px1 - sz//2, y_mid - sz//2), mask=ico)
                if win1:
                    tx = px1 - sz//2 - 28
                    draw.polygon([(tx - 12, y_mid + 8), (tx + 12, y_mid + 8), (tx, y_mid - 10)],
                                 fill=GREEN)
        else:
            clr1 = GREEN    if win1 else LOSER_COL
            fnt1 = f_val_w  if win1 else f_val_l
            draw.text((px1, y_mid), str(v1_raw), font=fnt1, fill=clr1, anchor="mm")
            if win1:
                bb1 = draw.textbbox((px1, y_mid), str(v1_raw), font=fnt1, anchor="mm")
                tx = bb1[0] - 22  # sempre 22px à esquerda da borda do texto
                draw.polygon([(tx - 12, y_mid + 8), (tx + 12, y_mid + 8), (tx, y_mid - 10)],
                             fill=GREEN)

        # ── Valor Jogador 2 (direita) ──
        px2 = largura - 255
        if icon2:
            ico = await baixar_imagem(icon2)
            if ico:
                sz  = 125
                ico = ico.resize((sz, sz)).convert("RGBA")
                fundo.paste(ico, (px2 - sz//2, y_mid - sz//2), mask=ico)
                if win2:
                    tx = px2 + sz//2 + 28
                    draw.polygon([(tx - 12, y_mid + 8), (tx + 12, y_mid + 8), (tx, y_mid - 10)],
                                 fill=GREEN)
        else:
            clr2 = GREEN    if win2 else LOSER_COL
            fnt2 = f_val_w  if win2 else f_val_l
            draw.text((px2, y_mid), str(v2_raw), font=fnt2, fill=clr2, anchor="mm")
            if win2:
                bb2 = draw.textbbox((px2, y_mid), str(v2_raw), font=fnt2, anchor="mm")
                tx = bb2[2] + 22  # sempre 22px à direita da borda do texto
                draw.polygon([(tx - 12, y_mid + 8), (tx + 12, y_mid + 8), (tx, y_mid - 10)],
                             fill=GREEN)

        draw = ImageDraw.Draw(fundo)
        y_at += altura_linha

    # ── RODAPÉ ───────────────────────────────────────────────────────────────
    draw.rectangle([(0, altura_total - 5), (largura, altura_total)], fill=RED)
    tri3 = 50
    draw.polygon([(0, altura_total), (0, altura_total - tri3), (tri3, altura_total)],
                 fill=RED)
    draw.polygon([(largura, altura_total), (largura - tri3, altura_total),
                  (largura, altura_total - tri3)], fill=RED)

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