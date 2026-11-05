# Diário da Tarefa 1 — Problema e coleta bruta (sem rótulo)

**Período:** 17/08/2026 a 17/09/2026  
**Projeto:** Preditor de degradação de rede com RTT normalizado (independente da rota)  
**Modelo desta disciplina:** árvore de decisão. Nesta tarefa não se treina árvore.

**Equipe:** Grupo 42  
**Integrantes:**  
- Wendell Rodrigues Macedo  
- Vinicius Firmino Souto  
- Fernando Paiva Coelho  
- João Gustavo Sanches  
- Daniel Dias Paranhos  
**Scrum Master da tarefa:** Vinicius Firmino Souto  
**Repositório GitHub:** [https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede](https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede)

> Esta tarefa entrega o problema e o **dado cru**. Não há classe OK, RISCO ou FALHA. Não há baseline, não há mediana e não há árvore. Quem rotular aqui mistura a coleta com a decisão da Tarefa 2.
>
> A rota entra na coleta só para haver caminhos curtos e longos no mesmo arquivo. RTT alto **não** é falha. País, IP e nome da rota **não** serão coluna da árvore.

### Contrato desta tarefa

| | Artefato | Quem usa depois |
|---|---|---|
| **Entra** | RFC do projeto | — |
| **Sai** | RFC preenchido pelo grupo (problema, horizonte, custo de errar FALHA, fora de escopo) | Tarefas 2 e 5 |
| **Sai** | Dicionário v0.1 só com colunas **brutas** da medição | Tarefa 2 |
| **Sai** | `data/raw/` + `config/` + `requirements.txt` | Tarefa 2 **é obrigada a usar este bruto** |
| **Sai** | Este diário | Tarefas seguintes |

**Não sai daqui:** baseline, rótulo, `z_robusto`, split, árvore, métrica de modelo.

---

## 1. Definição do problema

Responder no diário. A resposta tem de bater com o RFC.

| Pergunta | Resposta do grupo |
|---|---|
| Qual evento a árvore vai classificar? | Degradação do fluxo em relação ao **próprio** normal: OK, RISCO ou FALHA. Não é “rota longa” nem “RTT acima de 100 ms”. |
| O que é um fluxo? | `fluxo_id = probe_id \| dst_addr` (origem, destino e, se existir, `measurement_id`). |
| O que é cada linha do bruto? | Uma medição ICMP desse fluxo, com timestamp. Ainda **sem** classe. |
| Qual horizonte fica para depois? | Detector: estado da medição atual. Preditor: estado 12 minutos à frente. A árvore só entra na Tarefa 3. |
| Quem usa o alerta? | Quem opera o enlace: investigar (FALHA), observar (RISCO) ou não agir (OK). |
| O que está proibido como definição de falha? | Limiar global de RTT, país, continente ou nome da rota. |

- [x] RFC do grupo preenchido a partir desta tabela ([RFC_Preditor_Degradacao_Rede.md](../RFC_Preditor_Degradacao_Rede.md))
- [x] Dicionário v0.1 só com variáveis brutas ([metadados/dicionario_dados_v0.1.md](../metadados/dicionario_dados_v0.1.md))

---

## 2. O que coletar (e o que não criar)

Fonte: medições públicas já existentes de ping IPv4 (mesh de Anchors do RIPE Atlas, somente `GET`). Não criar medição própria e não gastar crédito.

Cada registro bruto guarda, quando a API trouxer:

| Campo | Unidade | Papel agora |
|---|---|---|
| `timestamp` | UTC | Ordenar o fluxo |
| `measurement_id` | — | Identidade da medição |
| `probe_id` | — | Origem |
| `dst_addr` | — | Destino |
| `fluxo_id` | texto estável | `probe_id\|dst_addr` |
| RTT da rajada (médio; mín/máx se existirem) | ms | Medição. Vazio se não houver resposta. **Nunca 0** |
| enviados, recebidos | contagem | `sent` e `rcvd` da rajada ICMP |
| `perda_pct` | % | `(enviados − recebidos) / enviados × 100` |
| `jitter_ms` | ms | Desvio-padrão dos RTT da rajada **somente** com 2 ou mais respostas. Senão, vazio. **Nunca 0 fingindo estabilidade** |
| `timeout_atual` | 0 ou 1 | 1 se não há RTT ou perda = 100% |
| país ou rota | texto | Só auditoria de diversidade. **Fora da futura árvore** |

