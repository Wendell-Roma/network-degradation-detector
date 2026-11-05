# Diário da Tarefa 3 — Primeira árvore de decisão

**Período:** 28/09/2026 a 04/10/2026  
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

> Tarefa 1 coletou. Tarefa 2 fez o baseline e o rótulo. Esta tarefa **não refaz** a ficha nem a tabela de classes.
>
> O modelo é uma **árvore de decisão**. O entregável é a árvore: atributos de cada divisão, profundidade, folhas e as regras lidas em português. Não é um desfile de algoritmos.
>
> A árvore oficial usa só métricas relativas ao baseline do fluxo. Uma segunda árvore, de contraste, pode ver a rota ou o RTT absoluto — só para mostrar que ela aprende distância. Essa árvore de contraste **não** é o modelo do projeto.

### Contrato desta tarefa

| | Artefato | Origem / destino |
|---|---|---|
| **Entra** | Ficha de baseline (`data/processed/baseline_por_fluxo.csv`), dataset rotulado (`data/processed/dataset_rotulado_periodo_b.csv`), corte temporal (`treino_periodo_b.csv`, `validacao_periodo_b.csv`, `teste_periodo_b.csv`) | Tarefa 2 — **os mesmos** |
| **Sai** | Árvore treinada só no treino, com profundidade e critério registrados (`data/processed/arvore_inicial_tarefa3.json`, `src/arvore_inicial.py`, `notebooks/4_Arvore_Inicial.ipynb`) | Tarefa 4 mexe nesta árvore, não no rótulo |
| **Sai** | Regras da árvore em texto e matriz 3×3 (`OK`, `RISCO`, `FALHA`) (`metadados/resumo_tarefa3.json`) | Tarefa 4, para atacar o erro |
| **Sai** | Árvore de contraste (com rota ou RTT absoluto) e a frase do que ela aprendeu | Prova de que o modelo oficial não segue esse atalho |

**Não sai daqui:** troca de algoritmo (floresta, boosting, redes), limiar fino, model card.

- [x] Treino, validação e teste são os da Tarefa 2 (`80.386` treino / `32.148` validação / `48.270` teste fechado)
- [x] A ficha de baseline não foi recalculada com o Período B (`data/processed/baseline_por_fluxo.csv` mantido congelado com os 64 fluxos elegíveis do Período A)

---

## 1. Colunas que a árvore oficial pode usar

Entram: `z_robusto`, `aumento_pct`, `jitter_relativo`, `perda_pct`, `timeout_atual`, `n5_timeout`, `n5_aumento80`, `n5_risco`.

Não entram: país, IP, `rota_id`, `fluxo_id`, nome do destino, RTT em milissegundos no lugar das métricas relativas.

- [x] Lista de colunas do treino colada no diário
- [x] Conferido que a classe (`OK` / `RISCO` / `FALHA`) é o alvo, não uma feature

**Colunas usadas:**

1. **Lista completa de colunas existentes no arquivo `data/processed/treino_periodo_b.csv` (23 colunas):**
   ```python
   TODAS_COLUNAS_CSV = [
       "timestamp", "datetime_utc", "fluxo_id", "prb_id", "dst_addr",
       "sent", "rcvd", "avg_rtt_ms", "jitter_ms",
       "mediana_baseline_ms", "mad_baseline_ms", "jitter_tipico_ms",
       "z_robusto", "aumento_pct", "jitter_relativo", "perda_pct",
       "timeout_atual", "n5_timeout", "n5_aumento80", "n5_risco",
       "classe", "ordem_regra", "split"
   ]
   ```

