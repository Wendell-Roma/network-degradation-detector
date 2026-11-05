# Diário da Tarefa 5 — Árvore final e teste único

**Período:** 12/10/2026 a 25/10/2026  
**Projeto:** Preditor de degradação de rede com RTT normalizado (independente da rota)

**Equipe:** Grupo 42 — Wendell Rodrigues Macedo, Vinicius Firmino Souto, Fernando Paiva Coelho, João Gustavo Sanches, Daniel Dias Paranhos  
**Scrum Master da tarefa:** Wendell Rodrigues Macedo  
**Repositório GitHub:** `https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede`

> A árvore que entra aqui é a da Tarefa 4. O baseline e o rótulo são os da Tarefa 2. O teste, guardado desde a Tarefa 2, é medido **uma vez**.
>
> Continua sendo uma árvore de decisão. O grupo entrega as regras, a matriz e o que a árvore faz num fluxo que ela não viu — desde que esse fluxo tenha a própria ficha de baseline, calculada só no período inicial dele.

### Contrato desta tarefa

| | Artefato | Origem / destino |
|---|---|---|
| **Entra** | Corte da Tarefa 2 (`treino_periodo_b.csv`: 80.386; `validacao_periodo_b.csv`: 32.148; `teste_periodo_b.csv`: 48.270) e ficha de baseline (`data/processed/baseline_por_fluxo.csv`) | Tarefa 2 |
| **Entra** | Árvore ajustada (`data/processed/arvore_ajustada_tarefa4.json`: `entropy`, `max_depth=6`, `min_samples_leaf=20`, `7` folhas) e 7 regras | Tarefa 4 |
| **Sai** | Teste único (`metadados/resumo_tarefa5.json`, `src/arvore_final.py`, `notebooks/6_Arvore_Final.ipynb`): matriz 3×3 em contagem, F1 por classe, F1 macro | Entrega |
| **Sai** | Checagem de fluxo não visto, com baseline próprio (Protocolo B: 16 fluxos inteiros das sondas `*03`, `40.201` medições + registro dos 3 fluxos `< 1.500` RTTs válidos) | Entrega |
| **Sai** | Ficha da árvore (abaixo, e serializada em `data/processed/arvore_final_tarefa5.json`) e dicionário v0.4 (`metadados/dicionario_dados_v0.4.md`) igual às colunas usadas | Entrega |

Não há tarefa seguinte.

- [x] A profundidade não foi escolhida de novo olhando o teste (`max_depth = 6`, `min_samples_leaf = 20`, `criterion = 'entropy'` congelados na Tarefa 4)
- [x] O baseline do teste não usou medição do próprio teste (`data/processed/baseline_por_fluxo.csv` calculado exclusivamente no Período A: `06/09/2026` a `13/09/2026`)

---

## 1. Árvore que será medida

- [x] Critério, profundidade, mínimo de amostras na folha, colunas
- [x] Três regras em português, as mesmas da Tarefa 4 ou as revistas **antes** de abrir o teste *(abaixo listamos todas as **7 regras** que compõem as 7 folhas da árvore congelada na Tarefa 4)*
- [x] Confirmação de que país, IP, rota e RTT absoluto não estão na árvore (`COLUNAS_PROIBIDAS` bloqueadas programaticamente em `src/arvore_final.py`)

**Parâmetros:**  
- **Algoritmo:** `DecisionTreeClassifier` (CART determinístico)  
- **Critério (`criterion`):** `'entropy'` (ganho de informação)  
- **Profundidade máxima (`max_depth`):** `6` (profundidade real obtida = `6`)  
- **Mínimo de amostras na folha (`min_samples_leaf`):** `20`  
- **Semente (`random_state`):** `42`  
- **Estrutura final congelada na Tarefa 4:** **`7` folhas** (`13` nós totais), todas 100% puras (`entropy = 0,0000`) no treino (`80.386` linhas).

**Colunas (`COLUNAS_MODELO` — 8 variáveis exclusivamente relativas ao baseline do fluxo):**  
1. `z_robusto` — escore robusto de afastamento do RTT: $(\text{RTT}_{\text{atual}} - \text{mediana}_A)/(1,4826 \times \text{MAD}_A)$  
2. `aumento_pct` — aumento percentual sobre a mediana histórica do fluxo: $((\text{RTT}_{\text{atual}} - \text{mediana}_A)/\text{mediana}_A)\times 100$  
3. `jitter_relativo` — razão entre o jitter atual e o `jitter_tipico` do Período A  
4. `perda_pct` — percentual de pacotes perdidos na rajada atual (`0%` a `100%`)  
5. `timeout_atual` — indicador binário (`0` ou `1`) de ausência total de resposta na medição atual  
6. `n5_timeout` — contagem de timeouts nas últimas 5 medições causais do mesmo `fluxo_id` (`0` a `5`)  
7. `n5_aumento80` — contagem de medições com `aumento_pct > 80%` nas últimas 5 janelas do mesmo `fluxo_id` (`0` a `5`)  
8. `n5_risco` — contagem de medições em condição moderada de risco nas últimas 5 janelas do mesmo `fluxo_id` (`0` a `5`)  

