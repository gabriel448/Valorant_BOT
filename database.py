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

    #criar tabelas
    # Tabela 1: O Jogador (Pura, sem guild_id)
    query_jogadores = """
    CREATE TABLE IF NOT EXISTS jogadores_monitorados (
        discord_user_id BIGINT PRIMARY KEY,
        riot_puuid VARCHAR(78) UNIQUE NOT NULL,
        riot_game_name VARCHAR(16) NOT NULL,
        riot_tag_line VARCHAR(5) NOT NULL,
        last_match_id VARCHAR(64) NULL,
        current_tier_int INTEGER DEFAULT 0,
        loss_streak INTEGER DEFAULT 0
    );
    """

    # Tabela 2: Configurações do Servidor
    query_servidores = """
    CREATE TABLE IF NOT EXISTS configuracoes_servidor (
        guild_id BIGINT PRIMARY KEY,
        alert_channel_id BIGINT NOT NULL
    );
    """

    # Tabela 3: A Tabela Associativa
    query_associacao = """
    CREATE TABLE IF NOT EXISTS jogadores_servidores (
        discord_user_id BIGINT REFERENCES jogadores_monitorados(discord_user_id),
        guild_id BIGINT,
        PRIMARY KEY (discord_user_id, guild_id)
    );
    """

    await conn.execute(query_jogadores)
    print("Tabela de jogadores criada/checada com sucesso")
    await conn.execute(query_servidores)
    print("Tabela de servidores criada/checada com sucesso")
    await conn.execute(query_associacao)
    print("Tabela de associacao criada/checada com sucesso")
    print("Estrutura Relacional (3 Tabelas) criada com sucesso!")

    #fecha a conexao apos a config
    await conn.close()

#funcao pra inserir jogadores no banco de dados
async def cadastrar_alvo_bd(discord_user_id, guild_id, riot_puuid, riot_game_name, riot_tag_line):
    """
    Insere o jogador no banco de dados. Se ele já existir, apenas atualiza os dados.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    
    query_jogador = """
    INSERT INTO jogadores_monitorados (discord_user_id, riot_puuid, riot_game_name, riot_tag_line)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (discord_user_id) DO UPDATE 
    SET riot_puuid = EXCLUDED.riot_puuid,
        riot_game_name = EXCLUDED.riot_game_name,
        riot_tag_line = EXCLUDED.riot_tag_line;
    """
    
    # Executa a query substituindo os $1, $2... pelos valores reais das variáveis
    await conn.execute(query_jogador, discord_user_id, riot_puuid, riot_game_name, riot_tag_line)

    # 2. Insere a relação "Jogador <-> Servidor" na 3ª tabela
    # Se o cara já tá nesse servidor, o DO NOTHING faz ele não dar erro.
    query_vinculo = """
    INSERT INTO jogadores_servidores (discord_user_id, guild_id)
    VALUES ($1, $2)
    ON CONFLICT (discord_user_id, guild_id) DO NOTHING;
    """
    await conn.execute(query_vinculo, discord_user_id, guild_id)

    print(f'Jogador {riot_game_name} cadastrado na base de dados com sucesso')
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


async def configurar_canal_alerta(guild_id, channel_id):
    """
    Salva ou atualiza o canal oficial de alertas de um servidor (Upsert).
    """
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
    INSERT INTO configuracoes_servidor (guild_id, alert_channel_id)
    VALUES ($1, $2)
    ON CONFLICT (guild_id) DO UPDATE 
    SET alert_channel_id = EXCLUDED.alert_channel_id;
    """
    await conn.execute(query, guild_id, channel_id)
    await conn.close()

async def pegar_canais_alerta_do_jogador(discord_user_id):
    """
    Faz um JOIN entre a Tabela 3 e a Tabela 2 para descobrir todos os
    canais de alerta espalhados pelos servidores em que este jogador está!
    """

    conn = await asyncpg.connect(DATABASE_URL)

    # Pegue o ID do canal (Tabela 2) usando os vínculos (Tabela 3)
    query = """
    SELECT c.alert_channel_id
    FROM jogadores_servidores js
    INNER JOIN configuracoes_servidor c ON js.guild_id = c.guild_id
    WHERE js.discord_user_id = $1;
    """

    registros = await conn.fetch(query, discord_user_id)
    await conn.close()

    #retorna uma lista limpa so com os IDs dos canais [12345, 67890, ...]
    return [registros['alert_channel_id'] for registro in registros]