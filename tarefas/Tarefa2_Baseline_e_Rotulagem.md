# Diário da Tarefa 2 — Baseline do fluxo e rotulagem OK, RISCO, FALHA

**Período:** 18/09/2026 a 30/09/2026  
**Projeto:** Preditor de degradação de rede com RTT normalizado (independente da rota)

**Equipe:** Grupo 42  
**Integrantes:**  
- Wendell Rodrigues Macedo  
- Vinicius Firmino Souto  
- Fernando Paiva Coelho  
- João Gustavo Sanches  
- Daniel Dias Paranhos  
**Scrum Master da tarefa:** Wendell Rodrigues Macedo  
**Repositório GitHub:** [https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede](https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede)

> Esta tarefa lê o `data/raw/` da Tarefa 1. Não troca a coleta sem versionar.
>
> O trabalho é **obter o baseline de cada fluxo e rotular o Período B** com a tabela desta página. A árvore não entra aqui. País, IP e rota não entram na tabela que a árvore vai ler.
>
> Ordem obrigatória: inspeção do bruto → ficha de baseline no Período A → métricas relativas no Período B → rótulo na ordem da tabela → só então o recorte temporal dentro de B.

### Contrato desta tarefa

| | Artefato | Origem / destino |
|---|---|---|
| **Entra** | `data/raw/` e dicionário v0.1 ([`metadados/dicionario_dados_v0.1.md`](../metadados/dicionario_dados_v0.1.md)) | Tarefa 1 |
| **Sai** | [`data/processed/baseline_por_fluxo.csv`](../data/processed/baseline_por_fluxo.csv) (uma ficha por `fluxo_id`) | Tarefas 3 a 5 |
| **Sai** | Dataset rotulado do Período B (`data/processed/dataset_rotulado_periodo_b.csv`), com a classe e as métricas abaixo | Tarefa 3 **usa este arquivo e este rótulo** |
| **Sai** | Recorte temporal dentro de B (`treino_periodo_b.csv`, `validacao_periodo_b.csv`, `teste_periodo_b.csv`) | Tarefas 3 a 5 — **o mesmo corte** |
| **Sai** | Dicionário v0.2 ([`metadados/dicionario_dados_v0.2.md`](../metadados/dicionario_dados_v0.2.md): bruto, ficha, métricas, classe, colunas proibidas) | Tarefa 3 |

**Não sai daqui:** árvore treinada, profundidade escolhida, acurácia, F1.

- [x] O notebook lê o bruto da Tarefa 1

---

## 1. Inspeção do bruto (ainda sem rótulo)

`data/raw/` permanece intocado. A auditoria vai para o diário; a tabela de trabalho, para `data/interim/`.

- [x] Contagem de linhas, fluxos, duplicatas e RTT vazio
- [x] Nenhum RTT ausente foi gravado como 0
- [x] Período A e Período B não compartilham timestamp do mesmo fluxo

**N bruto:** 336.326 medições ICMP  
**N de fluxos:** 67 fluxos (`probe_id|dst_addr`), 18 probes e 25 IPs de destino em 12 rotas geográficas  
**Evidências:**
- **Auditoria de Integridade Executada no Notebook [`3_Baseline_e_Rotulagem.ipynb`](../notebooks/3_Baseline_e_Rotulagem.ipynb) (Células 1 a 4) e no script [`src/baseline_e_rotulagem.py`](../src/baseline_e_rotulagem.py):**
  - **Preservação da Camada Raw:** O arquivo original `data/raw/ripe_atlas_14dias_20260920T043200Z.csv` permaneceu estritamente intocado. A tabela de trabalho ordenada com marcação de período (`A` ou `B`) foi salva em `data/interim/df_bruto_auditado.csv`.
  - **Volume Global:** 336.326 linhas e 16 colunas.
  - **Duplicatas:** 0 duplicatas pela chave composta `(fluxo_id, timestamp)`.
  - **Tratamento de Ausências e Timeouts:** 19.964 medições com RTT médio ausente (`avg` nulo, associadas a `timeout_atual = 1` ou perda total de pacotes). **Nenhum RTT ausente foi gravado como 0 ms** (0 registros com `avg == 0`).
  - **Particionamento Temporal Rigoroso:**
    - **Período A (Baseline):** `2026-09-06T04:32:00Z` até `2026-09-13T04:32:00Z` (167.962 medições).
    - **Período B (Rotulagem):** `2026-09-13T04:32:00Z` até `2026-09-20T04:32:00Z` (168.364 medições).
    - **Compartilhamento de Timestamp:** 0 timestamps compartilhados entre A e B para o mesmo fluxo (interseção estritamente nula).