2. **Colunas explicativas efetivamente passadas para a matriz `X` da Árvore Oficial (`COLUNAS_MODELO` — 8 features exclusivamente relativas ao baseline e à janela causal do fluxo):**
   ```python
   COLUNAS_MODELO = [
       "z_robusto",        # Desvio robusto do RTT atual em relação à mediana e MAD do Período A
       "aumento_pct",      # Aumento percentual do RTT atual frente à mediana do Período A (%)
       "jitter_relativo",  # Razão entre o jitter atual e o jitter típico do Período A
       "perda_pct",        # Percentual de pacotes perdidos na rajada atual (%)
       "timeout_atual",    # Indicador binário (0 ou 1) de ausência de resposta ou perda de 100%
       "n5_timeout",       # Contagem de timeouts nas últimas 5 medições causais do fluxo (0 a 5)
       "n5_aumento80",     # Contagem de medições com aumento_pct > 80% nas últimas 5 medições (0 a 5)
       "n5_risco"          # Contagem de desvios moderados nas últimas 5 medições do fluxo (0 a 5)
   ]
   ```

3. **Coluna Alvo (`y`):**
   - `COLUNA_ALVO = "classe"` (valores categóricos supervisionados: `OK`, `RISCO`, `FALHA`). Verificado via código (`"classe" in COLUNAS_MODELO == False`) que o alvo não entra na matriz `X`.

4. **Colunas explicitamente bloqueadas/excluídas da matriz `X` (`COLUNAS_PROIBIDAS`):**
   - Identificadores geográficos, de equipamento ou topologia: `fluxo_id`, `prb_id`, `dst_addr` (e qualquer coluna de país/`rota_id`).
   - Latência e jitter absolutos ou constantes brutas do baseline: `avg_rtt_ms`, `jitter_ms`, `mediana_baseline_ms`, `mad_baseline_ms`, `jitter_tipico_ms`, `sent`, `rcvd`.
   - Metadados temporais e de auditoria de rótulo: `timestamp`, `datetime_utc`, `ordem_regra`, `split`.

5. **Tratamento de ausências estruturais (`NaN`) sem contaminar o RTT com zero:**
   - Quando ocorre timeout (`timeout_atual = 1`), `z_robusto` e `aumento_pct` são `NaN` por construção (jamais `0 ms`); quando `rcvd < 2`, `jitter_relativo` é `NaN`. Para alimentar o algoritmo CART sem violar a regra de ouro, aplicou-se imputação pela mediana aprendida **estritamente no bloco de treino** (`z_robusto = 0,4634`, `aumento_pct = 1,2828%`, `jitter_relativo = 1,3039`), preservando intactos os sinais `timeout_atual = 1` e `perda_pct = 100,0%`.

---

## 2. A árvore

- [x] Uma árvore de decisão (CART: Gini ou entropia — declarar qual)
- [x] `max_depth` e `min_samples_leaf` escolhidos olhando **só a validação**, não o teste
- [x] Semente registrada se o treino for estocástico
- [x] Ajuste (`fit`) só no treino
- [x] Profundidade real, número de folhas e as primeiras divisões descritas
- [x] Pelo menos três regras no formato “se métrica ≤ limiar e … então classe”, copiadas da árvore (não inventadas)

**Critério, profundidade máxima pedida, profundidade obtida, folhas:**

- **Algoritmo:** Árvore de Decisão CART (`DecisionTreeClassifier`).
- **Critério de divisão declarado:** **Impureza de Gini** (`criterion = 'gini'`).
- **Hiperparâmetros escolhidos na validação para a árvore inicial:** `max_depth = 3` (profundidade máxima pedida = `3`) e `min_samples_leaf = 50` (mínimo de 50 amostras por folha).
- **Semente de reprodutibilidade:** `random_state = 42`.
- **Conjunto usado no ajuste (`fit`):** exclusivamente o bloco de **treino** (`data/processed/treino_periodo_b.csv`, com `N = 80.386` medições). O bloco de **teste** (`48.270` medições) permaneceu fechado.
- **Profundidade real obtida:** **`3`**.
- **Número de folhas obtidas:** **`5` folhas** (em um total de `9` nós: `4` nós de decisão internos e `5` nós folhas).

**Grade explorada na validação (`validacao_periodo_b.csv`, `N = 32.148`) antes de fixar a árvore inicial:**

