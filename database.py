import asyncpg
import os
from dotenv import load_dotenv

#carregando a url do .env
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
HENRIK_API_KEY = os.getenv('HENRIK_API_KEY')

async def iniciar_banco():
    print("Conectando com o banco de dados...")

    #cria a conexao com a database
    conn = await asyncpg.connect(DATABASE_URL)

    #cria a tabela
    query_criacao_tabela = """
    CREATE TABLE IF NOT EXISTS jogadores_monitorados (
        discord_user_id BIGINT PRIMARY KEY,
        guild_id BIGINT NOT NULL,
        riot_puuid VARCHAR(78) UNIQUE NOT NULL,
        riot_tag_line VARCHAR(5) NOT NULL,
        riot_game_name VARCHAR(16),
        last_match_id VARCHAR(64) NULL,
        current_tier_int INTEGER DEFAULT 0,
        loss_streak INTEGER DEFAULT 0,
        alert_channel_id BIGINT NOT NULL
    );
    """
    await conn.execute(query_criacao_tabela)
    print("Tabela 'jogadores_monitorados' verificada/criada com sucesso")

    #fecha a conexao apos a config
    await conn.close()

#funcao pra inserir jogadores no banco de dados
async def cadastrar_alvo_bd(discord_user_id, guild_id, riot_puuid, riot_game_name, riot_tag_line, alert_channel_id):
    """
    Insere o jogador no banco de dados. Se ele já existir, apenas atualiza os dados.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    
    query = """
    INSERT INTO jogadores_monitorados (discord_user_id, guild_id, riot_puuid, riot_game_name, riot_tag_line, alert_channel_id)
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT (discord_user_id) DO UPDATE 
    SET riot_puuid = EXCLUDED.riot_puuid,
        riot_game_name = EXCLUDED.riot_game_name,
        riot_tag_line = EXCLUDED.riot_tag_line,
        alert_channel_id = EXCLUDED.alert_channel_id;
    """
    
    # Executa a query substituindo os $1, $2 pelos valores reais das variáveis
    await conn.execute(query, discord_user_id, guild_id, riot_puuid, riot_game_name, riot_tag_line, alert_channel_id)
    await conn.close()

async def pegar_todos_alvos():
    """
    Busca no banco de  tados a lista de todos os jogadores
    retorna um tipo Record no caso do async
    """
    conn = await asyncpg.connect(DATABASE_URL)
    #selecionando todas as colunas
    registros = await conn.fetch("SELECT * FROM jogadores_monitorados")
    await conn.close()
    return registros

async def atualizar_match_id(riot_puuid, novo_match_id):
    """
    Busca no banco de dados a lista de todos os jogadores monitorados.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    query = "UPDATE jogadores_monitorados SET last_match_id = $1 WHERE riot_puuid = $2"
    await conn.execute(query, novo_match_id, riot_puuid)
    print('Ultima partida atualizada com sucesso')
    await conn.close()          