Regras da coleta:

- [x] Vários fluxos, com pelo menos um caminho curto e um caminho longo no mesmo período
- [x] A diversidade geográfica está documentada e **não** virou classe
- [x] Dois blocos de tempo contíguos, sem amostra nos dois: Período A (só para o baseline da Tarefa 2) e Período B (medições que serão rotuladas). Referência do projeto: 7 dias + 7 dias a partir de 06/09/2026 04:32 UTC até 20/09/2026 04:32 UTC
- [x] Timeout permanece no arquivo (`timeout_atual = 1`, RTT vazio, nunca zero)
- [x] JSON bruto preservado; a tabela tratada não apaga o bruto
- [x] Parâmetros (período, probes, destinos) em `config/`, não espalhados no código ([config/coleta_config.json](../config/coleta_config.json))
- [x] HTTP com timeout, releitura em erro transitório e coleta idempotente (rodar de novo não duplica)
- [x] `requirements.txt` da coleta versionado na raiz do projeto

**Evidências (notebook, commit, trecho do config):**
- **Arquivo de Configuração Externa:** Parâmetros desacoplados em [`config/coleta_config.json`](../config/coleta_config.json):
  ```json
  "janelas_temporais": {
    "periodo_a_baseline": {
      "inicio_utc": "2026-09-06T04:32:00Z",
      "fim_utc": "2026-09-13T04:32:00Z",
      "duracao_dias": 7,
      "minimo_amostras_validas_exigido": 1500
    },
    "periodo_b_dataset": {
      "inicio_utc": "2026-09-13T04:32:00Z",
      "fim_utc": "2026-09-20T04:32:00Z",
      "duracao_dias": 7
    }
  }
  ```
- **Código de Ingestão e Idempotência:** Implementado em [`src/coleta_bruta.py`](../src/coleta_bruta.py), garantindo `timeout=120`, tratamento de HTTP 429/5xx com retry exponencial, gravação direta do JSON íntegro e normalização tabular sem substituição de nulos por 0.

---

## 3. Relatório de qualidade — ainda sem classe

- [x] Registros por `fluxo_id` calculados e auditados
- [x] Início e fim de cada fluxo delimitados estritamente dentro dos 14 dias (sem sobreposição entre A e B)
- [x] Campos ausentes tratados (RTT vazio é ausência `null`, jamais gravado como zero)
- [x] Duplicatas verificadas pela tupla `(fluxo_id, timestamp)`
- [x] Quantidade de timeouts preservada e sinalizada via `timeout_atual = 1`
- [x] RTT e perda descritos estatisticamente (mínimo, mediana, média, máximo) **sem** atribuir rótulos OK, RISCO ou FALHA

**Métricas Globais da Coleta:**
- **Nº de registros brutos:** 336.326 medições ICMP consolidadas.
- **Nº de fluxos:** 67 fluxos origem–destino (`probe_id|dst_addr`), cobrindo 22 probes e 21 IPs de destino.
  - *Fluxos elegíveis para baseline (≥ 1.500 amostras válidas no Período A):* 64 fluxos.
  - *Fluxos excluídos por insuficiência amostral:* 3 fluxos intra-Brasil para o destino `170.81.100.114` (sem RTT válido no Período A; excluídos rigorosamente sem inventar mediana).
- **Caminho curto e caminho longo presentes (quais):**
  - **Caminhos Curtos (Intra-país / Regional Próximo):**
    - `DE->DE`: mediana ~14 ms (normal baixo europeu).
    - `AR->AR`: mediana ~10 ms (normal baixo sul-americano).
    - `BR->BR`: mediana ~50 ms (normal típico continental brasileiro).
  - **Caminhos Regionais:**
    - `BR->UY`, `DE->PT`, `ES->PL`, `ZA->KE`, `IN->SG`, `BR->BO`: medianas entre 50 ms e 150 ms.
  - **Caminhos Longos (Intercontinentais / Transoceânicos Saudáveis):**
    - `BR->JP`: mediana ~277 ms (saudável, demonstrando que latência estrutural não é defeito).
    - `BR->IN`: mediana ~339 ms (saudável).
    - `BR->ZA`: mediana ~344 ms (saudável).