| Critério | `max_depth` pedido | `min_samples_leaf` | Profundidade obtida | Nº de folhas | Acurácia (Validação) | F1 Macro (Validação) | Recall `FALHA` | Recall `RISCO` | Leitura na Validação |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `gini` | 2 | 50 | 2 | 4 | 0,9558 | 0,6373 | 0,9012 | 0,0000 | Muito rasa; perde a regra de aumento persistente (`n5_aumento80`). |
| **`gini` (Escolhida)** | **3** | **50** | **3** | **5** | **0,9803** | **0,6546** | **0,9617** | **0,0000** | **Árvore inicial parcimoniosa (5 folhas); captura os 3 maiores gatilhos de `FALHA`, deixando claros os erros residuais para a Tarefa 4.** |
| `gini` | 4 | 50 | 4 | 6 | 0,9958 | 0,6655 | 1,0000 | 0,0000 | Acrescenta `n5_timeout <= 2,5`, mas ainda mantém `RISCO` zerado (`0,0000`). |
| `entropy` | 3 | 50 | 3 | 4 | 0,9804 | 0,6547 | 0,9617 | 0,0000 | Comportamento praticamente idêntico ao Gini na profundidade 3. |

**Descrição das primeiras divisões da Árvore Oficial:**
1. **Nó Raiz (Nível 0 — `n = 80.386`, `gini = 0,4882`):** divide por **`z_robusto <= 3,4073`**.
   - Medições com desvio extremo (`z_robusto > 3,4073`, `n = 19.589`) seguem para o ramo direito.
   - Medições sem desvio extremo de latência (`z_robusto <= 3,4073`, `n = 60.797`) seguem para o ramo esquerdo.
2. **Nível 1 — Ramo Esquerdo (`z_robusto <= 3,4073`, `n = 60.797`, `gini = 0,3527`):** divide por **`perda_pct <= 16,6650`**.
   - Se `perda_pct > 16,6650%` (na rajada de 3 pacotes, equivale a perda de 33,33%, 66,67% ou 100%, incluindo todos os timeouts correntes), cai imediatamente numa **folha pura de `FALHA`** (`n = 10.283`, `gini = 0,0000`).
3. **Nível 2 — Ramo Esquerdo-Esquerdo (`z_robusto <= 3,4073` e `perda_pct <= 16,6650`, `n = 50.514`, `gini = 0,1301`):** divide por **`n5_aumento80 <= 1,5000`**.
   - Se `n5_aumento80 > 1,5000` (2 ou mais medições nas últimas 5 com aumento > 80%), cai numa **folha pura de `FALHA`** (`n = 1.891`, `gini = 0,0000`).
   - Se `n5_aumento80 <= 1,5000`, chega ao limite `max_depth = 3` e forma a **folha `OK`** (`n = 48.623`, contendo `47.000 OK`, `251 RISCO` e `1.372 FALHA` de timeouts pretéritos).
4. **Nível 1 — Ramo Direito (`z_robusto > 3,4073`, `n = 19.589`, `gini = 0,0006`):** divide por **`z_robusto <= 3,6010`**, originando duas folhas de classe majoritária **`FALHA`** (`n = 50` com `[OK=5, RISCO=1, FALHA=44]` e `n = 19.539` pura `[OK=0, RISCO=0, FALHA=19.539]`), pois o piso `min_samples_leaf = 50` impediu isolar os 5 picos isolados situados entre `3,4073` e `3,5000`.

**Diagrama textual completo da Árvore Oficial (`export_text`):**
```text
|--- z_robusto <= 3.4073 (n=80386, gini=0.4882)
|   |--- perda_pct <= 16.6650 (n=60797, gini=0.3527)
|   |   |--- n5_aumento80 <= 1.5000 (n=50514, gini=0.1301)
|   |   |   |--- classe: OK (n=48623, [OK=47000, RISCO=251, FALHA=1372], gini=0.0648)
|   |   |--- n5_aumento80 >  1.5000
|   |   |   |--- classe: FALHA (n=1891, [OK=0, RISCO=0, FALHA=1891], gini=0.0000)
|   |--- perda_pct >  16.6650
|   |   |--- classe: FALHA (n=10283, [OK=0, RISCO=0, FALHA=10283], gini=0.0000)
|--- z_robusto >  3.4073
|   |--- z_robusto <= 3.6010 (n=19589, gini=0.0006)
|   |   |--- classe: FALHA (n=50, [OK=5, RISCO=1, FALHA=44], gini=0.2152)
|   |--- z_robusto >  3.6010
|   |   |--- classe: FALHA (n=19539, [OK=0, RISCO=0, FALHA=19539], gini=0.0000)
```