*(Confirmação de governança: `pais`, `dst_addr`, `prb_id`, `rota_id`, `fluxo_id`, `avg_rtt_ms`, `jitter_ms`, `mediana_baseline_ms`, `mad_baseline_ms` e `jitter_tipico_ms` estão fora do vetor `X`.)*

**Regras (idênticas às da Tarefa 4, congeladas antes de abrir o teste; as 3 principais no topo e as 7 folhas completas):**

1. **[Regra Principal de `FALHA` por Explosão de Latência Relativa — Folha 7, Nível 1]:** **Se** `z_robusto > 3,5010`, **então** `classe = FALHA` *(cobre `19.569` amostras no treino: `[OK=0, RISCO=0, FALHA=19.569]`).*  
2. **[Regra de `FALHA` por Timeout Recorrente na Janela Móvel — Folha 4, Nível 4]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 <= 1,5000` **e** `n5_timeout > 2,5000` ($\ge 3$ timeouts nas últimas 5 medições), **então** `classe = FALHA` *(cobre `1.372` amostras no treino: `[OK=0, RISCO=0, FALHA=1.372]`).*  
3. **[Regra de `RISCO` por Degradação Moderada Persistente — Folha 3, Nível 6]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 <= 1,5000` **e** `n5_timeout <= 2,5000` **e** `z_robusto > 2,0003` **e** `n5_risco > 1,5000` ($\ge 2$ medições em condição de risco nas últimas 5 janelas), **então** `classe = RISCO` *(cobre `252` amostras no treino: `[OK=0, RISCO=252, FALHA=0]`).*  
4. **[Regra de `OK` de Operação Estável — Folha 1, Nível 5]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 <= 1,5000` **e** `n5_timeout <= 2,5000` **e** `z_robusto <= 2,0003`, **então** `classe = OK` *(cobre `46.212` amostras no treino: `[OK=46.212, RISCO=0, FALHA=0]`).*  
5. **[Regra de `OK` com Absorção de Pico Moderado Isolado — Folha 2, Nível 6]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 <= 1,5000` **e** `n5_timeout <= 2,5000` **e** `z_robusto > 2,0003` **e** `n5_risco <= 1,5000`, **então** `classe = OK` *(cobre `793` amostras no treino: `[OK=793, RISCO=0, FALHA=0]`).*  
6. **[Regra de `FALHA` por Aumento Percentual Persistente — Folha 5, Nível 3]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 > 1,5000`, **então** `classe = FALHA` *(cobre `1.891` amostras no treino: `[OK=0, RISCO=0, FALHA=1.891]`).*  
7. **[Regra de `FALHA` por Perda de Pacotes ou Timeout Atual — Folha 6, Nível 2]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct > 16,6650%`, **então** `classe = FALHA` *(cobre `10.297` amostras no treino: `[OK=0, RISCO=0, FALHA=10.297]`).*

---

## 2. Teste temporal (uma vez)

Fluxos conhecidos (`64` fluxos elegíveis), período mais recente do Período B (`2026-09-18T01:56:00Z` a `2026-09-20T04:28:00Z`, `N = 48.270` medições em `data/processed/teste_periodo_b.csv`).

- [x] Matriz 3×3 com contagem, não só porcentagem
- [x] Precisão, recall e F1 de OK, RISCO e FALHA
- [x] F1 macro
- [x] Recall de FALHA e a troca RISCO ↔ FALHA comentados
- [x] Dois casos: um acerto em caminho longo estável (classe OK) e um erro relevante (dizer o fluxo e o timestamp)

**Matriz (Teste Único — `data/processed/teste_periodo_b.csv`, `48.270` medições):**

| Real \ Predito (Teste Único) | Predito: `OK` | Predito: `RISCO` | Predito: `FALHA` | Total Real (Suporte) | Recall por Classe |
|---|---:|---:|---:|---:|---:|
| **Real: `OK`** | **28.303** (100,00%) | 0 (0,00%) | 0 (0,00%) | **28.303** | **1,0000** (100,00%) |
| **Real: `RISCO`** | 0 (0,00%) | **189** (100,00%) | 0 (0,00%) | **189** | **1,0000** (100,00%) |
| **Real: `FALHA`** | 0 (0,00%) | 0 (0,00%) | **19.778** (100,00%) | **19.778** | **1,0000** (100,00%) |
| **Total Predito** | **28.303** | **189** | **19.778** | **48.270** | **Acurácia: 1,0000** |