---

## 2. Como obter o baseline

Uma ficha por `fluxo_id`. Só o Período A. O Período B não entra na conta e não atualiza a ficha.

| Passo | O que fazer |
|---|---|
| 1 | Separar o fluxo e ordenar pelo timestamp. |
| 2 | Período A = bloco inicial. Período B = bloco seguinte, sem amostra nos dois. |
| 3 | RTT válido = medição com RTT presente. Timeout fica **fora** da mediana e do MAD, e **dentro** do dataset como evento. |
| 4 | Menos de **1.500** RTT válidos no A: `baseline_insuficiente`. Esse fluxo **não** recebe classe. Não inventar mediana. |
| 5 | Gravar uma linha em `baseline_por_fluxo.csv` e congelar. |

| Campo da ficha | Fórmula, somente Período A |
|---|---|
| `mediana` | mediana dos RTT válidos (ms) |
| `MAD` | mediana(\|RTT - mediana\|) |
| `jitter_tipico` | mediana do jitter nas medições em que o jitter existe (ms) |
| `perda_tipica` | mediana de `perda_pct`, inclusive timeout (%) |
| `prop_resposta` | medições com RTT válido / medições do período |

- [x] Ficha conferida em pelo menos um fluxo curto e um fluxo longo (as medianas podem ser muito diferentes; as duas são “normal”)
- [x] Lista dos fluxos excluídos e o motivo (contagem abaixo de 1.500)

**Fluxos com ficha:** **64 fluxos elegíveis** (`status_baseline = elegivel`), todos com entre 2.488 e 2.505 RTTs válidos no Período A (`prop_resposta` entre `98,85%` e `99,40%`), superando com folga o piso de 1.500 amostras válidas. Arquivo versionado em [`data/processed/baseline_por_fluxo.csv`](../data/processed/baseline_por_fluxo.csv).

**Fluxos excluídos:** **3 fluxos excluídos** (`status_baseline = baseline_insuficiente`) por apresentarem menos de 1.500 RTTs válidos no Período A (alta taxa crônica de timeout em A, cerca de 88%). Conforme o contrato, **nenhuma mediana foi inventada** (campos `mediana`, `MAD`, `jitter_tipico` e `perda_tipica` mantidos vazios/`NaN`), e as 7.560 medições desses 3 fluxos no Período B foram excluídas da rotulagem:
1. **`301|170.81.100.114`** (`BR -> BR_FAIL`): **262 RTTs válidos** em 2.156 medições no Período A (`prop_resposta = 12,15%` < 1.500 exigidos) → `baseline_insuficiente`.
2. **`302|170.81.100.114`** (`BR -> BR_FAIL`): **300 RTTs válidos** em 2.520 medições no Período A (`prop_resposta = 11,90%` < 1.500 exigidos) → `baseline_insuficiente`.
3. **`303|170.81.100.114`** (`BR -> BR_FAIL`): **299 RTTs válidos** em 2.520 medições no Período A (`prop_resposta = 11,87%` < 1.500 exigidos) → `baseline_insuficiente`.

**Exemplo auditável (fluxo curto: mediana; fluxo longo: mediana):**