- **Tratamento de Timeouts e Jitter:**
  - Registros com perda total (`rcvd == 0`) retêm `latencia_ms = null` e `timeout_atual = 1`.
  - Jitter médio só calculado com 2 ou mais respostas; rajadas com 1 resposta preservadas com `jitter_ms = null`.

---

## 4. Scrum

- [x] Product Owner = Profa. Andréa Ono Sakai; Scrum Master da tarefa: Vinicius Firmino Souto; Equipe de Desenvolvimento
- [x] Board com To do / Doing / Done atualizado no repositório GitHub
- [x] Pelo menos 3 histórias: coletar fluxos diversos; preservar o bruto com timeout; separar Período A e Período B sem rotular

**Histórias de Usuário:**

1. **História 1 — Coleta e Diversidade Topológica de Fluxos:**  
   *Como* desenvolvedor do sistema preditor,  
   *quero* consumir medições públicas de ping IPv4 do mesh de Anchors do RIPE Atlas englobando caminhos curtos (ex: `DE->DE`, `BR->BR`) e caminhos longos (ex: `BR->JP`),  
   *para que* o conjunto de dados contenha a física de diferentes enlaces sem permitir que o algoritmo aprenda distância como defeito.  
   *Critérios de Aceitação:*  
   - Consumo exclusivo via HTTP `GET` sem custos de créditos da API pública.  
   - Mínimo de 1 caminho curto e 1 caminho longo no mesmo arquivo.  
   - Registro de metadados das sondas sem transformar dados geográficos em atributos de decisão.

2. **História 2 — Preservação Íntegra do Dado Bruto e Tratamento de Timeout:**  
   *Como* engenheiro de dados,  
   *quero* armazenar as respostas JSON originais e tabelas CSV na pasta `data/raw/` com distinção rigorosa de timeouts e cálculo condicional de jitter,  
   *para que* falhas de conectividade não sejam mascaradas como 0 ms e o histórico original permaneça auditável para as tarefas seguintes.  
   *Critérios de Aceitação:*  
   - Armazenamento em `data/raw/` sem sobrescrever arquivos brutos.  
   - Timeout registrado como `timeout_atual = 1` e `latencia_ms = null` (proibido preencher com 0).  
   - Jitter preenchido apenas quando `rcvd >= 2`, permanecendo nulo caso contrário.  
   - Nenhuma coluna de classe (OK/RISCO/FALHA) gerada nesta etapa.

3. **História 3 — Particionamento Temporal sem Contaminação e Configuração Centralizada:**  
   *Como* analista do projeto integrador,  
   *quero* parametrizar a coleta em arquivo `config/coleta_config.json` separando Período A (7 dias de baseline) e Período B (7 dias de medições),  
   *para que* a Tarefa 2 possa calcular a normalidade de cada fluxo sem sobreposição temporal com os dados que serão classificados.  
   *Critérios de Aceitação:*  
   - Período A (06/09 a 13/09/2026) e Período B (13/09 a 20/09/2026) rigorosamente contíguos e sem sobreposição.  
   - Parâmetros de API, rotas e janelas externalizados em `config/`.  
   - Script de ingestão idempotente que previne duplicação em execuções repetidas.

**Link do board:** [https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede/projects](https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede/projects)

---

## 5. Diário de bordo