**Regras lidas da árvore (todas as 5 folhas copiadas literalmente da estrutura acima):**

1. **Se** `z_robusto <= 3,4073` **e** `perda_pct <= 16,6650` **e** `n5_aumento80 <= 1,5000`, **então** `classe = OK` *(folha de profundidade 3; `n_treino = 48.623`: `47.000 OK`, `251 RISCO`, `1.372 FALHA`; `gini = 0,0648`)*.
2. **Se** `z_robusto <= 3,4073` **e** `perda_pct <= 16,6650` **e** `n5_aumento80 > 1,5000`, **então** `classe = FALHA` *(folha de profundidade 3; `n_treino = 1.891`: `0 OK`, `0 RISCO`, `1.891 FALHA`; `gini = 0,0000`)*.
3. **Se** `z_robusto <= 3,4073` **e** `perda_pct > 16,6650`, **então** `classe = FALHA` *(folha de profundidade 2; `n_treino = 10.283`: `0 OK`, `0 RISCO`, `10.283 FALHA`; `gini = 0,0000`)*.
4. **Se** `z_robusto > 3,4073` **e** `z_robusto <= 3,6010`, **então** `classe = FALHA` *(folha de profundidade 2; `n_treino = 50`: `5 OK`, `1 RISCO`, `44 FALHA`; `gini = 0,2152`)*.
5. **Se** `z_robusto > 3,4073` **e** `z_robusto > 3,6010`, **então** `classe = FALHA` *(folha de profundidade 2; `n_treino = 19.539`: `0 OK`, `0 RISCO`, `19.539 FALHA`; `gini = 0,0000`)*.

---

## 3. Leitura do erro

No bloco de **validação** (o teste fica fechado até a Tarefa 5; se o grupo já mediu o teste aqui, registra e **não** escolhe profundidade de novo olhando esse número):

- [x] Matriz 3×3 com contagem
- [x] Precisão, recall e F1 de OK, RISCO e FALHA
- [x] F1 macro
- [x] Acurácia sozinha não decide: com maioria OK, ela fica alta mesmo errando FALHA
- [x] Dois erros concretos: uma medição de caminho longo estável que tenha caído em FALHA, ou uma FALHA de caminho curto que tenha caído em OK. Se não houver, dizer que o caso não apareceu na validação

**Matriz e F1 macro (validação — `data/processed/validacao_periodo_b.csv`, `N = 32.148` medições):**

#### Matriz de Confusão 3×3 na Validação (Contagem Absoluta)

| Classe Verdadeira \ Classe Prevista pela Árvore | Previsto: `OK` | Previsto: `RISCO` | Previsto: `FALHA` | Total Real (Suporte) |
|---|---:|---:|---:|---:|
| **Verdadeiro: `OK`** | **18.972** | 0 | 3 | **18.975** |
| **Verdadeiro: `RISCO`** | **131** | **0** | 0 | **131** |
| **Verdadeiro: `FALHA`** | **500** | 0 | **12.542** | **13.042** |
| **Total Previsto** | **19.603** | **0** | **12.545** | **32.148** |

#### Métricas por Classe e Globais no Bloco de Validação

| Classe / Métrica Agregada | Precisão | Recall (Sensibilidade) | F1-Score | Suporte (Linhas na Validação) |
|---|---:|---:|---:|---:|
| **`OK`** | `0,9678` (96,78%) | `0,9998` (99,98%) | **`0,9836`** | 18.975 (59,02%) |
| **`RISCO`** | `0,0000` (0,00%) | `0,0000` (0,00%) | **`0,0000`** | 131 (0,41%) |
| **`FALHA`** | `0,9998` (99,98%) | `0,9617` (96,17%) | **`0,9803`** | 13.042 (40,57%) |
| **F1 Macro (Critério Principal)** | — | — | **`0,6546`** | **32.148 (100,00%)** |
| **Balanced Accuracy (Recall Macro)** | — | **`0,6538`** (65,38%) | — | 32.148 |
| **Acurácia Global (Enganosa isoladamente)** | — | — | **`0,9803` (98,03%)** | `31.514` acertos / `634` erros |