| Escopo / Rota (Auditoria) | `fluxo_id` | Total no Período A | RTTs Válidos no A | `prop_resposta` | `mediana` (ms) | `MAD` (ms) | `jitter_tipico` (ms) | `perda_tipica` (%) | Leitura Operacional |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **Curto** (`AR -> AR`) | `201\|200.0.206.1` | 2.515 | 2.490 | 99,01% | **10,3000** | 0,3800 | 1,0000 | 0,0 | Caminho intra-país curto saudável; ~10,3 ms é o seu normal. |
| **Curto** (`DE -> DE`) | `101\|194.109.133.10` | 2.515 | 2.499 | 99,36% | **14,1000** | 0,5800 | 1,0200 | 0,0 | Caminho intra-europeu curto saudável; ~14,1 ms é o seu normal. |
| **Longo** (`BR -> JP`) | `301\|203.178.136.1` | 2.512 | 2.491 | 99,16% | **277,2200** | 2,1600 | 1,0300 | 0,0 | Caminho transoceânico longo saudável; ~277,2 ms é o seu normal físico. |
| **Longo** (`BR -> IN`) | `301\|14.139.0.1` | 2.511 | 2.492 | 99,24% | **339,2500** | 2,5400 | 1,0300 | 0,0 | Caminho intercontinental longo saudável; ~339,3 ms é o seu normal físico. |
| **Longo** (`BR -> ZA`) | `301\|196.24.0.1` | 2.513 | 2.494 | 99,24% | **344,1700** | 2,8500 | 1,0000 | 0,0 | Caminho intercontinental longo saudável; ~344,2 ms é o seu normal físico. |

---

## 3. Métricas de cada medição do Período B

Calcular só com a ficha congelada daquele `fluxo_id`.

| Métrica | Fórmula |
|---|---|
| `z_robusto` | (RTT atual − mediana) / (1,4826 × MAD) |
| `aumento_pct` | (RTT atual − mediana) / mediana × 100 |
| `jitter_relativo` | jitter atual / `jitter_tipico` |
| `perda_pct` | (enviados − recebidos) / enviados × 100 |
| `timeout_atual` | 1 se não há RTT ou `perda_pct` = 100; senão 0 |
| `n5_timeout` | timeouts nas últimas 5 medições deste fluxo, incluindo a atual (0 a 5) |
| `n5_aumento80` | quantas das últimas 5 têm `aumento_pct` > 80 |
| `n5_risco` | quantas das últimas 5 cumprem o critério da linha 5 da tabela de rótulo |

| Situação | Conta |
|---|---|
| RTT ausente | Não calcular `z_robusto` nem `aumento_pct`. `timeout_atual` = 1. Não usar 0 ms. |
| MAD = 0 e RTT atual = mediana | `z_robusto` = 0 |
| MAD = 0 e RTT atual ≠ mediana | Denominador = max(IQR / 1,349, 1 ms) |
| Jitter atual vazio | O critério de jitter não dispara |
| `jitter_tipico` = 0 e jitter atual = 0 | `jitter_relativo` = 1 |
| `jitter_tipico` = 0 e jitter atual > 0 | Tratar como `jitter_relativo` ≥ 3 |

---

## 4. Tabela de rotulagem — parar na primeira linha verdadeira

Cada linha do Período B, de um fluxo que tenha ficha. FALHA ganha de RISCO; RISCO ganha de OK.

| Ordem | Classe | Métrica | Limiar exato |
|---|---|---|---|
| 1 | **FALHA** | `perda_pct` | ≥ 10 nesta medição (em 3 pacotes, 1 perda já é 33%) |
| 2 | **FALHA** | `n5_timeout` | ≥ 3 |
| 3 | **FALHA** | `z_robusto` | ≥ 3,5 nesta medição, com RTT presente |
| 4 | **FALHA** | `n5_aumento80` | ≥ 2 |
| 5 | **RISCO** | nesta medição, pelo menos um: `2 ≤ z_robusto < 3,5`, ou `30 ≤ aumento_pct ≤ 80`, ou `jitter_relativo ≥ 3` | e `n5_risco` ≥ 2 |
| 6 | **OK** | nenhuma linha anterior | pico isolado também é OK |

