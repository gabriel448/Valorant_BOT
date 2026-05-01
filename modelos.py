from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class DadosJogador:
    puuid: str
    kills: int
    deaths: int
    assists: int
    kd_ratio: float
    porcentagem_peito: float
    rounds_jogados: int
    e_mono_sniper: bool
    elo_banco_int: int
    estatisticas_alvo: Dict[str, Any] # Mantemos como dict porque vem direto da API
    dados_mmr: Dict[str, Any]
    headshots: Any
    bodyshots: Any
    legshots: Any


@dataclass
class ResultadoJulgamento: # Serve tanto para 'punitivo' quanto para 'elogio'
    ativo: bool  
    motivos: List[str]
    motivos_ia: List[str]
    rank_up: bool = False

@dataclass
class DadosEmbed:
    foto_agente: Any
    banner_jogador: Any
    nome_agente: str
    mapa: str
    elo_imagem: Any

@dataclass
class DadosEnvio:
    destinos: List[Dict[str, int]]
    discord_id: int
    dados_jogador: DadosJogador
    nome_jogador: str
    dados_embed: DadosEmbed
    punicao: ResultadoJulgamento
    elogio: ResultadoJulgamento
    client: Any

@dataclass
class DadosElo:
    elo_atual_int: int
    elo_atual_nome: str
    elo_atual_imagem: Any

@dataclass
class DadosPartidasRecentes:
    partidas_recentes: List[Any]
    ultimo_match_salvo: Any
    puuid: str
    nome_jogador: str
    loss_streak_atual: int
    win_streak_atual: int
    cache_partida_vistas: Any
