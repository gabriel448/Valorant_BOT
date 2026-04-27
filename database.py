import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime


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
        loss_streak INTEGER DEFAULT 0,
        pontos_explanator INTEGER DEFAULT 0,
        alertas_md3 INTEGER DEFAULT 0,
        mes_referencia VARCHAR(7) DEFAULT '1970-01'
    );
    """

    # Tabela 2: Configurações do Servidor
    query_servidores = """
    CREATE TABLE IF NOT EXISTS configuracoes_servidor (
        guild_id BIGINT PRIMARY KEY,
        alert_channel_id BIGINT NOT NULL,
        alert_role_id BIGINT NULL,
        modo_ia INTEGER DEFAULT 2
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

async def pegar_canais_e_cargos_do_jogador(discord_user_id):
    """
    Faz um JOIN para descobrir todos os canais E cargos de alerta 
    espalhados pelos servidores em que este jogador está.
    """

    conn = await asyncpg.connect(DATABASE_URL)

    query = """
    SELECT c.alert_channel_id, c.alert_role_id, c.modo_ia
    FROM jogadores_servidores js
    INNER JOIN configuracoes_servidor c ON js.guild_id = c.guild_id
    WHERE js.discord_user_id = $1;
    """

    registros = await conn.fetch(query, discord_user_id)
    await conn.close()

    #retorna uma lista limpa so com os IDs dos canais e dos cargos
    return [{
            'canal': r['alert_channel_id'], 
            'cargo': r['alert_role_id'],
            'modo_ia': r['modo_ia']
        } for r in registros]

async def atualizar_tier_jogador(riot_puuid, novo_tier_int):
    """
    Atualiza o numero inteiro que representa o elo do jogador
    """

    conn = await asyncpg.connect(DATABASE_URL)
    query = "UPDATE jogadores_monitorados SET current_tier_int = $1 WHERE riot_puuid = $2"
    await conn.execute(query, novo_tier_int, riot_puuid)
    await conn.close()

async def atualizar_loss_streak(riot_puuid, novo_streak):
    """"
    atualiza a contagem de derrotas seguidas do jogador
    """
    conn = await asyncpg.connect(DATABASE_URL)
    query = "UPDATE jogadores_monitorados SET loss_streak = $1 WHERE riot_puuid = $2"
    await conn.execute(query, novo_streak, riot_puuid)
    await conn.close()

async def pegar_todos_canais_configurados():
    """Busca o ID de todos os canais de alerta de todos os servidores."""
    conn = await asyncpg.connect(DATABASE_URL)
    registros = await conn.fetch("SELECT alert_channel_id FROM configuracoes_servidor")
    await conn.close()
    
    return [registro['alert_channel_id'] for registro in registros]

async def configurar_cargo_alerta(guild_id, role_id):
    """Atualiza o cargo do servidor. Retorna True se atualizou, False se o servidor não existir."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    query = """
    UPDATE configuracoes_servidor 
    SET alert_role_id = $2 
    WHERE guild_id = $1;
    """
    
    # O execute retorna uma string de status. Ex: "UPDATE 1" (deu certo) ou "UPDATE 0" (linha não encontrada)
    status = await conn.execute(query, guild_id, role_id)
    await conn.close()
    
    return status == "UPDATE 1"

async def remover_alvo_bd(nome: str, tag:str):
    """
    Remove o jogador de todas as tabelas do banco de dados usando o Riot ID.
    Retorna True se deletou com sucesso, False se o jogador não existir.
    """
    conn = await asyncpg.connect(DATABASE_URL)

    #achando o jogador no banco
    query_busca = """
        SELECT discord_user_id 
        FROM jogadores_monitorados 
        WHERE riot_game_name = $1 riot_tag_line = $2
    """

    registro = await conn.fetchrow(query_busca, nome, tag)

    if not registro:
        await conn.close()
        return False
    
    discord_user_id = registro['discord_user_id']

    #retirando das tabelas
    await conn.execute("DELETE FROM jogadores_servidores WHERE discord_user_id = $1", discord_user_id)
    await conn.execute("DELETE FROM jogadores_monitorados WHERE discord_user_id = $1", discord_user_id)

    await conn.close()
    return True

async def configurar_modo_ia (guild_id, modo_ia):
    """Atualiza o modo de toxicidade da IA. Retorna True se sucesso."""
    conn = await asyncpg.connect(DATABASE_URL)
    query = "UPDATE configuracoes_servidor SET modo_ia = $2 WHERE guild_id = $1;"
    status = await conn.execute(query, guild_id, modo_ia)
    await conn.close()
    return status == "UPDATE 1"

async def pegar_dono_do_alvo(nome: str, tag: str):
    """
    Busca o ID do Discord de quem cadastrou esse Riot ID.
    Retorna o ID numérico ou None se não existir.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    query = """
        SELECT discord_user_id 
        FROM jogadores_monitorados 
        WHERE riot_game_name = $1 AND riot_tag_line = $2
    """
    registro = await conn.fetchrow(query, nome, tag)
    await conn.close()
    
    return registro['discord_user_id'] if registro else None

async def alterar_pontos_explanator(puuid: str, qtd_punicoes: int, qtd_elogios: int):
    """
    Motor da MD3 e da Temporada Regular do Explanator.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    
    # 1. Qual é o mês atual? (ex: "2026-04")
    mes_atual = datetime.now().strftime("%Y-%m")
    
    # 2. Pega os dados atuais do jogador
    query_busca = "SELECT pontos_explanator, alertas_md3, mes_referencia FROM jogadores_monitorados WHERE riot_puuid = $1"
    registro = await conn.fetchrow(query_busca, puuid)
    
    if not registro:
        await conn.close()
        print('Erro na busca no data base')
        return

    pontos = registro['pontos_explanator']
    alertas_md3 = registro['alertas_md3']
    mes_banco = registro['mes_referencia']
    
    # 3. LAZY RESET (Começo do mês)
    if mes_banco != mes_atual:
        pontos = 0
        alertas_md3 = 0
        
    # 4. FASE DE MD3
    if alertas_md3 < 3:
        # A cada aviso na MD3, os motivos valem MUITO mais pontos. Ex: peso 6.
        # Se ele cometeu 3 crimes num jogo só, ele ganha 18 pontos de uma vez!
        pontos += (qtd_punicoes * 6)
        pontos -= (qtd_elogios * 6)
        
        alertas_md3 += 1
        
        # FINALIZOU A MD3! Aplicar os limites (Clamp)
        if alertas_md3 == 3:
            if pontos > 53: pontos = 53 # Teto: Diamante 3
            if pontos < 6: pontos = 6   # Piso: Ferro 3
    
    # 5. TEMPORADA REGULAR (Já fez a MD3)
    else:
        # Aqui o peso volta ao normal (+1 por crime, -1 por elogio)
        pontos += qtd_punicoes
        pontos -= qtd_elogios
        
        # Travas de segurança padrão (0 a 74)
        if pontos > 74: pontos = 74
        if pontos < 0: pontos = 0

    # 6. Salva tudo no banco
    query_update = """
        UPDATE jogadores_monitorados 
        SET pontos_explanator = $1, alertas_md3 = $2, mes_referencia = $3
        WHERE riot_puuid = $4;
    """
    await conn.execute(query_update, pontos, alertas_md3, mes_atual, puuid)
    await conn.close()

async def pegar_top_bagres(guild_id: int):
    """
    Busca os 10 jogadores com mais pontos no Explanator dentro de um servidor específico.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    mes_atual = datetime.now().strftime("%Y-%m")

    query = """
        WITH ranking_resetado AS (
            SELECT 
                j.riot_game_name, 
                j.riot_tag_line, 
                j.riot_puuid,
                CASE WHEN j.mes_referencia = $2 THEN j.pontos_explanator ELSE 0 END as pontos_explanator,
                CASE WHEN j.mes_referencia = $2 THEN j.alertas_md3 ELSE 0 END as alertas_md3
            FROM jogadores_monitorados j
            INNER JOIN jogadores_servidores js ON j.discord_user_id = js.discord_user_id
            WHERE js.guild_id = $1
        )
        SELECT * FROM ranking_resetado 
        ORDER BY pontos_explanator DESC 
        LIMIT 10;
    """

    registros = await conn.fetch(query, guild_id, mes_atual)
    await conn.close()
    return registros