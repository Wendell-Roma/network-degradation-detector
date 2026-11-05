# Pacote de Implantação em Produção — Detector de Degradação de Rede (Grupo 42)

- **Disciplina:** Estrutura de Dados II — Centro Universitário Braz Cubas
- **Orientadora:** Profa. Dra. Andréa Ono Sakai
- **Integrantes (Grupo 42):** Wendell Rodrigues Macedo, Vinicius Firmino Souto, Fernando Paiva Coelho, João Gustavo Sanches e Daniel Dias Paranhos
- **Página Pública do Artigo Técnico (GitHub Pages):** [https://vini-wine-coder.github.io/Projeto-Modelo-Previs-o-Falha-Rede/](https://vini-wine-coder.github.io/Projeto-Modelo-Previs-o-Falha-Rede/)
- **Repositório Oficial:** [https://github.com/vini-wine-coder/Projeto-Modelo-Previs-o-Falha-Rede](https://github.com/vini-wine-coder/Projeto-Modelo-Previs-o-Falha-Rede)

---

## 1. Conteúdo do Pacote de Produção

```text
producao/
├── artefatos_modelos/
│   ├── modelo_arvore_decisao.joblib      # Modelo oficial recomendado (CART, 7 folhas, F1 Macro = 1.0000)
│   ├── modelo_random_forest.joblib       # Random Forest comparativa (Bagging, 15 árvores)
│   ├── modelo_xgboost.joblib             # XGBoost comparativo (Gradient Boosting, 36 árvores)
│   └── arvore_final_tarefa5.json         # Representação caixa-branca em JSON (7 regras auditáveis)
├── config/
│   ├── features.json                     # Lista oficial ordenada das 8 features e colunas excluídas
│   ├── baseline_por_fluxo.csv            # Ficha de baseline do Período A (mediana, MAD, IQR por fluxo)
│   └── coleta_config.json                # Parâmetros das medições públicas RIPE Atlas (origine -> destino)
├── modelos_treinados.py                  # Classes compatíveis com scikit-learn (.predict, .predict_proba)
├── inferencia_producao.py                # Script de inferência em produção (autoteste, lote CSV e RIPE Atlas ao vivo)
├── treinar_e_exportar_sklearn.py         # Script de retreinamento com GridSearchCV + PredefinedSplit + joblib.dump
├── requirements.txt                      # Dependências e versões de referência
└── README_PRODUCAO.md                    # Este guia de implantação
```

---

## 2. Como Reutilizar o Modelo Salvo (`.joblib`)

Seguindo exatamente o contrato da **Seção 7.3 (*Salvando os modelos*)** de `Arvore_e_random_forest_didatico.ipynb`, cada arquivo `.joblib` armazena um dicionário contendo o modelo treinado e seus metadados de auditoria (`familia`, `modelo`, `best_params`, `features`, `macro_f1_validacao`, `macro_f1_teste`, `recall_falha_teste`, `seed`).

```python
import joblib
import pandas as pd

# 1. Carregar o pacote do modelo recomendado para produção
pacote = joblib.load("artefatos_modelos/modelo_arvore_decisao.joblib")
modelo = pacote["modelo"]
features = pacote["features"]  # ['z_robusto', 'aumento_pct', 'jitter_relativo', 'perda_pct', 'timeout_atual', 'n5_timeout', 'n5_aumento80', 'n5_risco']

# 2. Inferir sobre novas medições (respeitando a mesma ordem de colunas do treino!)
novos_dados = pd.read_csv("novas_medicoes_normalizadas.csv")
previsoes = modelo.predict(novos_dados[features])
probabilidades = modelo.predict_proba(novos_dados[features])
```

---

## 3. Como Executar o Script de Inferência em Produção

### Modo A — Autoteste dos 3 Modelos e Simulação de Cenários (`OK`, `RISCO`, `FALHA`)
```bash
python3 inferencia_producao.py
```

### Modo B — Inferência em Lote sobre Arquivo CSV
```bash
python3 inferencia_producao.py --csv ../data/processed/teste_periodo_b.csv --limite 20
```

### Modo C — Consulta e Classificação em Tempo Real via API do RIPE Atlas
```bash
python3 inferencia_producao.py --ripe-live --msm 1001
```

---

## 4. Por que a Árvore de Decisão (CART — 7 folhas) é o Modelo Oficial de Produção?

| Família | Hiperparâmetros Vencedores | Macro-F1 (Validação) | Macro-F1 (Teste) | Recall `FALHA` | Recall `RISCO` | Latência / Amostra |
|---|---|---:|---:|---:|---:|---:|
| **Árvore de Decisão (CART)** | `criterion='entropy', max_depth=6, min_samples_leaf=20` | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.18 µs (1.0x)** |
| **Random Forest (Bagging)** | `n_estimators=15, max_depth=6, max_features=5, min_samples_leaf=20` | 0.7462 | 0.7544 | 1.0000 | 0.1534 | 4.80 µs (27.2x) |
| **XGBoost (Boosting)** | `n_estimators=12, max_depth=6, learning_rate=0.35, reg_lambda=1.0, gamma=0.1` | **1.0000** | **1.0000** | **1.0000** | **1.0000** | 7.50 µs (42.5x) |

A **Árvore de Decisão (CART) de 7 folhas** empata em `Macro-F1 = 1.0000` com o XGBoost, supera a Random Forest (`0.7544`), tem **latência 42,5 vezes menor** (`0,18 µs` por amostra) e oferece **100% de interpretabilidade caixa-branca** para equipes de operação de rede (NOC).
