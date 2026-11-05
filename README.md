# Preditor de Degradação de Rede com RTT Normalizado — Árvore de Decisão (CART), Random Forest e XGBoost

> **Projeto Interdisciplinar — Estrutura de Dados II**  
> **Orientadora:** Profa. Dra. Andréa Ono Sakai  
> **Autores:** Wendell Rodrigues Macedo, Vinicius Firmino Souto, Fernando Paiva Coelho, Joao Gustavo Sanches e Daniel Dias Paranhos  
> **Licença:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)

---

## 🌐 Artigo Técnico Publicado (Página Web)

- **URL pública (GitHub Pages):** [https://vini-wine-coder.github.io/Projeto-Modelo-Previs-o-Falha-Rede/](https://vvinedev.github.io/Projeto-Modelo-Previs-o-Falha-Rede/)
- **Arquivo principal da página:** [`index.html`](index.html) (estilizado em [`styles/artigo.css`](styles/artigo.css) com diagramas vetoriais autorais em [`images/`](images/))
- **Quadro de observação de referências (Passo 1 do artigo):** [`metadados/quadro_observacao_artigo.md`](metadados/quadro_observacao_artigo.md)

Para visualizar o artigo localmente no navegador sem servidor adicional:

```bash
xdg-open index.html
# ou sirva via HTTP local:
python3 -m http.server 8000
```

---

## 📊 Resumo Executivo do Experimento Comparativo

Avaliamos **Árvore de Decisão (CART)**, **Random Forest (Bagging)** e **XGBoost (Gradient Boosting)** na detecção multiclasse (`OK`, `RISCO`, `FALHA`) de degradação de rotas de Internet com RTT normalizado por baseline da própria rota (`z_robusto`), utilizando **96.519 janelas reais** da API pública do **RIPE Atlas** (`k-root DNS`, Measurement ID `#10301`) com corte temporal estrito:

- **Treino (Período A):** `2026-03-01` a `2026-03-07` (`48.249` janelas)
- **Teste (Período B):** `2026-03-08` a `2026-03-14` (`48.270` janelas: `28.303 OK`, `189 RISCO`, `19.778 FALHA`)

| Modelo | Hiperparâmetros Principais | Accuracy | Precision (Macro) | Recall (Macro) | Recall `FALHA` | Recall `RISCO` | F1 (Macro) | Treino (ms) | Inferência / Amostra (µs) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Árvore de Decisão (CART — 7 folhas)** | `criterion='entropy', max_depth=6, min_samples_leaf=20, random_state=42` | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **844.61** | **0.1765 µs (1.0x)** |
| **Random Forest (Bagging — 15 árvores)** | `n_estimators=15, max_depth=6, max_features=5, min_samples_leaf=20, random_state=42` | 0.9967 | 0.9882 | 0.7178 | 1.0000 | 0.1534 | 0.7544 | 18,779.15 | 4.7970 µs (27.2x) |
| **XGBoost (Gradient Boosting — 36 árvores)** | `n_estimators=12, max_depth=6, learning_rate=0.35, reg_lambda=1.0, gamma=0.1, seed=42` | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | 52,649.35 | 7.4960 µs (42.5x) |

**Decisão Técnica:** Recomendamos a **Árvore de Decisão (CART) podada de 7 folhas** para operação em produção no NOC. Ela empata em desempenho preditivo máximo (`F1 Macro = 1.0000`) com o XGBoost, supera amplamente a Random Forest (`F1 Macro = 0.7544`, penalizada pela diluição da classe rara `RISCO` na amostragem de atributos `max_features=5`), é **42,5 vezes mais rápida em inferência** (`0.18 µs` vs `7.50 µs` por amostra) e mantém **100% de transparência caixa-branca** (7 regras explícitas em português auditáveis pelo engenheiro de plantão).

---

## ⚙️ Como Reproduzir o Experimento Passo a Passo

### 1. Pré-requisitos e Ambiente Python

- **Python:** `>= 3.12` (validado em Python `3.12` / `3.14`)
- **Pacotes e versões de referência ([`requirements.txt`](requirements.txt)):**
  - `scikit-learn==1.5.2`
  - `xgboost==2.1.2`
  - `pandas==2.2.3`
  - `numpy==2.1.2`
  - `matplotlib==3.9.2`
  - `jupyter==1.1.1`

> **Nota sobre execução determinística:** Os scripts em `src/` foram implementados também com suporte nativo à biblioteca padrão do Python (`csv`, `math`, `random`, `json`) com `SEED = 42`, permitindo reproduzir 100% das métricas, matrizes de confusão e JSONs de saída mesmo em ambientes minimalistas sem dependências externas, além de fornecer o código equivalente em `scikit-learn` e `xgboost` no artigo e nos notebooks.

### 2. Instalação (Opcional, para ambiente virtual completo)

```bash
git clone https://github.com/vini-wine-coder/Projeto-Modelo-Previs-o-Falha-Rede.git
cd Projeto-Modelo-Previs-o-Falha-Rede
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Onde Estão os Dados

Todos os arquivos de dados processados e auditados já estão versionados no repositório em [`data/processed/`](data/processed/):

- [`data/processed/dataset_processado_v0.2.csv`](data/processed/dataset_processado_v0.2.csv) — Dataset consolidado completo (`96.519` janelas de 5 min, 20 probes globais RIPE Atlas).
- [`data/processed/treino_periodo_a.csv`](data/processed/treino_periodo_a.csv) — Conjunto de Treino (`48.249` janelas, `2026-03-01` a `2026-03-07`).
- [`data/processed/teste_periodo_b.csv`](data/processed/teste_periodo_b.csv) — Conjunto de Teste temporalmente disjunto (`48.270` janelas, `2026-03-08` a `2026-03-14`).
- [`metadados/dicionario_dados_v0.4.md`](metadados/dicionario_dados_v0.4.md) — Dicionário de dados completo com unidades, tipos e regras da variável-alvo.

### 4. Comandos para Executar o Pipeline e o Experimento do Artigo

```bash
# Tarefa 3 — Primeiras árvores de decisão (rasas max_depth=3 e livres)
python3 src/primeiras_arvores.py

# Tarefa 4 — Ajuste da árvore (poda por profundidade, min_samples_leaf e seleção de atributos)
python3 src/ajuste_arvore.py

# Tarefa 5 — Árvore Final escolhida (7 folhas, regras em português e importância MDI)
python3 src/arvore_final.py

# Artigo Técnico — Experimento comparativo: Árvore de Decisão vs Random Forest vs XGBoost
python3 src/experimento_artigo.py
```

O script [`src/experimento_artigo.py`](src/experimento_artigo.py) imprime no terminal a tabela comparativa completa, as matrizes de confusão 3×3 e salva todas as métricas auditáveis em [`metadados/resumo_artigo_comparativo.json`](metadados/resumo_artigo_comparativo.json).

---

## 📁 Estrutura do Repositório

```text
├── index.html                                         # Página web pública do artigo técnico (tema dark minimalista)
├── styles/
│   └── artigo.css                                     # Folha de estilos CSS (pitch-black #000000, Plus Jakarta Sans + JetBrains Mono)
├── images/
│   ├── diagrama_arvore_7folhas.svg                    # Diagrama vetorial completo da árvore CART de 7 folhas
│   ├── esquema_bagging_vs_boosting.svg                # Esquema conceitual Bagging (Random Forest) vs Boosting (XGBoost)
│   ├── grafico_metricas_tempos.svg                    # Gráfico comparativo de F1 Macro, Recall RISCO e latência de inferência
│   └── avatar_*.svg                                   # Avatares vetoriais dos 5 autores
├── src/
│   ├── preparar_dados.py                              # Tarefa 2: Limpeza, normalização por rota (z_robusto) e split temporal
│   ├── primeiras_arvores.py                           # Tarefa 3: Árvore rasa vs árvore livre (Gini e Entropia)
│   ├── ajuste_arvore.py                               # Tarefa 4: Varredura de max_depth, min_samples_leaf e subconjuntos de features
│   ├── arvore_final.py                                # Tarefa 5: Árvore final (7 folhas), regras operacionais e importância MDI
│   └── experimento_artigo.py                          # Artigo: Comparação Árvore de Decisão vs Random Forest vs XGBoost
├── notebooks/
│   ├── 1_Coleta_RIPE_Atlas.ipynb                      # Tarefa 1: Coleta via REST API v2 do RIPE Atlas
│   ├── 2_Preparacao_e_Auditoria_Dados.ipynb           # Tarefa 2: Preparação e auditoria sem vazamento temporal
│   ├── 4_Primeiras_Arvores.ipynb                      # Tarefa 3: Experimento das primeiras árvores
│   ├── 5_Ajuste_da_Arvore.ipynb                       # Tarefa 4: Experimento de poda e seleção de atributos
│   ├── 6_Arvore_Final.ipynb                           # Tarefa 5: Documentação executável da Árvore Final
│   └── 7_Experimento_Artigo_Arvore_RF_XGBoost.ipynb   # Artigo: Notebook executável comparando os 3 algoritmos
├── tarefas/
│   ├── Tarefa3_Primeiras_Arvores.md                   # Relatório da Tarefa 3
│   ├── Tarefa4_Ajuste_da_Arvore.md                    # Relatório da Tarefa 4
│   └── Tarefa5_Arvore_Final.md                        # Relatório da Tarefa 5
├── metadados/
│   ├── dicionario_dados_v0.4.md                       # Dicionário de dados atualizado até a Tarefa 5
│   ├── quadro_observacao_artigo.md                    # Quadro de observação das 2 referências do artigo técnico
│   ├── resumo_tarefa3.json                            # Métricas da Tarefa 3
│   ├── resumo_tarefa4.json                            # Métricas da Tarefa 4
│   ├── resumo_tarefa5.json                            # Métricas da Tarefa 5
│   └── resumo_artigo_comparativo.json                 # Métricas do comparativo CART vs Random Forest vs XGBoost
└── requirements.txt                                   # Pacotes e versões de referência
```

---

## 📚 Créditos de Imagens, Dados e Referências Bibliográficas

- **Figuras e Diagramas (`images/*.svg`):** Produzidos originalmente pelos autores do grupo para este artigo técnico e licenciados sob **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
- **Dados de Medição de Rede:** Coletados da API pública do **RIPE Atlas** (RIPE NCC — Measurement ID `#10301`, probes globais monitorando `k.root-servers.net`), utilizados conforme os termos abertos de pesquisa da plataforma RIPE Atlas.
- **Referências Bibliográficas do Artigo:**
  1. BREIMAN, L.; FRIEDMAN, J.; STONE, C. J.; OLSHEN, R. A. *Classification and Regression Trees*. Boca Raton: Chapman & Hall/CRC, 1984.
  2. BREIMAN, L. Random Forests. *Machine Learning*, v. 45, n. 1, p. 5–32, 2001.
  3. CHEN, T.; GUESTRIN, C. XGBoost: A Scalable Tree Boosting System. In: *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '16)*, p. 785–794, 2016.
  4. ACTIVESTATE. *Decision Tree vs. Random Forest vs. XGBoost: Key Differences*. ActiveState Blog, 2022.
  5. RIPE NCC. *RIPE Atlas REST API v2 Documentation*. Disponível em: <https://atlas.ripe.net/docs/apis/>.

---

# Memorando de Decisão — Fonte de Dados do Projeto (Etapa Inicial)

| Campo | Informação |
|---|---|
| Curso / Disciplina | Ciência da Computação |
| Projeto integrador | Preditor de Falha e Risco em Dispositivos de Rede |
| Orientador(a) | Andrea Ono Sakai |
| Data de entrega desta etapa | 08/09/2026 |
| Integrantes do grupo | Wendell Rodrigues Macedo, Vinicius Firmino Souto, Fernando Paiva Coelho, Joao Gustavo Sanches, Daniel Dias Paranhos |

---

## 1. Situação

A equipe precisa decidir se a próxima fase do projeto utilizará um dataset real já publicado ou a API do RIPE Atlas como fonte de dados, garantindo que sejam obtidas as métricas de latência, perda de pacotes e jitter necessárias para treinar, testar e validar o modelo de predição de falhas da rede.

## 2. Opção A — Dataset real

- **Origem / link:** Base de dados do SIMET — Sistema de Medição de Tráfego Internet, desenvolvido e mantido pelo NIC.br (Núcleo de Informação e Coordenação do Ponto BR). O portal disponibiliza bases de medições Web e Mobile para download.
- **Formato:** Os dados são disponibilizados em arquivos CSV, incluindo uma base das medições Web, uma base Mobile e um arquivo de dicionário dos dados.
- **Período coberto:** O portal do NIC.br utiliza, em suas visualizações públicas, informações dos últimos seis meses, reunindo mais de 5 milhões de medições realizadas pelo SIMET. A página de download não informa explicitamente o período histórico total existente dentro dos arquivos CSV.
- **Campos disponíveis:** As medições armazenam informações como horário da medição, operadora, tipo de dispositivo, localização aproximada, velocidade de download, latência, perda de pacotes e jitter. Essas três últimas métricas são diretamente compatíveis com os atributos necessários pelo projeto.
- **Licença de uso:** A página de disponibilização dos dados informa que o conteúdo do portal está sob licença Creative Commons Atribuição-CompartilhaIgual 4.0 Internacional (CC BY-SA 4.0), salvo quando houver restrições adicionais indicadas.

**Resumo do que foi encontrado:**
O SIMET é uma alternativa brasileira consolidada para obtenção de dados reais de qualidade de Internet, mantido e desenvolvido pelo NIC.br, fornecendo datasets estruturados com as variáveis exigidas pelo projeto.

## 3. Opção B — API do RIPE Atlas

- **Documentação consultada (link):** Documentação oficial da RIPE Atlas REST API v2.
- **Autenticação exigida:** Para criar novas medições, é necessário utilizar uma API Key com permissão para criação de medições, normalmente enviada no cabeçalho `Authorization`. Já a consulta de medições e resultados públicos pode ser feita sem autenticação.
- **Como se cria uma medição:** Uma medição é criada enviando uma requisição POST para `https://atlas.ripe.net/api/v2/measurements/`. No corpo da requisição são informados, em JSON, o tipo da medição (por exemplo, ping), o destino, a versão de IP, os probes que realizarão a medição e, opcionalmente, o período e a frequência da coleta.
- **Como se consultam os resultados:** Os resultados podem ser consultados por meio de uma requisição GET para `https://atlas.ripe.net/api/v2/measurements/{id}/results/`, substituindo `{id}` pelo identificador da medição. Também é possível filtrar os resultados por probes e por período de tempo. Medições públicas podem ser consultadas sem autenticação.

**Resumo do que foi encontrado:**
A API do RIPE Atlas permite criar medições de rede sob demanda usando probes distribuídos mundialmente. Para o projeto, pode ser criada uma medição do tipo ping, permitindo coletar dados reais de latência e perda de pacotes diretamente via API REST.

## 4. Comparação

| Critério | Opção A — Dataset real | Opção B — API RIPE Atlas |
|---|---|---|
| Controle sobre a coleta | Baixo — os dados já foram coletados e não é possível definir exatamente como cada medição foi realizada. | Alto — permite escolher o destino, os probes, o tipo de medição e a frequência da coleta. |
| Diversidade geográfica | Boa dentro do Brasil — o SIMET possui medições realizadas em diferentes regiões brasileiras. | Muito alta — possui probes distribuídos em diversos países e regiões do mundo. |
| Custo / complexidade de implementação | Baixo — basta baixar os dados em CSV, tratar e adaptar ao formato do projeto. | Médio — exige integração com a API, autenticação, configuração das medições e tratamento das respostas. |
| Tempo até os primeiros dados estarem disponíveis | Imediato — os dados já estão disponíveis para download e análise. | Maior — é necessário configurar a medição e aguardar a coleta e disponibilização dos resultados. |

## 5. Recomendação

Opção A — Dataset real do SIMET, por oferecer dados já disponíveis, com menor complexidade de implementação.

## 6. Justificativa

O dataset real do SIMET é a opção mais adequada porque os dados já estão prontamente disponíveis para uso, possuem métricas diretamente compatíveis com o projeto (latência, perda de pacotes e jitter) e exigem menor esforço de implementação. Em comparação, a API do RIPE Atlas oferece maior controle e diversidade geográfica, porém exige autenticação, configuração das medições e integração via API, aumentando a complexidade técnica e o tempo até a obtenção dos primeiros dados. Portanto, para esta etapa do projeto, o dataset do SIMET apresenta a melhor relação entre disponibilidade, facilidade de uso e compatibilidade com o modelo preditivo.

## 7. Riscos e limitações

O principal risco da opção escolhida é que a equipe não possui controle direto sobre a frequência e o método com que os dados foram coletados originalmente. Além disso, pode ser necessário tratar valores ausentes, filtrar registros ruidosos e adaptar os campos ao formato de schema exigido pelo projeto. Para mitigar esses riscos, o grupo realizará uma etapa prévia de limpeza e validação dos dados, selecionando apenas registros válidos contendo latência, perda de pacotes e jitter, convertendo o dataset para o padrão exigido pelo contrato de dados do projeto.

## 8. Contribuição Individual dos Integrantes

### Integrante 1 — Wendell Rodrigues Macedo
- **O que fez nesta etapa:** Pesquisei informações sobre o dataset real do SIMET, verificando as métricas disponíveis, como latência, perda de pacotes e jitter. Também analisei a compatibilidade desses dados com as necessidades do projeto e apresentei os principais pontos encontrados ao grupo.
- **Tempo dedicado (aprox.):** 2h30
- **Evidência da contribuição:** *(prints de conversas no grupo e histórico de commits no repositório)*

### Integrante 2 — Vinicius Firmino Souto
- **O que fez nesta etapa:** Pesquisei a documentação da API do RIPE Atlas, analisando como funciona a autenticação, a criação de medições e a consulta dos resultados. Também comparei a complexidade da API com a utilização de um dataset já disponível.
- **Tempo dedicado (aprox.):** 2h30
- **Evidência da contribuição:** *(prints de conversas no grupo e anotações técnicas compartilhadas)*

### Integrante 3 — Fernando Paiva Coelho
- **O que fez nesta etapa:** Realizei a comparação entre o dataset do SIMET e a API do RIPE Atlas considerando controle sobre a coleta, diversidade geográfica, complexidade de implementação e tempo para obtenção dos dados. Também participei da elaboração da recomendação e da justificativa final do memorando.
- **Tempo dedicado (aprox.):** 3h00
- **Evidência da contribuição:** *(documento compartilhado de rascunho e registros de reuniões do grupo)*

### Integrante 4 — Joao Gustavo Sanches
- **O que fez nesta etapa:** Analisei os riscos e limitações relacionados ao uso do dataset real do SIMET, identificando possíveis problemas como falta de controle sobre a coleta, necessidade de limpeza dos dados e adaptação dos campos ao formato definido pelo projeto. Também sugeri formas de reduzir esses riscos.
- **Tempo dedicado (aprox.):** 2h00
- **Evidência da contribuição:** *(registros de mensagens no grupo e trechos de análise de mitigação)*

### Integrante 5 — Daniel Dias Paranhos
- **O que fez nesta etapa:** Revisei as informações pesquisadas pelo grupo, conferi o preenchimento das seções do memorando e organizei as fontes utilizadas. Também revisei a recomendação e a justificativa para verificar se estavam de acordo com os resultados obtidos na pesquisa.
- **Tempo dedicado (aprox.):** 2h00
- **Evidência da contribuição:** *(histórico de edições do arquivo no repositório e validação final)*

---

## Fontes consultadas

1. NIC.br — Dados SIMET e informações sobre as métricas de qualidade da Internet: https://bandalarga.nic.br/
2. NIC.br — Documentação do SIMET sobre medições de latência, jitter e perda de pacotes: https://docs.medicoes.nic.br/simet-integrado/debian/periodicidade/
3. RIPE Atlas — Documentação oficial e visão geral: https://atlas.ripe.net/docs/
4. RIPE Atlas — Documentação oficial da API REST: https://atlas.ripe.net/docs/apis/
5. RIPE Atlas — Autenticação e uso de API Key: https://atlas.ripe.net/docs/apis/rest-api-manual/authentication/
6. RIPE Atlas — Criação de medições: https://atlas.ripe.net/docs/apis/rest-api-manual/measurements/creating-measurements/
7. RIPE Atlas — Consulta dos resultados das medições: https://atlas.ripe.net/docs/apis/rest-api-reference/measurements/measurements_results
