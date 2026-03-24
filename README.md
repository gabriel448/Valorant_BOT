# 🤖 Valorant Match Monitor (Discord Bot)

Um bot de Discord desenvolvido em Python para monitoramento contínuo e assíncrono de partidas de Valorant. 
O sistema consome APIs externas, gerencia a persistência de usuários em um banco de dados em nuvem e aplica regras de negócio customizadas para análise de métricas de desempenho (MatchDTOs).

Este projeto foi construído para aplicar conceitos práticos de Engenharia de Software, Integração de Sistemas e Banco de Dados.

## 🚀 Tecnologias e Ferramentas Utilizadas

* **Linguagem:** Python 3.12+
* [cite_start]**APIs e Integrações:** `discord.py` (Discord Gateway API), Unofficial HenrikDev API (Valorant REST API)[cite: 40].
* [cite_start]**Banco de Dados:** PostgreSQL (Hospedado via Supabase DBaaS)[cite: 130].
* [cite_start]**Comunicação de Rede:** `aiohttp` (HTTP Client assíncrono), `asyncpg` (Driver assíncrono para PostgreSQL)[cite: 130, 161].
* **Segurança:** `python-dotenv` para gerenciamento de variáveis de ambiente.

## 🧠 Arquitetura e Habilidades Demonstradas

Ao longo do desenvolvimento deste projeto, foram aplicados conceitos fundamentais de Sistemas de Informação:

### 1. Programação Assíncrona (Async/Await)
O bot opera de forma totalmente não-bloqueante. A utilização do loop de eventos nativo do Python (`asyncio`) permite que o sistema lide com respostas no chat do Discord simultaneamente enquanto realiza consultas pesadas de rede e transações no banco de dados.

### 2. Gerenciamento de Tráfego e Rate Limits (Polling Bifásico)
[cite_start]Para monitorar as partidas em tempo real sem sobrecarregar a API externa e evitar bloqueios de segurança (HTTP 429 Too Many Requests) [cite: 51][cite_start], foi implementada uma arquitetura de **Polling Bifásico**[cite: 67]:
* **Consulta Rasa:** Uma requisição leve (baixa latência) para verificar se o ID da última partida no servidor difere do armazenado no banco de dados.
* [cite_start]**Consulta Profunda:** Acionada apenas mediante validação positiva da etapa anterior, extraindo o pacote completo de dados da partida (MatchDTO)[cite: 78].
* [cite_start]**Distribuição Escalonada (Staggered Polling):** Uso de *delays* controlados (`asyncio.sleep()`) entre as requisições de cada usuário para diluir o tráfego de rede[cite: 52, 57].

### 3. Modelagem de Banco de Dados Relacional
[cite_start]A infraestrutura utiliza o **PostgreSQL** para garantir a integridade dos dados e prevenir redundâncias lógicas[cite: 130, 131].
* [cite_start]Mapeamento biunívoco entre entidades (Discord User ID ↔ Riot PUUID) utilizando Chaves Primárias (`PRIMARY KEY`) e restrições (`UNIQUE`, `NOT NULL`)[cite: 134].
* [cite_start]Operações seguras e atômicas de *Upsert* (`INSERT ON CONFLICT DO UPDATE`) para impedir o estancamento sistêmico durante atualizações simultâneas de usuários[cite: 137, 138].

### 4. Consumo de REST APIs e Manipulação de JSON
Desenvolvimento de métodos de extração precisos para navegar em grandes árvores de dados JSON, decodificando atributos específicos (K/D/A, Econ Rating, Rounds Played) e lidando com paginação e formatação segura de URLs (URL Encoding).

## ⚙️ Como executar localmente

1. Clone este repositório:
   ```bash
   git clone [https://github.com/SeuUsuario/bot-valorant-zoeira.git](https://github.com/SeuUsuario/bot-valorant-zoeira.git)
