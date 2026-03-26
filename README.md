# 🤖 Valorant BOT (Discord Bot)

Um bot de Discord desenvolvido em Python para monitoramento contínuo e assíncrono de partidas de Valorant. 
O sistema consome APIs externas, gerencia a persistência de usuários em um banco de dados em nuvem, aplica regras de negócio customizadas para análise de métricas de desempenho (MatchDTOs) e utiliza Inteligência Artificial Generativa para criar interações dinâmicas e bem-humoradas.

Este projeto foi construído para aplicar conceitos práticos de Engenharia de Software, Integração de Sistemas, Banco de Dados e Integração com LLMs (Large Language Models).

## 🚀 Tecnologias e Ferramentas Utilizadas

* **Linguagem:** Python 3.12+
* **APIs e Integrações:** `discord.py` (Discord Gateway API), Unofficial HenrikDev API (Valorant REST API), Google Gemini API (LLM).
* **Banco de Dados:** PostgreSQL (Hospedado via Supabase DBaaS).
* **Comunicação de Rede:** `aiohttp` (HTTP Client assíncrono), `asyncpg` (Driver assíncrono para PostgreSQL).
* **Inteligência Artificial:** `google-generativeai` para geração dinâmica de linguagem natural.
* **Segurança e Configuração:** `python-dotenv` para gerenciamento de variáveis de ambiente.

## 🧠 Arquitetura e Habilidades Demonstradas

Ao longo do desenvolvimento deste projeto, foram aplicados conceitos fundamentais de Sistemas de Informação:

### 1. Programação Assíncrona (Async/Await)
O bot opera de forma totalmente não-bloqueante. A utilização do loop de eventos nativo do Python (`asyncio`) permite que o sistema lide com respostas no chat do Discord simultaneamente enquanto realiza consultas pesadas de rede e transações no banco de dados.

### 2. Gerenciamento de Tráfego e Rate Limits (Polling Bifásico)
Para monitorar as partidas em tempo real sem sobrecarregar a API externa e evitar bloqueios de segurança (HTTP 429 Too Many Requests), foi implementada uma arquitetura de **Polling Bifásico**:
* **Consulta Rasa:** Uma requisição leve (baixa latência) para verificar se o ID da última partida no servidor difere do armazenado no banco de dados.
* **Consulta Profunda:** Acionada apenas mediante validação positiva da etapa anterior, extraindo o pacote completo de dados da partida (MatchDTO).
* **Distribuição Escalonada (Staggered Polling):** Uso de *delays* controlados (`asyncio.sleep()`) entre as requisições de cada usuário para diluir o tráfego de rede.

### 3. Modelagem de Banco de Dados Relacional
A infraestrutura utiliza o **PostgreSQL** para garantir a integridade dos dados e prevenir redundâncias lógicas. Estrutura normalizada (3FN) utilizando Tabelas Associativas para gerenciar a relação de *Muitos-para-Muitos* (N:M) entre Jogadores e Servidores do Discord.
* Mapeamento utilizando Chaves Primárias Compostas (`PRIMARY KEY`) e restrições (`UNIQUE`, `NOT NULL`).
* Operações seguras e atômicas de *Upsert* (`INSERT ON CONFLICT DO UPDATE`) para impedir o estancamento sistêmico durante atualizações.
* Consultas complexas utilizando `INNER JOIN` para roteamento dinâmico de mensagens.

### 4. Sincronização de Estado (Event Sourcing)
Implementação de um algoritmo de "viagem no tempo" para lidar com o histórico offline do bot. O sistema rastreia e reconstrói eventos passados (partidas jogadas enquanto o bot estava desligado) para atualizar contadores sequenciais de vitórias/derrotas de forma precisa, garantindo a integridade dos dados na retomada do serviço.

### 5. Integração com Inteligência Artificial Generativa (LLMs)
Implementação de *Prompt Engineering* (Instruções de Sistema / *System Prompt*) utilizando a API do Google Gemini. O bot atua como um pipeline de dados: ele sintetiza as métricas frias da partida (K/D, Agente, Mapa, % de tiros) e as injeta como contexto para a IA gerar, em tempo real, textos de resposta sarcásticos, dinâmicos e exclusivos. Isso transforma logs de dados massantes em interações de alto engajamento.

---

## ⚖️ Tribunal do Valorant: Condições de Punição

O núcleo analítico do bot julga o desempenho dos jogadores baseado em regras de negócio rígidas. Atualmente, os gatilhos que acionam a notificação de vexame no servidor são:

* **📉 Queda de Elo (Derretimento):** O bot rastreia o *Tier* numérico atual e compara com o persistido no banco de dados. Qualquer rebaixamento em partidas Competitivas gera uma punição pública.
* **🕊️ O Pacifista (Zero Kills):** Jogar 10 *rounds* ou mais em uma única partida e não conseguir absolutamente nenhuma eliminação (0 *Kills*).
* **🗑️ Desastre de K/D:** Terminar a partida com um K/D Ratio (Abates / Mortes) inferior ou igual a `0.5`.
* **📉 Fundo do Poço (Loss Streak):** Acumular `4` ou mais derrotas consecutivas estritamente em partidas ranqueadas.
* **🧲 Mira Magnética de Abdômen (Crosshair Placement):** O bot calcula a porcentagem de distribuição de dano. Se `84%` ou mais dos tiros acertados no inimigo foram no peito (*bodyshots*), o jogador é punido por não mirar na cabeça.

  

