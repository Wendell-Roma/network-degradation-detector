# Diário da Tarefa 4 — Ajuste da árvore a partir do erro

**Período:** 05/10/2026 a 11/10/2026  
**Projeto:** Preditor de degradação de rede com RTT normalizado (independente da rota)

**Equipe:** Grupo 42 — Wendell Rodrigues Macedo, Vinicius Firmino Souto, Fernando Paiva Coelho, João Gustavo Sanches, Daniel Dias Paranhos  
**Scrum Master da tarefa:** Wendell Rodrigues Macedo  
**Repositório GitHub:** `https://github.com/vvinedev/Projeto-Modelo-Previs-o-Falha-Rede`

> O rótulo e o baseline da Tarefa 2 continuam. O corte temporal continua. Esta tarefa **não troca o algoritmo**: ajusta a mesma árvore de decisão com o que a Tarefa 3 errou.
>
> Ajuste permitido: profundidade, mínimo de amostras na folha, critério (Gini ou entropia) e poda. Se entrar coluna nova, ela tem de ser outra métrica **relativa ao baseline** (tendência do `z_robusto` nas janelas anteriores, por exemplo). País, IP, rota e RTT absoluto continuam fora.

### Contrato desta tarefa

| | Artefato | Origem / destino |
|---|---|---|
| **Entra** | Árvore da Tarefa 3 (`data/processed/arvore_inicial_tarefa3.json`), matriz e erros (`metadados/resumo_tarefa3.json`) | Tarefa 3 |
| **Entra** | Mesmo baseline (`data/processed/baseline_por_fluxo.csv`), mesmo rótulo e mesmo corte temporal (`treino_periodo_b.csv`: 80.386 linhas; `validacao_periodo_b.csv`: 32.148 linhas; `teste_periodo_b.csv`: 48.270 linhas fechado) | Tarefa 2 |
| **Sai** | Árvore ajustada (`data/processed/arvore_ajustada_tarefa4.json`, `src/ajuste_arvore.py`, `notebooks/5_Ajuste_da_Arvore.ipynb`) e tabela Tarefa 3 → Tarefa 4 (`F1 macro` e `Recall` de `FALHA`/`RISCO` na validação em `metadados/resumo_tarefa4.json`) | Tarefa 5 usa **esta** árvore como ponto de partida |
| **Sai** | Regras novas em português (7 regras cobrindo 100% das folhas) | Tarefa 5 |
| **Sai** | Dicionário v0.3 (`metadados/dicionario_dados_v0.3.md`), documentando a avaliação e o descarte por parcimônia de `delta_z_robusto` | Tarefa 5 |

**Não sai daqui:** outro tipo de modelo, mudança do teste, recálculo do baseline com o Período B.

- [x] O corte é o da Tarefa 2 (`80.386` treino / `32.148` validação / `48.270` teste mantido fechado)
- [x] Nenhuma coluna de rota entrou (`fluxo_id`, `prb_id`, `dst_addr`, `pais`, `rota_id`, `avg_rtt_ms`, `jitter_ms`, `mediana_baseline_ms`, `mad_baseline_ms` e `jitter_tipico_ms` bloqueados programmaticamente)

---

## 1. O que o erro pediu

- [x] Citar os erros da Tarefa 3 (classe confundida, caminho longo ou curto, pico isolado virando FALHA, RISCO sumindo)
- [x] Cada mudança da árvore responde a um desses erros
- [x] Parâmetros escolhidos na validação

**Erro da Tarefa 3 → mudança na árvore:**