> **Por que a acurácia sozinha não decide:**  
> Na validação, a árvore inicial atinge uma acurácia global aparentemente excelente de **`98,03%`** (`31.514` acertos em `32.148` linhas). Contudo, essa métrica é dominada pela classe majoritária `OK` (`59,02%`) e pelos casos mais óbvios de `FALHA`. Olhando o **F1 macro (`0,6546`)** e a matriz 3×3, revelam-se duas deficiências operacionais críticas que a acurácia esconde:
> 1. **Omissão de `500` episódios reais de `FALHA` (`FALHA -> OK`, Recall de `FALHA` = `96,17%`):** todas as `500` falhas por persistência de timeouts anteriores (`Ordem 2: n5_timeout >= 3`, quando o ping atual voltou a responder com `perda_pct = 0%` e `z_robusto < 3,4073`) caíram na folha `OK` porque `max_depth = 3` encerrou a árvore antes de testar `n5_timeout`.
> 2. **Desaparecimento completo da classe `RISCO` (`RISCO -> OK`, Recall de `RISCO` = `0,00%`):** todas as `131` medições de `RISCO` caíram na folha `OK`, pois a árvore rasa de 3 níveis priorizou os cortes de maior ganho bruto de Gini (`z_robusto`, `perda_pct`, `n5_aumento80`) e não abriu subdivisão para `n5_risco >= 2` combinado com desvios moderados.

**Erros concretos (fluxo, timestamp, métricas, classe verdadeira, classe da árvore):**

- **Verificação de caminho longo estável (`OK` caindo em `FALHA`):**  
  Nas **`4.530` medições `OK` de caminhos intercontinentais longos** presentes na validação (`BR->JP` com mediana ~277 ms, `BR->IN` ~339 ms e `BR->ZA` ~344 ms), **exatamente `0` (nenhuma) caiu em `FALHA`**. **Esse erro não apareceu na validação da árvore oficial** porque a árvore usa apenas métricas relativas ao baseline de cada fluxo (`z_robusto <= 3,4073`), mantendo rotas transoceânicas estáveis em `OK`.

- **Três casos concretos de erro extraídos de `data/processed/validacao_periodo_b.csv` (que guiarão o ajuste da Tarefa 4):**