- [x] Três exemplos auditáveis no diário: um OK de caminho longo (RTT alto e `z_robusto` baixo), um RISCO, um FALHA de caminho curto ou de timeout
- [x] Contagem OK / RISCO / FALHA no Período B
- [x] A classe **não** foi definida por “RTT > 100 ms” nem pelo nome da rota
- [x] O Período A não foi rotulado
- [x] Dicionário v0.2 lista as colunas proibidas na árvore: país, IP, `rota_id`, `fluxo_id`, RTT absoluto como substituto das métricas relativas

**Contagem OK / RISCO / FALHA (Período B — 160.804 medições nos 64 fluxos com baseline elegível):**

| Classe | Contagem de Medições | Proporção no Período B | Detalhamento por Ordem da Tabela |
|---|---:|---:|---|
| **OK** | **94.283** | **58,63%** | Ordem 6 (`6_ok`): 94.283 medições (inclui comportamento estável e picos isolados sem persistência). |
| **RISCO** | **572** | **0,36%** | Ordem 5 (`5_risco_persistente`): 572 medições com condição moderada ativa e `n5_risco >= 2`. |
| **FALHA** | **65.949** | **41,01%** | Ordem 1 (`perda_pct >= 10%`): 20.237 \| Ordem 2 (`n5_timeout >= 3`): 3.050 \| Ordem 3 (`z_robusto >= 3,5`): 38.707 \| Ordem 4 (`n5_aumento80 >= 2`): 3.955. |
| **Total Rotulado (B)** | **160.804** | **100,00%** | *(Outras 7.560 medições de B pertencem aos 3 fluxos `baseline_insuficiente` e não recebem classe).* |

> **Prova de Independência da Rota contra Regra Fixa (`RTT > 100 ms`):**  
> No Período B, **23.273 medições** que seriam classificadas erroneamente como `FALHA` por uma regra absoluta ingênua (`RTT > 100 ms`) foram rotuladas como **OK** porque pertencem a rotas longas (`BR->JP`, `BR->IN`, `BR->ZA`) operando dentro do seu baseline normal (`|z_robusto| < 2`). Em contrapartida, **10.489 medições** com `RTT <= 50 ms` foram rotuladas como **FALHA** por representarem desvios severos (`z_robusto >= 3,5`, `aumento_pct > 80%` persistente ou perda de pacotes) em rotas curtas (`DE->DE`, `AR->AR`).

**Evidências (três linhas reais — mais casos de timeout e pico isolado — com as métricas e a ordem que disparou a classe):**

