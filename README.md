# 🤖 Valorant BOT (Discord Bot - "O Explanator")

Um bot de Discord desenvolvido em Python para monitoramento contínuo e assíncrono de partidas de Valorant. 
O sistema consome APIs externas, gerencia a persistência de usuários em um banco de dados em nuvem, aplica regras de negócio customizadas para análise de métricas de desempenho (MatchDTOs) e utiliza Inteligência Artificial Generativa para criar interações dinâmicas. Originalmente criado para humilhar o mau desempenho, o bot evoluiu para um sistema completo de julgamento, premiando MVPs e ranqueando a ruindade em uma tabela de liderança gerada dinamicamente.

Este projeto foi construído para aplicar conceitos práticos de Engenharia de Software, Integração de Sistemas, Banco de Dados, Processamento de Imagens e Integração com LLMs (Large Language Models).

## 🚀 Tecnologias e Ferramentas Utilizadas

* **Linguagem:** Python 3.11+
* **APIs e Integrações:** `discord.py` (Discord Gateway API), Unofficial HenrikDev API (Valorant REST API), Google Gemini API (LLM).
* **Banco de Dados:** PostgreSQL (Hospedado via Supabase DBaaS).
* **Comunicação de Rede:** `aiohttp` (HTTP Client assíncrono), `asyncpg` (Driver assíncrono para PostgreSQL).
* **Inteligência Artificial:** `google-generativeai` para geração dinâmica de linguagem natural em múltiplas personas.
* **Processamento de Imagens:** `Pillow` (PIL) para renderização gráfica dinâmica.
* **Infraestrutura/Deploy:** `Docker` para conteinerização e Oracle Cloud Infrastructure (OCI).

## 🧠 Arquitetura e Habilidades Demonstradas

Ao longo do desenvolvimento deste projeto, foram aplicados conceitos fundamentais de Sistemas de Informação:

### 1. Programação Assíncrona (Async/Await)
O bot opera de forma totalmente não-bloqueante. A utilização do loop de eventos nativo do Python (`asyncio`) permite que o sistema lide com respostas no chat do Discord simultaneamente enquanto realiza consultas pesadas de rede e transações no banco de dados.

### 2. Gerenciamento de Tráfego e Rate Limits (Polling Bifásico)
Para monitorar as partidas em tempo real sem sobrecarregar a API externa e evitar bloqueios de segurança (HTTP 429 Too Many Requests), foi implementada uma arquitetura de **Polling Bifásico**:
* **Consulta Rasa:** Uma requisição leve para verificar se o ID da última partida difere do armazenado no banco de dados.
* **Consulta Profunda:** Acionada apenas mediante validação positiva, extraindo o pacote completo de dados da partida (MatchDTO).
* **Distribuição Escalonada (Staggered Polling):** Uso de *delays* controlados entre requisições de usuários para diluir o tráfego.

### 3. Modelagem de Banco de Dados Relacional
Infraestrutura PostgreSQL normalizada (3FN) utilizando Tabelas Associativas para gerenciar a relação (N:M) entre Jogadores e Servidores do Discord, além de persistência de pontuação para o sistema de Ranking. Operações atômicas de *Upsert* e travas de segurança (`GREATEST`/`LEAST`) na manipulação de pontos.

### 4. Sincronização de Estado (Event Sourcing) e Tolerância a Falhas
Rastreamento de histórico offline para atualizar contadores sequenciais de vitórias/derrotas de forma precisa. O sistema também implementa filtros avançados de validação (ex: ignorar partidas que terminaram em empate no cálculo de sequências de derrotas).

### 5. Integração com IA Generativa (LLMs)
O bot atua como um pipeline de dados: sintetiza as métricas frias da partida e as injeta como contexto para a IA gerar textos. Possui suporte a múltiplas "Personalidades" (Tóxico, Comentarista, Leve), adaptando o tom da resposta com base nas instruções de sistema (System Prompts).

### 6. Geração Dinâmica de Assets Visuais
Uso da biblioteca Pillow para criar tabelas de liderança (Leaderboards) "on-the-fly". O sistema baixa banners de jogadores, aplica máscaras de transparência (gradientes alfa) e sobrepõe textos e ícones oficiais de Elo renderizados em tempo real.

---

## ⚖️ As Leis do Explanator

O núcleo analítico julga o desempenho dos jogadores baseado em regras de negócio rígidas. 

### 📉 Condições de Punição
* **Queda de Elo:** Qualquer rebaixamento em partidas Competitivas gera uma notificação de vexame.
* **O Pacifista (Zero Kills):** Jogar 10 *rounds* ou mais em uma partida sem conseguir nenhuma eliminação.
* **Desastre de K/D:** Terminar a partida com um K/D Ratio inferior ou igual a `0.5`.
* **Fundo do Poço (Loss Streak):** Acumular `4` ou mais derrotas consecutivas (empates pausam, mas não resetam o contador).
* **Mira Magnética de Abdômen:** Se `84%` ou mais dos tiros acertados foram no peito (*bodyshots*). 
  * *🛡️ Exceção do Sniper:* A punição de mira é perdoada e ignorada se mais de 50% dos abates do jogador vieram de Operator, Outlaw, Marshal ou Tour de Force (Chamber).

### 🏆 Condições de Elogio
* **Promoção de Elo (Rank Up):** O bot comemora a subida de Elo com um Embed dourado exclusivo e a imagem oficial da nova medalha do jogador.
* **Alerta de MVP:** Se o jogador finalizar a partida com K/D Ratio igual ou superior a `2.0` e, no mínimo, `20` eliminações, o modo Narrador da IA gera uma exaltação pública elogiando o desempenho.

---

## 📊 O "Anti-Rank" do Explanator
Transformamos a ruindade em um ecossistema competitivo. O bot mantém uma pontuação oculta para cada jogador rastreado:
* **Mecânica de Pontos:** Receber uma punição concede `+1 Ponto`. Receber um Elogio de MVP/Rank Up subtrai `-1 Ponto`.
* **Escala de Elo Invertida:** A cada 3 pontos acumulados, o jogador sobe na escala do Explanator (indo do "Ferro 1" até o "Radiante"). O limite máximo mecânico do banco de dados é de 74 pontos.
* **A Parede da Vergonha:** Usando o comando de liderança, o bot gera uma imagem mostrando os maiores bagres do servidor com seus devidos fundos dinâmicos.

---

## 🛠️ Comandos do Bot (Slash Commands)

O bot conta com Slash Commands integrados para administração e visualização no Discord:

* `/cadastrar-alvo [riot_id]`: Adiciona um novo jogador ao monitoramento do Explanator.
* `/remover-alvo [riot_id]`: Remove um jogador do monitoramento e do banco de dados (Usuários normais só podem remover a si mesmos; ADMs podem remover qualquer um).
* `/top-bagres`: Gera, compila e envia a imagem dinâmica do Leaderboard do Explanator ordenado pelos jogadores mais punidos do servidor atual.
* `/modo-ia`: (Apenas ADMs) Altera a personalidade global de geração de texto do bot entre `toxico` (pesado e sem filtro), `leve` (ironia branda) e `comentarista` (análise formal de esports).

  