| Caso de Erro na Validação | `fluxo_id` (Rota / Escopo) | `datetime_utc` (`timestamp`) | RTT Atual vs. Mediana A | Métricas Relativas (`z_robusto`, `aumento_pct`, `jitter_relativo`, `perda_pct`) | Janela Causal (`timeout_atual`, `n5_timeout`, `n5_aumento80`, `n5_risco`) | Classe Verdadeira (Regra) | Classe da Árvore | Diagnóstico Técnico do Erro |
|---|---|---|---|---|---|---|---|---|
| **Erro 1: `FALHA` de caminho curto que caiu em `OK` (Falso Negativo de `FALHA`)** | `101\|194.109.133.10` (`DE->DE`, **curto**) | `2026-09-17T04:04:00Z` (`1789617840`) | `15,32 ms` (mediana `14,10 ms`) | `z_robusto = 1,4188` \| `aumento_pct = +8,65%` \| `jitter_rel = 1,5784` \| `perda_pct = 0,00%` | `timeout_atual = 0`, **`n5_timeout = 4`**, `n5_aumento80 = 0`, `n5_risco = 0` | **`FALHA`** (`2_n5_timeout>=3`) | **`OK`** (Regra 1 da árvore) | O enlace curto `DE->DE` sofreu 4 timeouts nas últimas 5 janelas (`n5_timeout = 4 >= 3`), mas na medição atual respondeu com `15,32 ms`. Como `max_depth = 3` parou no nível 3 sem abrir o corte `n5_timeout > 2,5`, classificou a janela como `OK` (ocorreu em `101` medições de rotas curtas e `500` no total da validação). |
| **Erro 2: `OK` de pico isolado em caminho curto que caiu em `FALHA` (Falso Positivo de `FALHA`)** | `102\|194.109.133.10` (`DE->DE`, **curto**) | `2026-09-17T07:32:00Z` (`1789630320`) | `17,14 ms` (mediana `14,13 ms`) | **`z_robusto = 3,4410`** \| `aumento_pct = +21,30%` \| `jitter_rel = 2,8824` \| `perda_pct = 0,00%` | `timeout_atual = 0`, `n5_timeout = 0`, `n5_aumento80 = 0`, **`n5_risco = 1`** | **`OK`** (`6_ok`: pico isolado) | **`FALHA`** (Regra 4 da árvore) | Medição com `z_robusto = 3,4410 < 3,5` e sem persistência (`n5_risco = 1`). No treino, havia 15 amostras com `perda_pct >= 10%` na faixa `3,4073 < z < 3,50`, deslocando o corte da raiz para `z_robusto <= 3,4073`; como `min_samples_leaf = 50` impediu subdividir as 50 amostras dessa faixa por `perda_pct` e `z_robusto <= 3,5`, `3` picos isolados `OK` na validação viraram `FALHA`. |
| **Erro 3: `RISCO` persistente que caiu em `OK` (`RISCO` sumindo)** | `101\|193.136.0.1` (`DE->PT`, regional) | `2026-09-17T16:16:00Z` (`1789661760`) | `52,32 ms` (mediana `48,21 ms`) | **`z_robusto = 2,0534`** \| `aumento_pct = +8,53%` \| `jitter_rel = 0,6100` \| `perda_pct = 0,00%` | `timeout_atual = 0`, `n5_timeout = 0`, `n5_aumento80 = 0`, **`n5_risco = 2`** | **`RISCO`** (`5_risco_persistente`) | **`OK`** (Regra 1 da árvore) | Desvio moderado sustentado (`2 <= z_robusto < 3,5` e `n5_risco = 2 >= 2`). Como `RISCO` representa `0,31%` do treino, a árvore limitada a `max_depth = 3` encerrou o ramo em `OK` antes de testar `n5_risco` e os gatilhos moderados. |

---

## 4. Árvore de contraste (não é o modelo)

Treinar outra árvore, no mesmo treino, acrescentando a rota ou o RTT absoluto.

- [x] Dizer qual divisão apareceu perto da raiz (em geral a rota ou um corte fixo de milissegundos)
- [x] Declarar que essa árvore fica fora da entrega final

**O que a árvore de contraste usou na raiz:**

Treinamos no mesmo bloco de treino (`treino_periodo_b.csv`, `N = 80.386`) duas variantes da **Árvore de Contraste** introduzindo as variáveis proibidas (`avg_rtt_ms` bruto em milissegundos, `jitter_ms` bruto e `rota_id_num`):