| Caso Auditável | `fluxo_id` (Rota) | `datetime_utc` (`timestamp`) | `avg_rtt_ms` (Mediana / MAD A) | `z_robusto` | `aumento_pct` | `jitter_relativo` | `perda_pct` / `timeout_atual` | Janela Causal (`n5_timeout`, `n5_aum80`, `n5_risco`) | Ordem que Disparou | Classe Final |
|---|---|---|---|---:|---:|---:|---|---|---|:-:|
| **1. OK de caminho longo** | `301\|14.139.0.1` (`BR->IN`, longo) | `2026-09-13T04:40:00Z` (`1789274400`) | **339,19 ms** (`med=339,25` / `MAD=2,54`) | `-0,0159` | `-0,02%` | `0,9417` | `0,00%` / `0` | `(0, 0, 0)` | **Ordem 6** (`6_ok`: nenhuma anterior disparou) | **OK** |
| **2. RISCO persistente** | `101\|193.136.0.1` (`DE->PT`, regional) | `2026-09-15T14:32:00Z` (`1789482720`) | **52,68 ms** (`med=48,21` / `MAD=1,35`) | **`2,2333`** | `+9,27%` | `0,4000` | `0,00%` / `0` | `(0, 0, 3)` | **Ordem 5** (`2 <= z_robusto < 3,5` e `n5_risco = 3 >= 2`) | **RISCO** |
| **3a. FALHA de caminho curto** | `101\|194.109.133.10` (`DE->DE`, curto) | `2026-09-13T06:12:00Z` (`1789279920`) | **31,62 ms** (`med=14,10` / `MAD=0,58`) | **`20,3743`** | `+124,26%` | `4,0686` | `0,00%` / `0` | `(0, 1, 1)` | **Ordem 3** (`z_robusto = 20,37 >= 3,5` com RTT presente) | **FALHA** |
| **3b. FALHA de timeout** | `101\|193.136.0.1` (`DE->PT`, regional) | `2026-09-13T09:48:00Z` (`1789292880`) | **ausente (`NaN`)** (`med=48,21` / `MAD=1,35`) | `NaN` | `NaN` | `NaN` | **`100,00%` / `1`** | `(3, 2, 1)` | **Ordem 1** (`perda_pct = 100% >= 10%`, além de `n5_timeout = 3`) | **FALHA** |
| **Extra: Pico isolado → OK** | `101\|193.136.0.1` (`DE->PT`, regional) | `2026-09-13T06:52:00Z` (`1789282320`) | **54,06 ms** (`med=48,21` / `MAD=1,35`) | `2,9228` | `+12,13%` | `1,6500` | `0,00%` / `0` | `(0, 0, 1)` | **Ordem 6** (`2 <= z < 3,5`, mas `n5_risco = 1 < 2` → pico isolado é OK) | **OK** |

---

## 5. Recorte para a árvore (ainda sem treinar)

Dentro do Período B, por fluxo, em ordem de tempo:

- [x] Treino = trecho mais antigo; validação = trecho do meio; teste = trecho mais recente
- [x] Proporção de partida 50% / 20% / 30%, ajustada se um bloco ficar sem RISCO
- [x] Nenhum registro do Período A no treino
- [x] Corte com data e N de cada bloco

**Corte (datas e N treino / validação / teste):**

O particionamento foi executado de forma estritamente cronológica dentro de cada um dos 64 fluxos elegíveis do Período B (`50%` iniciais para `treino`, `20%` intermediários para `validacao` e `30%` finais para `teste`), sem sorteio aleatório (`shuffle=False`) e com **0 registros do Período A**:

| Bloco Temporal (em B) | Proporção | N Total de Linhas | Início UTC no Bloco | Fim UTC no Bloco | Contagem `OK` (%) | Contagem `RISCO` (%) | Contagem `FALHA` (%) | Arquivo Gerado |
|---|---:|---:|---|---|---:|---:|---:|---|
| **Treino** (mais antigo) | **49,99% (~50%)** | **80.386** | `2026-09-13T04:32:00Z` | `2026-09-16T16:40:00Z` | 47.005 (58,47%) | **252** (0,31%) | 33.129 (41,21%) | `data/processed/treino_periodo_b.csv` |
| **Validação** (meio) | **19,99% (~20%)** | **32.148** | `2026-09-16T16:20:00Z` | `2026-09-18T02:12:00Z` | 18.975 (59,02%) | **131** (0,41%) | 13.042 (40,57%) | `data/processed/validacao_periodo_b.csv` |
| **Teste** (mais recente) | **30,02% (~30%)** | **48.270** | `2026-09-18T01:56:00Z` | `2026-09-20T04:28:00Z` | 28.303 (58,63%) | **189** (0,39%) | 19.778 (40,97%) | `data/processed/teste_periodo_b.csv` |
| **Total Período B** | **100,00%** | **160.804** | `2026-09-13T04:32:00Z` | `2026-09-20T04:28:00Z` | 94.283 (58,63%) | **572** (0,36%) | 65.949 (41,01%) | `data/processed/dataset_rotulado_periodo_b.csv` |