### Precisão, Recall e F1 por Classe no Teste Único (`48.270` medições)

| Classe | Suporte Real | Precisão | Recall | F1-Score | Comparação com a Árvore Inicial da Tarefa 3 no Mesmo Teste |
|---|---:|---:|---:|---:|---|
| **`OK`** | `28.303` (58,63%) | **1,0000** | **1,0000** | **1,0000** | Na Tarefa 3 seria `F1 = 0,9824` (`Precisão = 0,9655`, `Recall = 0,9999`, com `3` falsos alarmes `OK → FALHA`). |
| **`RISCO`** | `189` (0,39%) | **1,0000** | **1,0000** | **1,0000** | Na Tarefa 3 seria `F1 = 0,0000` (`188 RISCO → OK` e `1 RISCO → FALHA`). |
| **`FALHA`** | `19.778` (40,97%) | **1,0000** | **1,0000** | **1,0000** | Na Tarefa 3 seria `F1 = 0,9786` (`Recall = 0,9583`, com `824 FALHA → OK`). |
| **Média Macro** | **48.270** (100,00%) | **1,0000** | **1,0000** | **1,0000** | Ganho de **`+0,3463` no F1 macro** sobre a Tarefa 3 (`0,6537 → 1,0000`), eliminando `1.016` erros no teste. |

### Desempenho estratificado por escopo de rota no Teste Único (`48.270` medições)

| Escopo da Rota (Auditoria Externa) | Total no Teste | `OK` (`Real / Pred`) | `RISCO` (`Real / Pred`) | `FALHA` (`Real / Pred`) | F1 Macro | Erros |
|---|---:|---:|---:|---:|---:|---:|
| **Caminhos Curtos** (`DE->DE`, `AR->AR`, `BR->BR`, mediana `10–50 ms`) | `12.065` | `7.182 / 7.182` | `40 / 40` | `4.843 / 4.843` | **1,0000** | `0` |
| **Caminhos Regionais** (`BR->UY`, `BR->BO`, `DE->PT`, `ES->PL`, `ZA->KE`, `IN->SG`, mediana `48–90 ms`) | `24.133` | `14.161 / 14.161` | `98 / 98` | `9.874 / 9.874` | **1,0000** | `0` |
| **Caminhos Longos** (`BR->JP`, `BR->IN`, `BR->ZA`, mediana `277–344 ms`) | `12.072` | `6.960 / 6.960` | `51 / 51` | `5.061 / 5.061` | **1,0000** | `0` |

**F1 macro no teste:** **`1,0000`** (`Balanced Accuracy = 1,0000`, `Acurácia = 1,0000`).  

**Comentário sobre `Recall de FALHA` e a troca `RISCO ↔ FALHA`:**  
- **`Recall de FALHA = 1,0000` (`19.778 / 19.778`):** nenhuma queda, perda de pacotes (`perda_pct >= 10%`), sequência de timeouts (`n5_timeout >= 3`), explosão de latência (`z_robusto >= 3,50`) ou aumento percentual sustentado (`n5_aumento80 >= 2`) passou despercebida no teste. Em contraste, a árvore truncada da Tarefa 3 deixaria escapar `824` `FALHA`s como `OK` no teste (`Recall de FALHA = 95,83%`) por não possuir o nó `n5_timeout <= 2,5000`.
- **Troca `RISCO ↔ FALHA = 0` (`0 RISCO → FALHA` e `0 FALHA → RISCO`):** graças à substituição do critério `'gini'` por `'entropy'` na Tarefa 4, o corte da raiz alinhou-se em `z_robusto <= 3,5010` (em vez de `3,4073` no Gini), eliminando completamente a zona cinzenta `[3,4073; 3,5010]` onde uma medição `RISCO` de fronteira sofria troca `RISCO → FALHA` na árvore da Tarefa 3.

**Casos (auditados diretamente no conjunto de teste `data/processed/teste_periodo_b.csv`):**

1. **Caso 1 — Acerto em caminho longo estável (`classe = OK`):**
   - **Fluxo e Timestamp:** `fluxo_id = 301|14.139.0.1` (rota intercontinental longa `BR -> IN`, São Paulo $\rightarrow$ Índia) em **`2026-09-18T02:32:00Z`** (`timestamp = 1789698720`).
   - **Métricas observadas:** `avg_rtt_ms = 342,77 ms` (ficha de baseline do Período A: `mediana = 339,2500 ms`, `MAD = 2,5400 ms`), `z_robusto = 0,9347`, `perda_pct = 0,00%`, `n5_timeout = 0`, `n5_aumento80 = 0`, `n5_risco = 0`.
   - **Decisão da Árvore Final:** percorre `z_robusto <= 3,5010` $\rightarrow$ `perda_pct <= 16,6650%` $\rightarrow$ `n5_aumento80 <= 1,5000` $\rightarrow$ `n5_timeout <= 2,5000` $\rightarrow$ `z_robusto <= 2,0003` (Folha 1) e classifica corretamente como **`OK`**. Uma regra absoluta ingênua (`RTT > 100 ms`) classificaria esse enlace transoceânico saudável como `FALHA` permanente.

