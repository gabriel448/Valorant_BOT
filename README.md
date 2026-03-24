# 🤖 Valorant Match Monitor (Discord Bot)

Um bot de Discord desenvolvido em Python para monitoramento contínuo e assíncrono de partidas de Valorant. 
O sistema consome APIs externas, gerencia a persistência de usuários em um banco de dados em nuvem e aplica regras de negócio customizadas para análise de métricas de desempenho (MatchDTOs).

Este projeto foi construído para aplicar conceitos práticos de Engenharia de Software, Integração de Sistemas e Banco de Dados.

## 🚀 Tecnologias e Ferramentas Utilizadas

* **Linguagem:** Python 3.12+
* **APIs e Integrações:** `discord.py` (Discord Gateway API), Unofficial HenrikDev API (Valorant REST API).
* **Banco de Dados:** PostgreSQL (Hospedado via Supabase DBaaS).
* **Comunicação de Rede:** `aiohttp` (HTTP Client assíncrono), `asyncpg` (Driver assíncrono para PostgreSQL).
* **Segurança:** `python-dotenv` para gerenciamento de variáveis de ambiente.

## 🧠 Arquitetura e Habilidades Demonstradas

Ao longo do desenvolvimento deste projeto, foram aplicados conceitos fundamentais de Sistemas de Informação:

### 1. Programação Assíncrona (Async/Await)
O bot opera de forma totalmente não-bloqueante. A utilização do loop de eventos nativo do Python (`asyncio`) permite que o sistema lide com respostas no chat do Discord simultaneamente enquanto realiza consultas pesadas de rede e transações no banco de dados.

### 2. Gerenciamento de Tráfego e Rate Limits (Polling Bifásico)
Para monitorar as partidas em tempo real sem sobrecarregar a API externa e evitar bloqueios de segurança (HTTP 429 Too Many Requests), foi implementada uma arquitetura de **Polling Bifásico**:
* **Consulta Rasa:** Uma requisição leve (baixa latência) para verificar se o ID da última partida no servidor difere do armazenado no banco de dados.
* **Consulta Profunda:** Acionada apenas mediante validação positiva da etapa anterior, extraindo o pacote completo de dados da partida (MatchDTO).
* **Distribuição Escalonada (Staggered Polling):** Uso de *delays* controlados (`asyncio.sleep()`) entre as requisições de cada usuário para diluir o tráfego de rede .

### 3. Modelagem de Banco de Dados Relacional
A infraestrutura utiliza o **PostgreSQL** para garantir a integridade dos dados e prevenir redundâncias lógicas.
* Mapeamento biunívoco entre entidades (Discord User ID ↔ Riot PUUID) utilizando Chaves Primárias (`PRIMARY KEY`) e restrições (`UNIQUE`, `NOT NULL`).
* Operações seguras e atômicas de *Upsert* (`INSERT ON CONFLICT DO UPDATE`) para impedir o estancamento sistêmico durante atualizações simultâneas de usuários.

### 4. Consumo de REST APIs e Manipulação de JSON
Desenvolvimento de métodos de extração precisos para navegar em grandes árvores de dados JSON, decodificando atributos específicos (K/D/A, Econ Rating, Rounds Played) e lidando com paginação e formatação segura de URLs (URL Encoding).

## ⚙️ Como executar localmente

1. Clone este repositório:
   ```bash
   git clone [https://github.com/SeuUsuario/bot-valorant-zoeira.git](https://github.com/SeuUsuario/bot-valorant-zoeira.git)