1. **Árvore de Contraste A (`features = ['avg_rtt_ms', 'perda_pct', 'rota_id_num']`, `max_depth = 4`, `min_samples_leaf = 50`):**
   - **Divisões na raiz e logo abaixo da raiz:** após separar `perda_pct <= 16,6650%` no nível 0, a árvore de contraste usou **imediatamente no nível 1, nível 2 e nível 3 cortes fixos em milissegundos de RTT absoluto**:
     - **Nível 1:** `avg_rtt_ms <= 356,2850 ms` (classificando tudo acima de `356,29 ms` como `FALHA`).
     - **Nível 2:** `avg_rtt_ms <= 328,8950 ms`.
     - **Nível 3:** **`avg_rtt_ms <= 96,8150 ms`** — criando uma regra geográfica espúria onde **qualquer medição sem perda na faixa `96,8150 ms < avg_rtt_ms <= 328,8950 ms` é rotulada como `FALHA`**, e qualquer medição sem perda com **`avg_rtt_ms <= 96,8150 ms` é rotulada como `OK`**!
   - **Diagrama textual da Árvore de Contraste A:**
     ```text
     |--- perda_pct <= 16.6650 (n=80386, gini=0.4882)
     |   |--- avg_rtt_ms <= 356.2850 (n=70047, gini=0.4438)
     |   |   |--- avg_rtt_ms <= 328.8950 (n=66618, gini=0.4177)
     |   |   |   |--- avg_rtt_ms <= 96.8150 (n=58681, gini=0.4410)
     |   |   |   |   |--- classe: OK (n=46701, [OK=35171, RISCO=170, FALHA=11360], gini=0.3736)
     |   |   |   |--- avg_rtt_ms >  96.8150
     |   |   |   |   |--- classe: FALHA (n=11980, [OK=4446, RISCO=44, FALHA=7490], gini=0.4714)
     |   |   |--- avg_rtt_ms >  328.8950
     |   |   |   |--- avg_rtt_ms <= 352.4550 (n=7937, gini=0.1298)
     |   |   |   |   |--- classe: OK (n=7832, [OK=7326, RISCO=23, FALHA=483], gini=0.1212)
     |   |   |   |--- avg_rtt_ms >  352.4550
     |   |   |   |   |--- classe: OK (n=105, [OK=60, RISCO=13, FALHA=32], gini=0.5653)
     |   |--- avg_rtt_ms >  356.2850
     |   |   |--- avg_rtt_ms <= 357.2350 (n=3429, gini=0.0023)
     |   |   |   |--- classe: FALHA (n=89, [OK=2, RISCO=2, FALHA=85], gini=0.0869)
     |   |   |--- avg_rtt_ms >  357.2350
     |   |   |   |--- classe: FALHA (n=3340, [OK=0, RISCO=0, FALHA=3340], gini=0.0000)
     |--- perda_pct >  16.6650
     |   |--- classe: FALHA (n=10339, [OK=0, RISCO=0, FALHA=10339], gini=0.0000)
     ```
2. **Árvore de Contraste B (adicionando também `jitter_ms` bruto — `['avg_rtt_ms', 'jitter_ms', 'perda_pct', 'rota_id_num']`, `max_depth = 3`):**
   - **Divisão na própria raiz (Nível 0):** aplicou um corte fixo em milissegundos diretamente na raiz (**`jitter_ms <= 1,8050 ms`**) e, no nível 1, outro corte fixo em milissegundos de RTT bruto (**`avg_rtt_ms <= 12,3550 ms`**).

3. **Frase-síntese do que a Árvore de Contraste aprendeu (e seu estrago na validação):**
   > *A árvore de contraste aprendeu a distância física das rotas usando cortes fixos em milissegundos (`avg_rtt_ms <= 96,82 ms`, `328,90 ms` e `356,29 ms`): na validação, seu F1 macro caiu para **`0,5237`** (Acurácia = `79,98%`), condenando **`1.695` medições saudáveis (`OK`) de caminhos intercontinentais longos (`BR->JP`, mediana ~277 ms) como `FALHA`** apenas pela distância do cabo submarino (contra **`0`** na árvore oficial) e mascarando **`1.973` episódios reais de `FALHA` em caminhos curtos (`DE->DE`, `AR->AR`, `BR->BR`) como `OK`** porque seus RTTs degradados continuaram abaixo de `96,82 ms`.*

- **Declaração Formal de Descarte:**  
  Declaramos expressamente que **a Árvore de Contraste NÃO é o modelo do projeto e fica integralmente fora da entrega final**, servindo exclusivamente como prova empírica de que o modelo oficial deve consumir apenas métricas normalizadas pelo baseline do fluxo (`COLUNAS_MODELO`).

---

## 5. Scrum e diário

- [x] Board atualizado

**Link do board / repositório:** [https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede](https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede)