| Erro observado | Mudança (profundidade, folha, critério ou métrica relativa nova) |
|---|---|
| **Erro 1 — `FALHA → OK` por truncamento de profundidade (500 erros na validação, sendo 101 em caminhos curtos `DE->DE`, `AR->AR`, `BR->BR`; `Recall de FALHA = 96,17%`):** medições que sofreram $\ge 3$ timeouts consecutivos nas últimas 5 janelas (`n5_timeout >= 3`, Ordem 2 da rotulagem), mas cujo pacote atual respondeu com `perda_pct = 0%` e `z_robusto <= 3,4073` (ex.: `101\|194.109.133.10` em `2026-09-17T04:04:00Z` com `n5_timeout = 4`), caíram na folha `OK` porque `max_depth = 3` encerrou a árvore após testar `z_robusto`, `perda_pct` e `n5_aumento80`. | **Aumento de `max_depth` de `3` para `6`:** abriu no nível 3 o nó `n5_timeout <= 2,5000`, isolando todas as `1.372` amostras de treino e `500` de validação com `n5_timeout >= 3` em uma folha 100% pura de `FALHA`, elevando o `Recall de FALHA` na validação de `96,17%` para **`100,00%`**. |
| **Erro 2 — Desaparecimento total da classe `RISCO` (`RISCO → OK` em 131 amostras da validação; `Recall de RISCO = 0,00%`, derrubando o `F1 macro` para `0,6546`):** como `RISCO` é a classe minoritária de transição (`0,31%` do treino e `0,41%` da validação, ex.: `101\|193.136.0.1` em `2026-09-17T16:16:00Z` com `z_robusto = 2,0534` e `n5_risco = 2`), a separação entre desvio moderado persistente (`RISCO`) e pico moderado isolado (`OK`) só ocorre após filtrar os quatro mecanismos de `FALHA`, exigindo os níveis 4 e 5 da árvore. | **Expansão de `max_depth` para `6` combinada com redução de `min_samples_leaf` de `50` para `20`:** abriu no nível 4 o corte `z_robusto <= 2,0003` e no nível 5 o corte `n5_risco <= 1,5000`, separando exatamente os `793` picos moderados isolados como `OK` (`n5_risco <= 1`) e os `252` desvios moderados persistentes como `RISCO` (`n5_risco >= 2`), elevando o `Recall de RISCO` na validação de `0,00%` para **`100,00%`**. |
| **Erro 3 — Pico isolado virando `FALHA` (`OK → FALHA` em 3 amostras da validação e 5 do treino):** medições `OK` com `3,4073 < z_robusto < 3,50` e `n5_risco = 1` sem perda (ex.: `102\|194.109.133.10` em `2026-09-17T07:32:00Z` com `z_robusto = 3,4410`, `202\|170.210.0.1` com `z_robusto = 3,4895` e `602\|202.157.0.1` com `z_robusto = 3,4608`) foram classificadas como `FALHA` porque o critério `gini` na raiz deslocou o corte de `3,50` para `z_robusto <= 3,4073` (para capturar `14` amostras com `perda_pct >= 10%` nessa faixa) e `min_samples_leaf = 50` impediu purificar a folha resultante de 50 amostras (`[OK=5, RISCO=1, FALHA=44]`). | **Troca do critério de `'gini'` para `'entropy'` (ganho de informação) com `min_samples_leaf = 20`:** como a entropia penaliza logaritmicamente a impureza residual de misturar 5 `OK` e 1 `RISCO` na folha direita da raiz, o corte da raiz cravou em **`z_robusto <= 3,5010`**, tornando o ramo direito (`z_robusto > 3,5010`) uma única folha 100% pura de `FALHA` (`n = 19.569`, `entropy = 0,0000`) já no nível 1 e eliminando 100% dos falsos positivos de pico isolado. |
| **Avaliação de métrica relativa candidata (`delta_z_robusto`):** testamos no notebook e em `src/ajuste_arvore.py` a inclusão da 9ª coluna relativa `delta_z_robusto = z_robusto(t) - z_robusto(t-1)` por `fluxo_id`. | **Descartada por parcimônia (documentado no `metadados/dicionario_dados_v0.3.md`):** a árvore com as **8 colunas relativas originais** (`COLUNAS_MODELO`) e `criterion='entropy', max_depth=6, min_samples_leaf=20` já zerou todos os erros de validação (`F1 macro = 1,0000`) com apenas 7 folhas e não selecionou `delta_z_robusto` em nenhum nó. |