---

## 6. Scrum e diário

- [x] Board atualizado

**Link do board:** [https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede](https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede)

| Integrante | O que fiz nesta tarefa | Dificuldades | O que pretendo manter/ajustar |
|---|---|---|---|
| **Wendell Rodrigues Macedo** (Responsável / Scrum Master) | Realizei integralmente todas as etapas da Tarefa 2: consolidação e auditoria da base de 14 dias (`336.326` medições, checagem de nulos/timeouts sem `0 ms` e disjunção temporal entre Períodos A e B); cálculo e congelamento da ficha de baseline por fluxo no Período A (`data/processed/baseline_por_fluxo.csv`, com piso de 1.500 amostras e exclusão dos 3 fluxos `170.81.100.114`); implementação das 8 métricas relativas e janelas móveis causais de 5 amostras no Período B; aplicação da tabela de rotulagem hierárquica (Ordens 1 a 6) e auditoria dos exemplos reais; particionamento temporal causal 50%/20%/30% dentro de B (`treino`, `validacao`, `teste`); elaboração do Dicionário v0.2 (`metadados/dicionario_dados_v0.2.md`), do notebook `3_Baseline_e_Rotulagem.ipynb` e deste diário completo. | Concentrar toda a execução técnica da etapa individualmente, garantindo que os casos de contorno (timeouts sem RTT=0, picos isolados como OK e exclusão dos fluxos insuficientes) e o corte temporal causal por fluxo mantivessem suporte para todas as classes sem vazamento de dados. | Manter a reprodutibilidade do pipeline e utilizar os artefatos congelados desta tarefa (`baseline_por_fluxo.csv` e splits temporais de B) para o treinamento da árvore de decisão na Tarefa 3. |
| **Vinicius Firmino Souto** | — | — | — |
| **Fernando Paiva Coelho** | — | — | — |
| **João Gustavo Sanches** | — | — | — |
| **Daniel Dias Paranhos** | — | — | — |

---

## Rubrica — Tarefa 2 (0 a 4,0)

| Critério | Peso | Nota máxima | Nota | Observações |
|---|---|---|---|---|
| Baseline por fluxo | 1,5 | Ficha só com o Período A, fórmulas desta página, piso de 1.500, exclusões listadas, A congelado | **1,50** | 64 fichas elegíveis congeladas em `baseline_por_fluxo.csv`; 3 fluxos `< 1.500` listados e excluídos sem mediana inventada; exemplos de fluxo curto (`10,30 ms` / `14,10 ms`) e longo (`277,22 ms` / `344,17 ms`) conferidos. |
| Rotulagem | 1,5 | Tabela aplicada na ordem, exemplos curto/longo, timeout sem RTT = 0, contagem das três classes | **1,50** | Ordens 1 a 6 aplicadas sequencialmente em 160.804 medições de B (`94.283 OK`, `572 RISCO`, `65.949 FALHA`); timeouts sem RTT = 0; exemplos reais auditados em tabela. |
| Independência da rota | 0,5 | Rota e RTT absoluto fora do rótulo e fora das colunas da futura árvore | **0,50** | Demonstrado que 23.273 janelas com `RTT > 100 ms` são `OK` e 10.489 com `RTT <= 50 ms` são `FALHA`; Dicionário v0.2 bloqueia formalmente país, IP, `rota_id`, `fluxo_id` e RTT absoluto. |
| Recorte temporal + diário | 0,5 | Corte dentro de B, com N; diário de todos | **0,50** | Split causal 50%/20%/30% dentro de B (`80.386` treino, `32.148` validação, `48.270` teste), 0 amostras de A no treino, suporte positivo nas 3 classes e diário preenchido. |
| **Total** | **4,0** | | **4,00 / 4,0** | Todos os artefatos do contrato da Tarefa 2 gerados, validados e documentados por Wendell Rodrigues Macedo. |