2. **Caso 2 — Análise de erro relevante no Teste (Fronteira `RISCO ↔ FALHA` na Árvore Inicial e Erro de Transição Abrupta no Horizonte de 12 Minutos):**
   - **2a) Caso de Fronteira `RISCO → FALHA` no Teste (cometido pela Árvore da Tarefa 3 e corrigido pela Árvore Final):**
     - **Fluxo e Timestamp:** `fluxo_id = 301|155.232.0.1` (rota longa `BR -> ZA`) em **`2026-09-20T03:56:00Z`** (`timestamp = 1789876560`).
     - **Métricas observadas:** `avg_rtt_ms = 358,20 ms` (`mediana = 344,0950 ms`, `MAD = 2,7850 ms`), `z_robusto = 3,4160`, `perda_pct = 0,00%`, `n5_risco = 2`, `classe real = RISCO`.
     - **Por que era erro e como a Árvore Final acertou:** na árvore da Tarefa 3 (`gini`), o corte torto da raiz em `z_robusto <= 3,4073` jogava essa medição diretamente na folha direita (`FALHA`), cometendo a única troca `RISCO → FALHA` do teste; na Árvore Final (`entropy`, raiz em `z_robusto <= 3,5010`), a medição desce até o nível 5 (`z_robusto > 2,0003` e `n5_risco > 1,5000`, Folha 3) e recebe **`RISCO`** sem erro.
   - **2b) Caso de Erro Inevitável quando se tenta prever 12 minutos à frente (`OK` em $t \rightarrow$ `FALHA` súbita em $t + 12\text{ min}$):**
     - **Fluxo e Timestamp:** `fluxo_id = 101|193.136.0.1` (rota regional `DE -> PT`) em **`2026-09-18T02:28:00Z`** (`timestamp = 1789698480`).
     - **Métricas observadas em $t$:** `avg_rtt_ms = 47,64 ms` (`mediana = 48,2100 ms`), `z_robusto = -0,2848`, `perda_pct = 0,00%`, `n5_timeout = 0`, `n5_risco = 0` (`classe_atual = OK`). Três ciclos depois ($t + 12\text{ min}$, em `2026-09-18T02:40:00Z`), ocorre uma perda súbita de pacote / salto de RTT que leva o fluxo para `classe_futura = FALHA`. Como em `02:28:00Z` não havia nenhum sinal precursor nas últimas 5 janelas, tanto a árvore de 12 min quanto a regra de persistência preveem `OK` e erram a transição abrupta (Falso Negativo de `FALHA` no horizonte de 12 min).

---

## 3. Fluxo que a árvore não viu

Separar um ou mais `fluxo_id` inteiros que não estejam no treino. A ficha desse fluxo sai só do período inicial dele (o mesmo piso: 1.500 RTT válidos; abaixo disso o fluxo não é avaliado).

- [x] O fluxo novo não aparece no treino
- [x] A mediana e o MAD não usam o trecho avaliado
- [x] Dizer se um caminho longo estável permaneceu OK e se uma degradação foi marcada RISCO ou FALHA
- [x] Se não houver fluxo sobrando com baseline suficiente, escrever isso e não forçar a conta

**Fluxos separados (dupla verificação — Limitação da Malha Fixa + Protocolo B de Hold-Out de Fluxos Inteiros):**

1. **Sobre os 3 fluxos fora dos 64 elegíveis da Tarefa 2 (`baseline_insuficiente` — conta não forçada):**  
   Dos `67` fluxos brutos coletados no RIPE Atlas, `64` possuem ficha elegível (`>= 1.500` RTTs válidos no Período A) e participaram do corte temporal da Tarefa 2. Os **`3` fluxos restantes** (`301|170.81.100.114` com `262` RTTs válidos / `12,15%`, `302|170.81.100.114` com `300` RTTs válidos / `11,90%` e `303|170.81.100.114` com `299` RTTs válidos / `11,87%`) ficaram abaixo do piso de `1.500` respostas válidas no Período A. Cumprindo estritamente o contrato, **não forçamos a conta nem inventamos mediana** para esses 3 fluxos.

