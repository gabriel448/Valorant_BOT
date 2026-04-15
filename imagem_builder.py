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
        fonte_titulo = ImageFont.truetype("LiberationSans-Bold.ttf", 48) # Maior e mais negrito
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