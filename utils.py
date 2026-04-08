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