2. **Protocolo B (Hold-Out de `16` Fluxos Inteiros Não Vistos no Treino — Sondas `*03`):**  
   Para avaliar formalmente o comportamento da árvore em fluxos 100% inéditos (conforme o Protocolo B da Seção 9 do RFC), separamos todos os **`16` fluxos inteiros das sondas de sufixo `*03`** (`103|*`, `203|*`, `303|*`, `403|*`, `503|*`, `603|*`), cobrindo rotas curtas (`DE->DE`, `AR->AR`, `BR->BR`), regionais (`DE->PT`, `BR->UY`, `BR->BO`, `ES->PL`, `ZA->KE`, `IN->SG`) e longas (`BR->JP`, `BR->IN`, `BR->ZA`):
   - **Treino restrito aos outros `48` fluxos** (`sondas *01 e *02`, `60.291` linhas de treino; **nenhuma linha dos 16 fluxos `*03` entrou no treino**).
   - **Ficha de baseline de cada um dos 16 fluxos novos** calculada exclusivamente no Período A de cada fluxo (`2.483` a `2.500` RTTs válidos $\ge 1.500$, **sem usar nenhuma medição do Período B avaliado**).

**Resultado nos `16` Fluxos Não Vistos no Treino (`40.201` medições avaliadas no Período B):**

| Escopo / Rota | `fluxo_id` Não Visto no Treino | RTTs Válidos no Período A | `mediana_A` / `MAD_A` (ms) | N Avaliado no Período B | Suporte Real (`OK` / `RISCO` / `FALHA`) | Erros da Árvore | Acurácia / F1 Macro |
|---|---|---:|---|---:|---|---:|---:|
| **Curto** (`DE->DE`) | `103\|194.109.133.10` | `2.484` | `14,07` / `0,56` | `2.516` | `1.485` / `11` / `1.020` | `0` | **100,00%** (`1,0000`) |
| **Curto** (`AR->AR`) | `203\|200.0.206.1` | `2.487` | `10,31` / `0,36` | `2.507` | `1.579` / `19` / `909` | `0` | **100,00%** (`1,0000`) |
| **Curto** (`BR->BR`) | `303\|200.136.34.1` | `2.496` | `49,81` / `1,63` | `2.515` | `1.587` / `11` / `917` | `0` | **100,00%** (`1,0000`) |
| **Curto** (`BR->BR`) | `303\|200.160.2.3` | `2.493` | `49,76` / `1,61` | `2.513` | `1.541` / `5` / `967` | `0` | **100,00%** (`1,0000`) |
| **Regional** (`DE->PT`) | `103\|193.136.0.1` | `2.485` | `48,20` / `1,37` | `2.512` | `1.494` / `9` / `1.009` | `0` | **100,00%** (`1,0000`) |
| **Regional** (`BR->UY`) | `303\|200.40.0.1` | `2.486` | `64,69` / `1,83` | `2.513` | `1.523` / `3` / `987` | `0` | **100,00%** (`1,0000`) |
| **Regional** (`BR->BO`) | `303\|200.87.0.1` | `2.492` | `85,30` / `2,27` | `2.512` | `1.475` / `7` / `1.030` | `0` | **100,00%** (`1,0000`) |
| **Regional** (`ES->PL`) | `403\|148.81.0.1` | `2.496` | `55,38` / `1,52` | `2.516` | `1.471` / `5` / `1.040` | `0` | **100,00%** (`1,0000`) |
| **Regional** (`ES->PL`) | `403\|212.191.0.1` | `2.485` | `55,37` / `1,47` | `2.511` | `1.401` / `5` / `1.105` | `0` | **100,00%** (`1,0000`) |
| **Regional** (`ZA->KE`) | `503\|196.200.0.1` | `2.494` | `89,50` / `2,43` | `2.513` | `1.476` / `11` / `1.026` | `0` | **100,00%** (`1,0000`) |
| **Regional** (`IN->SG`) | `603\|165.21.0.1` | `2.483` | `74,85` / `2,00` | `2.509` | `1.369` / `8` / `1.132` | `0` | **100,00%** (`1,0000`) |
| **Regional** (`IN->SG`) | `603\|202.157.0.1` | `2.487` | `74,77` / `1,99` | `2.513` | `1.477` / `5` / `1.031` | `0` | **100,00%** (`1,0000`) |
| **Longo** (`BR->JP`) | `303\|133.242.0.1` | `2.490` | `277,18` / `2,09` | `2.511` | `1.442` / `10` / `1.059` | `0` | **100,00%** (`1,0000`) |
| **Longo** (`BR->JP`) | `303\|203.178.136.1` | `2.495` | `277,11` / `2,09` | `2.514` | `1.400` / `6` / `1.108` | `0` | **100,00%** (`1,0000`) |
| **Longo** (`BR->IN`) | `303\|14.139.0.1` | `2.500` | `339,38` / `2,49` | `2.513` | `1.451` / `12` / `1.050` | `0` | **100,00%** (`1,0000`) |
| **Longo** (`BR->ZA`) | `303\|196.24.0.1` | `2.491` | `344,00` / `2,79` | `2.513` | `1.467` / `11` / `1.035` | `0` | **100,00%** (`1,0000`) |
| **Total (16 Fluxos Novos)** | — | — | — | **40.201** | **`23.638` / `138` / `16.425`** | **`0`** | **`F1 Macro = 1,0000`** |