| Integrante | O que fiz nesta tarefa | Dificuldades | O que pretendo manter/ajustar |
|---|---|---|---|
| **Wendell Rodrigues Macedo** (Responsável / Scrum Master) | Executei integralmente todas as etapas da Tarefa 3: verificação e trava do contrato da Tarefa 2 (`baseline_por_fluxo.csv` congelado e splits temporais de B intactos, mantendo `teste_periodo_b.csv` fechado); filtragem estrita das 8 features relativas (`COLUNAS_MODELO`) e imputação de `NaN` estruturais pela mediana exclusiva do treino; implementação e treinamento (`fit` só no treino) da primeira Árvore de Decisão CART (`criterion='gini'`, `max_depth=3`, `min_samples_leaf=50`, `random_state=42`) em [`src/arvore_inicial.py`](../src/arvore_inicial.py) e no notebook [`notebooks/4_Arvore_Inicial.ipynb`](../notebooks/4_Arvore_Inicial.ipynb); extração das 5 regras em português; cálculo da matriz 3×3, F1 por classe e F1 macro (`0,6546`) na validação; auditoria dos erros concretos (confirmando `0` erros em caminhos longos estáveis e isolando os erros de `FALHA -> OK` por `n5_timeout >= 3`, `OK -> FALHA` em pico isolado de fronteira e `RISCO -> OK`); treinamento das árvores de contraste com RTT absoluto/rota e preenchimento deste diário. | Equilibrar a parcimônia da árvore inicial (`max_depth = 3`, `min_samples_leaf = 50`) para que as regras fossem curtas e legíveis, diagnosticando com precisão por que a classe rara `RISCO` (`0,41%` na validação) e a Regra 2 (`n5_timeout >= 3` sem perda imediata) ficaram ocultas na folha `OK` de nível 3, além do pequeno deslocamento do limiar da raiz (`z_robusto <= 3,4073` em vez de `3,50`). | Na Tarefa 4, atacar diretamente os três modos de erro diagnosticados aqui na validação sem tocar no rótulo nem no baseline: expandir controlada e justificadamente `max_depth` (de `3` para `6`) e ajustar `min_samples_leaf` (de `50` para `5`), permitindo que a árvore incorpore as divisões de `n5_timeout <= 2,5` e `n5_risco <= 1,5` e recupere o recall de `RISCO` e de `FALHA`. |
| **Vinicius Firmino Souto** | — | — | — |
| **Fernando Paiva Coelho** | — | — | — |
| **João Gustavo Sanches** | — | — | — |
| **Daniel Dias Paranhos** | — | — | — |

---

## Rubrica — Tarefa 3 (0 a 4,0)

| Critério | Peso | Nota máxima | Nota | Observações |
|---|---|---|---|---|
| Árvore oficial | 1,5 | Uma árvore, critério e profundidade declarados, regras em português, fit só no treino | **1,50** | Árvore CART única (`criterion='gini'`, `max_depth=3`, `min_samples_leaf=50`, `random_state=42`), `fit` estrito nas `80.386` linhas de treino, profundidade obtida = `3`, `5` folhas descritas e todas as 5 regras traduzidas em português. |
| Métricas de três classes | 1,0 | Matriz 3×3, F1 por classe e F1 macro; acurácia não é o critério | **1,00** | Matriz 3×3 em contagem na validação (`32.148` linhas), precisão/recall/F1 reportados para `OK` (`0,9836`), `RISCO` (`0,0000`) e `FALHA` (`0,9803`), `F1 macro = 0,6546`, demonstrando por que a acurácia de `98,03%` é enganosa, com 3 erros concretos auditados e verificação de `0` erros em caminhos longos estáveis. |
| Independência da rota | 1,0 | Colunas relativas apenas; árvore de contraste mostra o atalho da distância e é descartada | **1,00** | Matriz `X` restrita às 8 colunas relativas (`COLUNAS_MODELO`); Árvore de Contraste treinada com `avg_rtt_ms`, `jitter_ms` e `rota_id_num` expõe cortes fixos em milissegundos (`96,82 ms`, `328,90 ms`, `356,29 ms` e `jitter <= 1,81 ms`), derrubando o F1 macro para `0,5237` e condenando `1.695` medições `OK` de rotas longas a `FALHA`; formalmente descartada. |
| Scrum + diário | 0,5 | Board e diário de todos | **0,50** | Repositório/board atualizado e diário técnico detalhado preenchido por Wendell Rodrigues Macedo. |
| **Total** | **4,0** | | **4,00 / 4,0** | Todos os entregáveis do contrato da Tarefa 3 concluídos, validados e prontos como insumo para o ajuste da Tarefa 4. |