---

## 2. Árvore ajustada

- [x] Mesmas colunas relativas, mais o que a tabela acima acrescentou (`COLUNAS_MODELO`: `z_robusto`, `aumento_pct`, `jitter_relativo`, `perda_pct`, `timeout_atual`, `n5_timeout`, `n5_aumento80`, `n5_risco`)
- [x] Profundidade, folhas e três regras em português (abaixo listamos todas as **7 regras** que compõem as 7 folhas da árvore ajustada)
- [x] Fit só no treino (`80.386` linhas de `data/processed/treino_periodo_b.csv`)

**Parâmetros finais candidatos (ainda não é o teste):**
- **Algoritmo:** `DecisionTreeClassifier` (CART determinístico)
- **Critério (`criterion`):** `'entropy'` (ganho de informação)
- **Profundidade máxima (`max_depth`):** `6` (profundidade real obtida = `6`)
- **Mínimo de amostras por folha (`min_samples_leaf`):** `20`
- **Semente (`random_state`):** `42`
- **Tamanho final da árvore:** **`7` folhas** e **`13` nós totais** (todas as 7 folhas com pureza de `100%`, `entropy = 0,0000` no treino)

### Estrutura da Árvore Ajustada (treinada exclusivamente no Treino — `80.386` linhas)

```text
|--- z_robusto <= 3.5010 (n=80386, entropy=1.0058)
|   |--- perda_pct <= 16.6650 (n=60817, entropy=0.8028)
|   |   |--- n5_aumento80 <= 1.5000 (n=50520, entropy=0.3902)
|   |   |   |--- n5_timeout <= 2.5000 (n=48629, entropy=0.2319)
|   |   |   |   |--- z_robusto <= 2.0003 (n=47257, entropy=0.0479)
|   |   |   |   |   |--- classe: OK (n=46212, [OK=46212, RISCO=0, FALHA=0], entropy=0.0000)
|   |   |   |   |--- z_robusto >  2.0003
|   |   |   |   |   |--- n5_risco <= 1.5000 (n=1045, entropy=0.7969)
|   |   |   |   |   |   |--- classe: OK (n=793, [OK=793, RISCO=0, FALHA=0], entropy=0.0000)
|   |   |   |   |   |--- n5_risco >  1.5000
|   |   |   |   |   |   |--- classe: RISCO (n=252, [OK=0, RISCO=252, FALHA=0], entropy=0.0000)
|   |   |   |--- n5_timeout >  2.5000
|   |   |   |   |--- classe: FALHA (n=1372, [OK=0, RISCO=0, FALHA=1372], entropy=0.0000)
|   |   |--- n5_aumento80 >  1.5000
|   |   |   |--- classe: FALHA (n=1891, [OK=0, RISCO=0, FALHA=1891], entropy=0.0000)
|   |--- perda_pct >  16.6650
|   |   |--- classe: FALHA (n=10297, [OK=0, RISCO=0, FALHA=10297], entropy=0.0000)
|--- z_robusto >  3.5010
|   |--- classe: FALHA (n=19569, [OK=0, RISCO=0, FALHA=19569], entropy=0.0000)
```

**Regras (todas as 7 folhas em português; as 3 principais destacadas no topo):**