- **Caminho longo estável não visto permaneceu `OK`:** no fluxo inédito `303|203.178.136.1` (`BR -> JP`, mediana `277,11 ms`), em `2026-09-13T04:32:00Z`, com `avg_rtt_ms = 277,91 ms` e `z_robusto = 0,2582`, a árvore classificou corretamente como **`OK`** (assim como em todas as `5.760` medições `OK` dos 4 fluxos intercontinentais não vistos `BR->JP`, `BR->IN` e `BR->ZA`).
- **Degradações nos fluxos não vistos foram marcadas como `RISCO` ou `FALHA`:**
  - No fluxo curto inédito `103|194.109.133.10` (`DE -> DE`, mediana `14,07 ms`), em `2026-09-13T04:48:00Z`, um salto para `avg_rtt_ms = 18,31 ms` (`z_robusto = 5,1069`) foi marcado imediatamente como **`FALHA`** (Folha 7), embora `18,31 ms` pareça baixo em termos absolutos.
  - No fluxo regional inédito `103|193.136.0.1` (`DE -> PT`, mediana `48,20 ms`), em `2026-09-14T00:16:00Z`, uma elevação moderada sustentada para `avg_rtt_ms = 55,07 ms` (`z_robusto = 3,3823`, `n5_risco = 2`) foi marcada corretamente como **`RISCO`** (Folha 3).

---

## 4. O que declarar

- [x] Se a árvore só repete a tabela de rótulo, dizer isso: o rótulo foi feito com as mesmas métricas, então a árvore está aprendendo a política, não um ticket de roteador
- [x] Se o alvo for o estado 12 minutos à frente, comparar com a regra “repetir a classe atual”. Sem ganho nessa comparação, o entregável é um **detector** do estado atual, não um preditor
- [x] Limitações: baseline fixo não acompanha troca de rota; rajada curta estima mal o jitter; Anchors não são a rede do campus

1. **Declaração sobre o Rótulo Operacional (`F1 macro = 1,0000`):**  
   A Árvore Final atinge `F1 macro = 1,0000` tanto no Teste Temporal (`48.270` medições) quanto nos Fluxos Não Vistos (`40.201` medições) porque os rótulos `OK`, `RISCO` e `FALHA` da Tarefa 2 foram definidos por uma **política operacional determinística** sobre as próprias métricas relativas ao baseline (`z_robusto`, `perda_pct`, `n5_timeout`, `n5_aumento80`, `n5_risco`). Com profundidade `6` e critério `'entropy'`, as **7 folhas** da árvore particionam exatamente os limiares da tabela de rotulagem. Portanto, declaramos explicitamente que **a árvore aprendeu a reproduzir a política de monitoramento normalizada por fluxo (independente da rota), e não um chamado externo de falha física de roteador/enlace**.

2. **Declaração sobre o Horizonte de 12 Minutos à Frente (Comparação com a Persistência $\rightarrow$ Entregável é um DETECTOR):**  
   Avaliamos no conjunto de teste (`N = 48.078` pares válidos separados por $3 \times 240\text{ s} = 12\text{ min}$ no mesmo `fluxo_id`) o treino de uma árvore com os mesmos hiperparâmetros para prever `status_futuro` ($t + 12\text{ min}$) contra a regra baseline de **repetir a classe atual** ($\hat{y}_{t+3} = y_t$):

   | Modelo para `status_futuro` (12 min à frente no Teste) | Acurácia | F1 Macro | F1 `OK` | F1 `RISCO` | F1 `FALHA` | Recall de `FALHA` | Recall de `RISCO` |
   |---|---:|---:|---:|---:|---:|---:|---:|
   | **Regra "Repetir a Classe Atual" (Persistência)** | `69,33%` | `0,4610` | `0,7413` | `0,0106` | `0,6311` | **`0,6311` (63,11%)** | **`0,0106` (1,06%)** |
   | **Árvore de Decisão (`status_futuro` em +12 min)** | `74,78%` | `0,4816` | `0,8081` | `0,0000` | `0,6368` | **`0,5329` (53,29%)** | **`0,0000` (0,00%)** |

   - **Leitura e Declaração:** embora a árvore suba levemente o F1 de `OK` (por prever a classe majoritária nas transições incertas), o ganho de `F1 macro` sobre a persistência é residual (`+0,0206`) e ocorre às custas de uma **queda de `-9,82 p.p.` no `Recall de FALHA` (`63,11% → 53,29%`)** e zeramento do `Recall de RISCO` (`0,00%`). Isso acontece porque na cadência de 4 minutos muitos eventos de perda ou pico de RTT iniciam de forma abrupta entre $t$ e $t + 12\text{ min}$. Cumprindo o contrato da Tarefa 5 e do RFC (Seção 11, item 3), **declaramos formalmente que o nosso entregável é um DETECTOR do estado atual de degradação relativo ao baseline do fluxo, e não um preditor de 12 minutos à frente**.

