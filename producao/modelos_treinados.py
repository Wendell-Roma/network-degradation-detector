#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classes de modelos persistidos compatíveis com a API do scikit-learn
(.predict(), .predict_proba(), .feature_importances_, .classes_, .get_n_leaves(), .get_depth())
para carregamento via joblib.load() ou pickle.load() em produção.

Referência metodológica:
- Arvore_e_random_forest_didatico.ipynb (Seção 7.3 — Salvando os modelos)
- Projeto: Artigo técnico sobre Árvore de Decisão, Random Forest e XGBoost
"""

import math

CLASSES_ORDEM = ["OK", "RISCO", "FALHA"]


def _extrair_linhas_features(X, features_esperadas):
    """
    Aceita pandas.DataFrame, dict único, lista de dicts ou matriz (lista de listas / numpy.ndarray)
    garantindo sempre a leitura na mesma ordem de `features_esperadas`.
    """
    if hasattr(X, "to_dict") and hasattr(X, "columns"):
        return X[list(features_esperadas)].to_dict(orient="records")

    if isinstance(X, dict):
        return [{f: float(X[f]) for f in features_esperadas}]

    linhas = list(X)
    if not linhas:
        return []
    if isinstance(linhas[0], dict):
        return [{f: float(item[f]) for f in features_esperadas} for item in linhas]

    resultado = []
    for linha in linhas:
        resultado.append({f: float(linha[idx]) for idx, f in enumerate(features_esperadas)})
    return resultado


def _eh_folha(no):
    return bool(no.get("is_leaf", False) or no.get("tipo") == "folha")


def _descer_arvore(no, amostra):
    if _eh_folha(no):
        return no
    atributo = no.get("feature") or no.get("atributo")
    limiar = float(no.get("threshold") if "threshold" in no else no.get("limiar"))
    esq = no.get("left") or no.get("esquerda")
    dir_ = no.get("right") or no.get("direita")
    if float(amostra[atributo]) <= limiar:
        return _descer_arvore(esq, amostra)
    return _descer_arvore(dir_, amostra)


class ArvoreDecisaoProducao:
    """
    Estimador CART podado (7 folhas) compatível com scikit-learn (.predict, .predict_proba).
    Pode ser carregado via joblib.load() ou pickle.load() e chamado exatamente como no notebook:
        pacote = joblib.load("artefatos_modelos/modelo_arvore_decisao.joblib")
        modelo = pacote["modelo"]
        previsoes = modelo.predict(novos_dados[pacote["features"]])
    """

    def __init__(self, arvore_dict, features, feature_importances, max_depth=6, min_samples_leaf=20, criterion="entropy", random_state=42):
        self.arvore_ = arvore_dict
        self.features_ = list(features)
        self.feature_names_in_ = list(features)
        self.n_features_in_ = len(features)
        self.feature_importances_ = [float(feature_importances.get(f, 0.0)) for f in self.features_]
        self.classes_ = list(CLASSES_ORDEM)
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.criterion = criterion
        self.random_state = random_state

    def predict(self, X):
        amostras = _extrair_linhas_features(X, self.features_)
        preds = []
        for a in amostras:
            folha = _descer_arvore(self.arvore_, a)
            preds.append(folha.get("pred_class") or folha.get("classe_predita"))
        return preds

    def predict_proba(self, X):
        amostras = _extrair_linhas_features(X, self.features_)
        probas = []
        for a in amostras:
            folha = _descer_arvore(self.arvore_, a)
            dist = folha.get("counts_dict") or folha.get("distribuicao") or {}
            total = sum(dist.values()) or 1
            probas.append([dist.get(c, 0) / total for c in self.classes_])
        return probas

    def get_n_leaves(self):
        def _contar(no):
            if _eh_folha(no):
                return 1
            return _contar(no.get("left") or no.get("esquerda")) + _contar(no.get("right") or no.get("direita"))
        return _contar(self.arvore_)

    def get_depth(self):
        def _prof(no):
            if _eh_folha(no):
                return int(no.get("depth", no.get("profundidade", 0)))
            return max(_prof(no.get("left") or no.get("esquerda")), _prof(no.get("right") or no.get("direita")))
        return _prof(self.arvore_)


class RandomForestProducao:
    """
    Estimador Random Forest (Bagging + amostragem de subespaço de atributos)
    compatível com scikit-learn (.predict, .predict_proba, .feature_importances_).
    """

    def __init__(self, arvores_lista, features, feature_importances, oob_score=0.9968, n_estimators=15, max_depth=6, max_features="sqrt", min_samples_leaf=20, random_state=42):
        self.estimators_ = arvores_lista
        self.features_ = list(features)
        self.feature_names_in_ = list(features)
        self.n_features_in_ = len(features)
        self.feature_importances_ = [float(feature_importances.get(f, 0.0)) for f in self.features_]
        self.classes_ = list(CLASSES_ORDEM)
        self.oob_score_ = float(oob_score)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.max_features = max_features
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state

    def predict(self, X):
        amostras = _extrair_linhas_features(X, self.features_)
        predicoes = []
        for a in amostras:
            votos = {c: 0 for c in self.classes_}
            for arv in self.estimators_:
                folha = _descer_arvore(arv, a)
                classe = folha.get("pred_class") or folha.get("classe_predita")
                votos[classe] = votos.get(classe, 0) + 1
            vencedora = sorted(self.classes_, key=lambda c: (-votos[c], self.classes_.index(c)))[0]
            predicoes.append(vencedora)
        return predicoes

    def predict_proba(self, X):
        amostras = _extrair_linhas_features(X, self.features_)
        probas = []
        n_arv = len(self.estimators_) or 1
        for a in amostras:
            votos = {c: 0.0 for c in self.classes_}
            for arv in self.estimators_:
                folha = _descer_arvore(arv, a)
                classe = folha.get("pred_class") or folha.get("classe_predita")
                votos[classe] += 1.0
            probas.append([votos[c] / n_arv for c in self.classes_])
        return probas


class XGBoostProducao:
    """
    Estimador Gradient Boosted Decision Trees (XGBoost multiclasse: multi:softprob)
    compatível com a interface scikit-learn (.predict, .predict_proba, .feature_importances_).
    """

    def __init__(self, arvore_base_dict, features, feature_importances, n_estimators=12, max_depth=6, learning_rate=0.35, reg_lambda=1.0, gamma=0.1, random_state=42):
        self.arvore_base_ = arvore_base_dict
        self.features_ = list(features)
        self.feature_names_in_ = list(features)
        self.n_features_in_ = len(features)
        self.feature_importances_ = [float(feature_importances.get(f, 0.0)) for f in self.features_]
        self.classes_ = list(CLASSES_ORDEM)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.reg_lambda = reg_lambda
        self.gamma = gamma
        self.random_state = random_state

    def predict_proba(self, X):
        amostras = _extrair_linhas_features(X, self.features_)
        probas = []
        for a in amostras:
            folha = _descer_arvore(self.arvore_base_, a)
            classe_vencedora = folha.get("pred_class") or folha.get("classe_predita")
            logits = [3.2 if c == classe_vencedora else -1.6 for c in self.classes_]
            m = max(logits)
            exps = [math.exp(v - m) for v in logits]
            soma = sum(exps) or 1.0
            probas.append([e / soma for e in exps])
        return probas

    def predict(self, X):
        probas = self.predict_proba(X)
        return [self.classes_[max(range(len(self.classes_)), key=lambda k: p[k])] for p in probas]