| Integrante | O que fiz nesta tarefa | Dificuldades | O que pretendo manter/ajustar |
|---|---|---|---|
| **Vinicius Firmino Souto** (Scrum Master) | Condução das cerimônias Scrum, definição e priorização das 3 histórias no quadro Kanban, estruturação do diário da Tarefa 1 e curadoria dos pares de fluxos curtos (`BR->BR`, `DE->DE`) e longos (`BR->JP`, `BR->ZA`) no RFC. | Conciliar a visão de redes com o contrato de dados estático exigido para o aprendizado de máquina. | Manter a rotina de reuniões assíncronas e assegurar que a Tarefa 2 utilize estritamente o `data/raw/` gerado. |
| **Wendell Rodrigues Macedo** | Desenvolvimento do módulo de ingestão [`src/coleta_bruta.py`](../src/coleta_bruta.py), externalização dos parâmetros em [`config/coleta_config.json`](../config/coleta_config.json) e implementação de lógica de retries (HTTP 429/5xx) e timeout HTTP. | Tratar as variações de payload retornado pelo RIPE Atlas e garantir idempotência sem sobrescrita destrutiva. | Manter o desacoplamento de parâmetros em arquivos JSON/YAML e refinar o tratamento de exceções de rede. |
| **Fernando Paiva Coelho** | Criação do Dicionário de Dados v0.1 ([`metadados/dicionario_dados_v0.1.md`](../metadados/dicionario_dados_v0.1.md)) e do arquivo formal de metadados ([`metadados/ripe_atlas_metadata.json`](../metadados/ripe_atlas_metadata.json)), documentando cada tipo e regra de nulidade. | Mapear claramente por que colunas geográficas (`dst_addr`, `probe_id`) devem ser excluídas da árvore na modelagem. | Expandir o dicionário para a versão v0.2 na Tarefa 2, documentando as fórmulas do baseline e as features relativas. |
| **João Gustavo Sanches** | Implementação dos filtros de tratamento bruto no extrator de dados: preservação da flag `timeout_atual`, garantia de RTT vazio (sem 0) e cálculo condicional do jitter amostral apenas com `rcvd >= 2`. | Evitar a armadilha comum de preencher nulos com zero durante a normalização inicial com Pandas. | Automatizar testes unitários de integridade para validar que nenhum valor zerado espúrio entre no dataset. |
| **Daniel Dias Paranhos** | Elaboração do Relatório de Qualidade dos dados brutos: verificação de integridade temporal entre Período A e B, conferência de duplicatas `(fluxo_id, timestamp)` e auditoria dos 3 fluxos insuficientes. | Isolar estatísticas descritivas (mínimo, média, mediana) sem emitir qualquer juízo ou rótulo de classe (OK/RISCO/FALHA). | Desenvolver scripts de inspeção prévia para alimentar a seção de análise exploratória da Tarefa 2. |

---

## 6. Evidências gerais

- **RFC do Projeto:** [`RFC_Preditor_Degradacao_Rede.md`](../RFC_Preditor_Degradacao_Rede.md)
- **Dicionário de Dados v0.1:** [`metadados/dicionario_dados_v0.1.md`](../metadados/dicionario_dados_v0.1.md)
- **Metadados da Ingestão:** [`metadados/ripe_atlas_metadata.json`](../metadados/ripe_atlas_metadata.json)
- **Configuração da Coleta:** [`config/coleta_config.json`](../config/coleta_config.json)
- **Script de Coleta e Auditoria:** [`src/coleta_bruta.py`](../src/coleta_bruta.py)
- **Camada de Dados Brutos:** [`data/raw/`](../data/raw/) (com [`data/raw/README.md`](../data/raw/README.md))
- **Dependências de Ambiente:** [`requirements.txt`](../requirements.txt)
- **Repositório GitHub e Commits:** [https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede](https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede)

---

## Rubrica — Tarefa 1 (0 a 4,0)

| Critério | Peso | Nota máxima | Autoavaliação / Justificativa |
|---|---|---|---|
| Problema | 0,5 | 0,50 | Fluxo (`probe_id\|dst_addr`), unidade de análise e proibição formal de RTT absoluto como falha estão explicitados no diário e no RFC. |
| Coleta bruta | 1,5 | 1,50 | Diversidade contemplada com caminhos curtos e longos, timeout preservado (`timeout_atual = 1`), RTT nulo ≠ 0, jitter sem falso 0, parâmetros em `config/` e camada `data/raw/` intocável. |
| Período A e Período B sem rótulo | 1,0 | 1,00 | Blocos de 7 dias contíguos e não sobrepostos (06/09 a 13/09 e 13/09 a 20/09); relatório de qualidade descritivo estritamente **sem** classes. |
| Scrum + diário | 1,0 | 1,00 | Papéis definidos (PO, SM, Devs), 3 histórias de usuário com critérios de aceitação, link do repositório/board e diário de bordo com contribuições técnicas individualizadas para os 5 alunos. |
| **Total** | **4,0** | **4,00 / 4,00** | Entrega robusta, rastreável e aderente às diretrizes docentes. |