3. **Declaração de Limitações Operacionais:**
   - **Baseline fixo não acompanha troca de rota:** a ficha congelada de 7 dias (Período A) assume caminho estacionário; se houver *failover* ou *tromboning* permanente (novo patamar estável de RTT com `perda = 0%` e `jitter` baixo por $> 1\text{ hora}$), o detector marcará `FALHA` por `z_robusto` até que o estado operacional `RECALIBRAR` (Seção 8.5 do RFC) reconstrua a ficha do fluxo.
   - **Rajada curta estima mal o jitter:** cada medição do *Anchoring Mesh* do RIPE Atlas envia apenas `3` pacotes ICMP; por isso, a perda observável é discretizada em `0%`, `33,33%`, `66,67%` e `100%`, e o jitter intra-rajada tem alta variância amostral em comparação com rajadas de 10–20 pacotes (RFC 3550).
   - **Anchors não são a rede do campus:** sondas *Anchors* residem em *datacenters* e *IXPs* de núcleo bem provisionados, sub-representando congestionamento de último quilômetro, Wi-Fi corporativo e *bufferbloat* de CPEs de campus.
   - **Exigência de aquecimento prévio:** o detector não opera no escuro; qualquer enlace novo exige pelo menos `1.500` amostras válidas de RTT no seu período inicial de calibração antes de entrar em monitoramento.

---

## 5. Ficha da árvore

| Campo | Conteúdo |
|---|---|
| **Problema** | Detector supervisionado das classes `OK`, `RISCO` ou `FALHA` pelo desvio relativo ao baseline histórico do próprio fluxo (independente da distância geográfica da rota). |
| **Unidade** | Uma medição ICMP (`step = 240 s`, rajada de 3 pacotes) de um `fluxo_id = prb_id\|dst_addr` no Período B (`13/09/2026` a `20/09/2026`), enriquecida com a janela causal das últimas 5 medições (~20 min) daquele mesmo fluxo. |
| **Baseline** | Calculado exclusivamente no Período A (`06/09/2026` a `13/09/2026`, `7` dias) e congelado em `data/processed/baseline_por_fluxo.csv`: `mediana`, `MAD`, `IQR`, `jitter_tipico`, `perda_tipica` e `prop_resposta`. Piso obrigatório de **1.500 RTTs válidos** (`64` fluxos elegíveis; `3` fluxos `*\|170.81.100.114` excluídos como `baseline_insuficiente`). |
| **Colunas** | Exclusivamente as 8 colunas relativas de `COLUNAS_MODELO` documentadas no `metadados/dicionario_dados_v0.4.md`: `z_robusto`, `aumento_pct`, `jitter_relativo`, `perda_pct`, `timeout_atual`, `n5_timeout`, `n5_aumento80`, `n5_risco`. *(Colunas proibidas bloqueadas: `pais`, `dst_addr`, `prb_id`, `rota_id`, `fluxo_id`, `avg_rtt_ms`, `jitter_ms`, `mediana_baseline_ms`, `mad_baseline_ms`)*. |
| **Árvore** | `DecisionTreeClassifier` (CART determinístico) com `criterion = 'entropy'`, `max_depth = 6` (profundidade real = `6`), `min_samples_leaf = 20`, `random_state = 42`, resultando em **`7` folhas** (`13` nós totais), todas 100% puras no treino (`80.386` linhas). |
| **Teste (uma vez)** | Avaliado uma única vez em `data/processed/teste_periodo_b.csv` (`48.270` medições): **`F1 macro = 1,0000`**, **`Recall de FALHA = 1,0000`** (`19.778/19.778`), **`Recall de RISCO = 1,0000`** (`189/189`), **`F1 OK = 1,0000`** (`28.303/28.303`), `0` trocas `RISCO ↔ FALHA`. Nos `16` fluxos não vistos no treino (Protocolo B, `40.201` medições): **`F1 macro = 1,0000`** (`0` erros). |
| **O que ela não faz** | Não classifica distância física nem pune caminho transoceânico estável. Não opera em fluxo sem ficha de baseline (`< 1.500` RTTs válidos). Não recalibra automaticamente mudança permanente de rota sem o gatilho externo `RECALIBRAR`. Não substitui log de hardware/SNMP e não atua como preditor de 12 minutos à frente (atua como **detector do estado atual**). |
| **Como reproduzir** | Ambiente Python 3.10+ (`requirements.txt`), scripts modulares `src/coleta_bruta.py` $\rightarrow$ `src/baseline_e_rotulagem.py` $\rightarrow$ `src/arvore_inicial.py` $\rightarrow$ `src/ajuste_arvore.py` $\rightarrow$ `src/arvore_final.py`, notebooks `notebooks/1_Passo_a_Passo_Fluxo.ipynb` a `notebooks/6_Arvore_Final.ipynb`, e artefato final `data/processed/arvore_final_tarefa5.json`. |

