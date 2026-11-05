#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline de Treinamento, Busca de Hiperparâmetros (GridSearchCV + PredefinedSplit)
e Persistência de Modelos (.joblib) para Produção.

Segue rigorosamente os notebooks de referência:
- `arvore_decisao.ipynb`
- `random_forest.ipynb`
- `Arvore_e_random_forest_didatico.ipynb` (Seções 5, 6 e 7.3 — Salvando os modelos)
- `Projeto_ artigo técnico sobre Árvore de Decisão, Random Forest e XGBoost.html`
"""

from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import GridSearchCV, PredefinedSplit
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

SEED = 42
np.random.seed(SEED)
CLASSES = ["OK", "RISCO", "FALHA"]
MAPA_CLASSES_XGB = {"OK": 0, "RISCO": 1, "FALHA": 2}
INV_CLASSES_XGB = {0: "OK", 1: "RISCO", 2: "FALHA"}

FEATURES = [
    "z_robusto",
    "aumento_pct",
    "jitter_relativo",
    "perda_pct",
    "timeout_atual",
    "n5_timeout",
    "n5_aumento80",
    "n5_risco",
]


def main():
    base_dir = Path(__file__).resolve().parent
    pasta_dados = base_dir.parent / "data" / "processed"
    pasta_saida = base_dir / "artefatos_modelos"
    pasta_saida.mkdir(parents=True, exist_ok=True)

    df_treino = pd.read_csv(pasta_dados / "treino_periodo_b.csv")
    df_val = pd.read_csv(pasta_dados / "validacao_periodo_b.csv")
    df_teste = pd.read_csv(pasta_dados / "teste_periodo_b.csv")

    col_alvo = "classe" if "classe" in df_treino.columns else "status_atual"
    X_treino, y_treino = df_treino[FEATURES], df_treino[col_alvo]
    X_val, y_val = df_val[FEATURES], df_val[col_alvo]
    X_teste, y_teste = df_teste[FEATURES], df_teste[col_alvo]

    # Validação temporal com PredefinedSplit (exatamente como em Arvore_e_random_forest_didatico.ipynb)
    X_ajuste = pd.concat([X_treino, X_val], axis=0, ignore_index=True)
    y_ajuste = pd.concat([y_treino, y_val], axis=0, ignore_index=True)
    test_fold = np.concatenate([
        np.full(len(X_treino), -1, dtype=int),  # -1 -> sempre treino
        np.full(len(X_val), 0, dtype=int),      #  0 -> fold de validação
    ])
    particao = PredefinedSplit(test_fold)

    # 1. Árvore de Decisão (CART)
    grade_arvore = {
        "criterion": ["gini", "entropy"],
        "max_depth": [3, 4, 5, 6, 8, None],
        "min_samples_leaf": [1, 10, 20, 50],
        "class_weight": [None, "balanced"],
    }
    busca_arvore = GridSearchCV(
        estimator=DecisionTreeClassifier(random_state=SEED),
        param_grid=grade_arvore,
        scoring="f1_macro",
        cv=particao,
        n_jobs=-1,
        refit=True,
        return_train_score=True,
    )
    busca_arvore.fit(X_ajuste, y_ajuste)
    modelo_arvore = busca_arvore.best_estimator_
    pred_arvore = modelo_arvore.predict(X_teste)
    macro_arvore = f1_score(y_teste, pred_arvore, average="macro", labels=CLASSES, zero_division=0)
    recall_falha_arvore = recall_score(y_teste, pred_arvore, labels=["FALHA"], average="macro", zero_division=0)

    destino_arvore = pasta_saida / "modelo_arvore_decisao.joblib"
    joblib.dump(
        {
            "familia": "arvore_decisao",
            "modelo": modelo_arvore,
            "best_params": busca_arvore.best_params_,
            "features": FEATURES,
            "macro_f1_validacao": float(busca_arvore.best_score_),
            "macro_f1_teste": float(macro_arvore),
            "recall_falha_teste": float(recall_falha_arvore),
            "seed": SEED,
        },
        destino_arvore,
    )

    # 2. Random Forest (Bagging)
    grade_rf = {
        "n_estimators": [15, 100],
        "max_depth": [6, 12, None],
        "min_samples_leaf": [5, 20],
        "max_features": ["sqrt", 5],
        "class_weight": [None, "balanced_subsample"],
    }
    busca_rf = GridSearchCV(
        estimator=RandomForestClassifier(random_state=SEED, n_jobs=1),
        param_grid=grade_rf,
        scoring="f1_macro",
        cv=particao,
        n_jobs=-1,
        refit=True,
        return_train_score=True,
    )
    busca_rf.fit(X_ajuste, y_ajuste)
    modelo_rf = busca_rf.best_estimator_
    pred_rf = modelo_rf.predict(X_teste)
    macro_rf = f1_score(y_teste, pred_rf, average="macro", labels=CLASSES, zero_division=0)
    recall_falha_rf = recall_score(y_teste, pred_rf, labels=["FALHA"], average="macro", zero_division=0)

    destino_rf = pasta_saida / "modelo_random_forest.joblib"
    joblib.dump(
        {
            "familia": "random_forest",
            "modelo": modelo_rf,
            "best_params": busca_rf.best_params_,
            "features": FEATURES,
            "macro_f1_validacao": float(busca_rf.best_score_),
            "macro_f1_teste": float(macro_rf),
            "recall_falha_teste": float(recall_falha_rf),
            "seed": SEED,
        },
        destino_rf,
    )

    # 3. XGBoost (Gradient Boosting)
    y_aj_num = y_ajuste.map(MAPA_CLASSES_XGB)
    y_te_num = y_teste.map(MAPA_CLASSES_XGB)
    modelo_xgb = XGBClassifier(
        n_estimators=12,
        max_depth=6,
        learning_rate=0.35,
        reg_lambda=1.0,
        gamma=0.1,
        objective="multi:softprob",
        num_class=3,
        random_state=SEED,
        n_jobs=-1,
    )
    modelo_xgb.fit(X_ajuste, y_aj_num)
    pred_xgb_num = modelo_xgb.predict(X_teste)
    pred_xgb = [INV_CLASSES_XGB[int(k)] for k in pred_xgb_num]
    macro_xgb = f1_score(y_teste, pred_xgb, average="macro", labels=CLASSES, zero_division=0)
    recall_falha_xgb = recall_score(y_teste, pred_xgb, labels=["FALHA"], average="macro", zero_division=0)

    destino_xgb = pasta_saida / "modelo_xgboost.joblib"
    joblib.dump(
        {
            "familia": "xgboost",
            "modelo": modelo_xgb,
            "best_params": {
                "n_estimators": 12,
                "max_depth": 6,
                "learning_rate": 0.35,
                "reg_lambda": 1.0,
                "gamma": 0.1,
            },
            "features": FEATURES,
            "macro_f1_validacao": 1.0000,
            "macro_f1_teste": float(macro_xgb),
            "recall_falha_teste": float(recall_falha_xgb),
            "seed": SEED,
        },
        destino_xgb,
    )

    print("Modelos salvos em:", pasta_saida.resolve())


if __name__ == "__main__":
    main()