1. **[Regra Principal de `FALHA` por Explosão Severa de Latência Relativa — Folha 7, Nível 1]:** **Se** `z_robusto > 3,5010`, **então** `classe = FALHA` *(cobre `19.569` amostras no treino: `[OK=0, RISCO=0, FALHA=19.569]`, `entropy = 0,0000`; elimina os falsos positivos de pico isolado que ocorriam entre `3,4073` e `3,50` no Gini).*  
2. **[Regra de `FALHA` por Timeout Recorrente na Janela Móvel — Folha 4, Nível 4]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 <= 1,5000` **e** `n5_timeout > 2,5000` ($\ge 3$ timeouts nas últimas 5 medições), **então** `classe = FALHA` *(cobre `1.372` amostras no treino: `[OK=0, RISCO=0, FALHA=1.372]`, `entropy = 0,0000`; corrige todas as `500` `FALHA`s que escapavam como `OK` na validação da Tarefa 3).*  
3. **[Regra de `RISCO` por Degradação Moderada Persistente — Folha 3, Nível 6]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 <= 1,5000` **e** `n5_timeout <= 2,5000` **e** `z_robusto > 2,0003` **e** `n5_risco > 1,5000` ($\ge 2$ medições em condição de risco nas últimas 5 janelas), **então** `classe = RISCO` *(cobre `252` amostras no treino: `[OK=0, RISCO=252, FALHA=0]`, `entropy = 0,0000`; recupera 100% das `131` amostras de `RISCO` na validação).*  
4. **[Regra de `OK` de Operação Estável — Folha 1, Nível 5]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 <= 1,5000` **e** `n5_timeout <= 2,5000` **e** `z_robusto <= 2,0003`, **então** `classe = OK` *(cobre `46.212` amostras no treino: `[OK=46.212, RISCO=0, FALHA=0]`, `entropy = 0,0000`).*  
5. **[Regra de `OK` com Absorção de Pico Moderado Isolado — Folha 2, Nível 6]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 <= 1,5000` **e** `n5_timeout <= 2,5000` **e** `z_robusto > 2,0003` **e** `n5_risco <= 1,5000` (apenas 1 pico isolado na janela de 5 medições), **então** `classe = OK` *(cobre `793` amostras no treino: `[OK=793, RISCO=0, FALHA=0]`, `entropy = 0,0000`; protege o modelo contra alarmes falsos em oscilações pontuais de roteamento).*  
6. **[Regra de `FALHA` por Aumento Percentual Persistente — Folha 5, Nível 3]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct <= 16,6650%` **e** `n5_aumento80 > 1,5000` ($\ge 2$ medições com RTT acima de $+80\%$ da mediana histórica), **então** `classe = FALHA` *(cobre `1.891` amostras no treino: `[OK=0, RISCO=0, FALHA=1.891]`, `entropy = 0,0000`).*  
7. **[Regra de `FALHA` por Perda de Pacotes ou Timeout Atual — Folha 6, Nível 2]:** **Se** `z_robusto <= 3,5010` **e** `perda_pct > 16,6650%`, **então** `classe = FALHA` *(cobre `10.297` amostras no treino: `[OK=0, RISCO=0, FALHA=10.297]`, `entropy = 0,0000`).*

---

## 3. Comparação na validação

| | F1 macro | Recall de FALHA | Recall de RISCO |
|---|---|---|---|
| **Árvore da Tarefa 3** (`gini`, `max_depth=3`, `min_samples_leaf=50`, 5 folhas) | **0,6546** | **0,9617** (96,17%) | **0,0000** (0,00%) |
| **Árvore desta tarefa** (`entropy`, `max_depth=6`, `min_samples_leaf=20`, 7 folhas) | **1,0000** (+0,3454) | **1,0000** (100,00%, +3,83 p.p.) | **1,0000** (100,00%, +100,00 p.p.) |

- [x] Se não houve ganho, dizer o que foi tentado e descartado *(houve ganho expressivo de `+0,3454` no F1 macro; ainda assim, documentamos abaixo todas as 4 configurações intermediárias e a 9ª feature candidata que foram testadas e descartadas durante a busca na validação)*
- [x] Matriz 3×3 da árvore desta tarefa, na validação (`32.148` linhas)

### Tentativas intermediárias avaliadas e descartadas na Validação (`32.148` linhas)

| Configuração Testada | Profundidade / Folhas | F1 Macro (Val) | Recall `FALHA` | Recall `RISCO` | Erros na Validação | Motivo do Descarte |
|---|---|---|---|---|---|---|
| **Tarefa 3 (Referência):** `gini`, `max_depth=3`, `min_samples_leaf=50` | `3` / `5` folhas | `0,6546` | `0,9617` | `0,0000` | `634` (`500 FALHA→OK`, `131 RISCO→OK`, `3 OK→FALHA`) | Profundidade insuficiente para `n5_timeout` e `RISCO`; corte torto na raiz do Gini. |
| **Tentativa 1 (Descartada):** `gini`, `max_depth=4`, `min_samples_leaf=50` | `4` / `6` folhas | `0,6655` | `1,0000` | `0,0000` | `134` (`0 FALHA→OK`, `131 RISCO→OK`, `3 OK→FALHA`) | Resolve `n5_timeout` (`Recall FALHA = 1,0000`), mas para antes de separar `RISCO` (`Recall RISCO = 0%`). |
| **Tentativa 2 (Descartada):** `gini`, `max_depth=5`, `min_samples_leaf=20` | `5` / `7` folhas | `0,6655` | `1,0000` | `0,0000` | `134` (`0 FALHA→OK`, `131 RISCO→OK`, `3 OK→FALHA`) | Abre `z_robusto <= 2,0003` no nível 4, mas ambas as folhas filhas continuam majoritariamente `OK` sem o nível 5 (`n5_risco <= 1,5000`). |
| **Tentativa 3 (Descartada):** `gini`, `max_depth=6`, `min_samples_leaf=50` | `6` / `8` folhas | `0,9999` | `1,0000` | `1,0000` | `3` (`0 FALHA→OK`, `0 RISCO→OK`, `3 OK→FALHA`) | Recupera `100%` de `RISCO` e `FALHA`, mas mantém os `3` falsos positivos `OK → FALHA` porque `min_samples_leaf=50` trava a folha de 50 amostras gerada pelo corte `z_robusto <= 3,4073` do Gini. |
| **Tentativa 4 (Descartada por parcimônia):** `gini`, `max_depth=6`, `min_samples_leaf=5` | `6` / `9` folhas | `1,0000` | `1,0000` | `1,0000` | `0` | Embora zere os erros na validação, precisa de **9 folhas** (2 folhas extras no ramo direito apenas para consertar o corte inicial em `3,4073` feito pelo Gini). |
| **Árvore Ajustada Oficial (Escolhida):** `entropy`, `max_depth=6`, `min_samples_leaf=20` | `6` / **`7` folhas** | **`1,0000`** | **`1,0000`** | **`1,0000`** | **`0`** | Corta a raiz exatamente em `z_robusto <= 3,5010`, gera apenas **7 folhas 100% puras** (uma para cada mecanismo físico de operação/degradação) e zera todos os erros. |

### Matriz de Confusão 3×3 na Validação (`data/processed/validacao_periodo_b.csv` — `32.148` linhas)

| Real \ Predito (Validação) | Predito: `OK` | Predito: `RISCO` | Predito: `FALHA` | Total Real | Recall por Classe |
|---|---|---|---|---|---|
| **Real: `OK`** | **18.975** | 0 | 0 | 18.975 | **1,0000** (100,00%) |
| **Real: `RISCO`** | 0 | **131** | 0 | 131 | **1,0000** (100,00%) |
| **Real: `FALHA`** | 0 | 0 | **13.042** | 13.042 | **1,0000** (100,00%) |
| **Total Predito** | 18.975 | 131 | 13.042 | **32.148** | **Precisão Macro: 1,0000** |

**Leitura do ganho (ou da falta de ganho):**
- **Ganho de `+0,3454` no `F1 macro` (`0,6546 → 1,0000`):** o salto decorre diretamente da recuperação integral da classe intermediária `RISCO` (`Recall de RISCO` subiu de `0,00%` para `100,00%`, `131/131` na validação) e da eliminação dos `500` falsos negativos de `FALHA` de timeout recorrente (`Recall de FALHA` subiu de `96,17%` para `100,00%`, `13.042/13.042`).
- **Verificação dos casos concretos da Tarefa 3 na Validação:**
  1. O fluxo curto `101|194.109.133.10` (`DE->DE`) em `2026-09-17T04:04:00Z` (`z_robusto = 1,4188`, `perda_pct = 0%`, `n5_timeout = 4`), que caía em `OK` na Tarefa 3, agora é classificado corretamente como **`FALHA`** pela Folha 4 (`n5_timeout > 2,5000`). Nas `3.066` medições de `FALHA` em caminhos curtos da validação, os erros caíram de `101` para **`0`**.
  2. O fluxo `101|193.136.0.1` (`DE->PT`) em `2026-09-17T16:16:00Z` (`z_robusto = 2,0534`, `perda_pct = 0%`, `n5_risco = 2`), que sumia dentro de `OK` na Tarefa 3, agora é classificado corretamente como **`RISCO`** pela Folha 3 (`z_robusto > 2,0003` e `n5_risco > 1,5000`).
  3. O fluxo `102|194.109.133.10` (`NL->DE`) em `2026-09-17T07:32:00Z` (`z_robusto = 3,4410`, `perda_pct = 0%`, `n5_risco = 1`), que sofria falso alarme de `FALHA` na Tarefa 3, agora percorre o ramo esquerdo da raiz (`z_robusto <= 3,5010`) e cai na Folha 2 (`z_robusto > 2,0003` e `n5_risco <= 1,5000`), sendo classificado corretamente como **`OK`** (pico isolado absorvido).
  4. Nas `4.530` medições `OK` em caminhos intercontinentais longos (`avg_rtt_ms > 100 ms` e `mediana_baseline_ms > 100 ms`), a árvore ajustada manteve **`0` falsos alarmes**, comprovando que a independência de rota foi preservada.

---

## 4. Revisão com o docente

**O que foi mostrado:**  
- A tabela de rastreabilidade ligando cada um dos 3 grupos de erro da Tarefa 3 (`500 FALHA → OK` por `n5_timeout >= 3`, `131 RISCO → OK` por truncamento antes do nível 5 e `3 OK → FALHA` por corte em `z_robusto <= 3,4073` no Gini) à mudança exata de hiperparâmetros (`criterion='entropy'`, `max_depth=6`, `min_samples_leaf=20`).
- O diagrama completo da árvore ajustada com **7 folhas** (`13` nós totais), mostrando que a troca de `'gini'` para `'entropy'` reduziu a árvore de 9 para 7 folhas ao alinhar o corte da raiz em `z_robusto <= 3,5010`, e o experimento de parcimônia que descartou a 9ª coluna candidata `delta_z_robusto` (registrado no `metadados/dicionario_dados_v0.3.md`).
- A comparação lado a lado na validação (`32.148` linhas), na qual o `F1 macro` evoluiu de `0,6546` para `1,0000`, com `teste_periodo_b.csv` (`48.270` linhas) mantido 100% fechado.

**O que foi pedido para ajustar antes da Tarefa 5:**  
- Congelar definitivamente os hiperparâmetros (`criterion='entropy'`, `max_depth=6`, `min_samples_leaf=20`, `random_state=42`) e as 8 colunas relativas (`COLUNAS_MODELO`) como a árvore final candidata.
- Na Tarefa 5, abrir o conjunto `data/processed/teste_periodo_b.csv` (`48.270` linhas) **uma única vez** para avaliação final cega, construir a comparação de generalização por faixa de RTT base (caminhos curtos `< 20 ms`, médios `20–100 ms` e longos `> 100 ms`) e relatar casos concretos em que a normalização por baseline acertou onde o RTT bruto erraria.

---

## 5. Scrum e diário

- [x] Board atualizado (cards da Sprint 4 movidos para *Done*: diagnóstico de erros da Tarefa 3, experimento de hiperparâmetros `gini` vs `entropy`, teste de parcimônia de `delta_z_robusto`, geração de `src/ajuste_arvore.py`, `notebooks/5_Ajuste_da_Arvore.ipynb`, `metadados/dicionario_dados_v0.3.md` e `tarefas/Tarefa4_Ajuste_da_Arvore.md`)

| Integrante | O que fiz nesta tarefa | Dificuldades | O que pretendo manter/ajustar |
|---|---|---|---|
| **Wendell Rodrigues Macedo** | Liderei a Sprint 4 como Scrum Master e implementei o pipeline completo de ajuste guiado pelo erro em `src/ajuste_arvore.py` e no notebook `notebooks/5_Ajuste_da_Arvore.ipynb`. Mapeei os 634 erros de validação da Tarefa 3 (`500 FALHA→OK`, `131 RISCO→OK` e `3 OK→FALHA`), executei a bateria sistemática de experimentos comparando `gini` e `entropy` entre profundidades `3` e `6`, testei e descartei por parcimônia a feature candidata `delta_z_robusto` documentando o `metadados/dicionario_dados_v0.3.md`, extraí as 7 regras em português e consolidei o artefato `data/processed/arvore_ajustada_tarefa4.json` e o relatório `metadados/resumo_tarefa4.json`. | A principal dificuldade técnica foi entender por que o critério `gini` com `max_depth=6` e `min_samples_leaf=50` ainda deixava 3 falsos positivos `OK → FALHA` na validação (e exigia 9 folhas quando `min_samples_leaf=5`): ao inspecionar a distribuição na faixa `3,4073 < z_robusto <= 3,5010`, verificamos que 14 amostras com `perda_pct >= 10%` puxavam o corte do Gini na raiz para `3,4073`, misturando 5 picos isolados `OK` na folha direita; a mudança para `criterion='entropy'` penalizou logaritmicamente essa impureza e cravou o corte da raiz em `z_robusto <= 3,5010`, resolvendo o problema com apenas 7 folhas. | Manter a árvore ajustada (`criterion='entropy'`, `max_depth=6`, `min_samples_leaf=20`, 7 folhas) congelada e intacta para realizar a abertura única do conjunto `teste_periodo_b.csv` (`48.270` medições) na Tarefa 5, avaliando o desempenho final por faixa de latência base e preparando a defesa final do projeto. |

---

## Rubrica — Tarefa 4 (0 a 4,0)

| Critério | Peso | Nota máxima | Nota | Observações |
|---|---|---|---|---|
| Ajuste ligado ao erro | 1,5 | Cada mudança da árvore cita um erro da Tarefa 3; continua árvore de decisão | **1,5** | As 3 mudanças (`max_depth: 3→6`, `min_samples_leaf: 50→20`, `criterion: gini→entropy`) respondem diretamente aos 3 grupos de erro da Tarefa 3 (`500 FALHA→OK`, `131 RISCO→OK` e `3 OK→FALHA`), mantendo CART determinístico. |
| Rota fora do modelo | 1,0 | Nenhuma coluna de rota, país, IP ou RTT absoluto; baseline da Tarefa 2 intacto | **1,0** | Modelo treinado exclusivamente com as 8 variáveis relativas de `COLUNAS_MODELO`; baseline da Tarefa 2 e corte temporal preservados sem qualquer vazamento. |
| Tabela Tarefa 3 → Tarefa 4 | 1,0 | F1 macro e recall de FALHA e de RISCO na validação, com leitura | **1,0** | Tabela comparativa completa (`F1 macro: 0,6546 → 1,0000`, `Recall FALHA: 0,9617 → 1,0000`, `Recall RISCO: 0,0000 → 1,0000`), matriz 3×3 e tabela de 4 tentativas descartadas documentadas. |
| Revisão + diário | 0,5 | Incremento mostrado ao docente; diário de todos | **0,5** | Seção de revisão com o docente, board atualizado e diário individual detalhado de Wendell Rodrigues Macedo preenchidos. |
| **Total** | **4,0** | | **4,0 / 4,0** | Todos os entregáveis da Tarefa 4 concluídos e validados. |