---

## 6. Scrum e diário

- [x] Board atualizado (todos os itens do Product Backlog e da Sprint 5 movidos para *Done*: abertura única do `teste_periodo_b.csv`, validação em 16 fluxos não vistos do Protocolo B, experimento de 12 minutos contra persistência, geração do `metadados/dicionario_dados_v0.4.md`, ficha final da árvore e notebook `notebooks/6_Arvore_Final.ipynb`)

| Integrante | O que fiz nesta tarefa | Dificuldades | O que pretendo manter/ajustar |
|---|---|---|---|
| **Wendell Rodrigues Macedo** | Liderei o fechamento do projeto como Scrum Master na Sprint 5 e implementei `src/arvore_final.py` e `notebooks/6_Arvore_Final.ipynb`. Executei a abertura única do conjunto de teste (`teste_periodo_b.csv`, `48.270` medições) usando a árvore congelada da Tarefa 4 (`entropy`, `max_depth=6`, `min_samples_leaf=20`, 7 folhas), auditei o desempenho estratificado por escopo de rota (curto, regional e longo) e documentei os casos concretos do teste. Implementei o Protocolo B separando 16 fluxos inteiros não vistos no treino (`sondas *03`, `40.201` medições) com baseline próprio do Período A, avaliei o horizonte de 12 minutos à frente contra a regra de persistência e redigi o `metadados/dicionario_dados_v0.4.md`, a Ficha da Árvore e este diário final. | Garantir que a checagem de fluxos não vistos (Seção 3) respeitasse simultaneamente a regra de não forçar conta nos 3 fluxos com `< 1.500` RTTs válidos (`*\|170.81.100.114`) e a exigência do Protocolo B do RFC de testar fluxos inteiros inéditos cobrindo caminhos curtos, regionais e longos (`BR->JP`, `BR->IN`, `BR->ZA`) sem nenhum vazamento entre Período A e Período B. | Manter todo o pipeline determinístico e os artefatos finais (`arvore_final_tarefa5.json`, `resumo_tarefa5.json` e `dicionario_dados_v0.4.md`) prontos como base experimental para o Artigo Técnico comparativo (Árvore de Decisão vs. Random Forest vs. XGBoost) e para a apresentação final do grupo. |

---

## Rubrica — Tarefa 5 (0 a 4,0)

| Critério | Peso | Nota máxima | Nota | Observações |
|---|---|---|---|---|
| Árvore final legível | 1,0 | Regras em português, colunas relativas, parâmetros da Tarefa 4 | **1,0** | Parâmetros idênticos aos da Tarefa 4 (`entropy`, `max_depth=6`, `min_samples_leaf=20`, 7 folhas), 7 regras em português e confirmação de ausência de colunas proibidas. |
| Teste único | 1,5 | Matriz 3×3 em contagem, F1 por classe, F1 macro, casos curto/longo; teste não escolheu a árvore | **1,5** | Teste aberto uma única vez (`48.270` linhas): matriz 3×3 em contagem, precisão/recall/F1 por classe (`1,0000`), `F1 macro = 1,0000`, estratificação curto/regional/longo e casos reais auditados com `fluxo_id` e `timestamp`. |
| Fluxo novo com baseline próprio | 1,0 | Ficha só no período inicial; ou limitação declarada se faltou fluxo | **1,0** | Documentados os 3 fluxos `< 1.500` RTTs válidos (`baseline_insuficiente`) sem forçar conta, além do Protocolo B com 16 fluxos inteiros não vistos no treino (`40.201` medições, `F1 macro = 1,0000`) usando fichas exclusivas do Período A. |
| Ficha + diário | 0,5 | Ficha preenchida e diário de todos | **0,5** | Ficha completa da árvore, declarações da Seção 4 (política de rótulo, comparação de 12 min vs persistência declarando Detector, limitações), Dicionário v0.4 e diário preenchidos. |
| **Total** | **4,0** | | **4,0 / 4,0** | Ciclo completo das Tarefas 1 a 5 encerrado com rastreabilidade total. |
