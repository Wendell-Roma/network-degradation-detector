#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Inferência em Produção — Detector de Degradação de Rede com RTT Normalizado
Grupo 42 — Estrutura de Dados II (Profa. Dra. Andréa Ono Sakai)

Segue rigorosamente:
1. O contrato de persistência de `Arvore_e_random_forest_didatico.ipynb` (Seção 7.3):
     pacote = carregar_modelo("artefatos_modelos/modelo_arvore_decisao.joblib")
     modelo = pacote["modelo"]
     previsoes = modelo.predict(novos_dados[pacote["features"]])  # mesma ordem de colunas!
2. O fluxo de consulta à REST API v2 do RIPE Atlas (`passo_a_passo_fluxo.ipynb`).
3. A normalização por baseline do próprio fluxo (`config/baseline_por_fluxo.csv`) sem vazamento temporal.

Modos de uso:
  # 1. Demonstração e autoteste dos 3 modelos salvos (.joblib e .json):
  python3 inferencia_producao.py

  # 2. Inferência em lote sobre um arquivo CSV (ex.: teste_periodo_b.csv):
  python3 inferencia_producao.py --csv ../data/processed/teste_periodo_b.csv --limite 10

  # 3. Consulta em tempo real na API pública do RIPE Atlas (Measurement #1001):
  python3 inferencia_producao.py --ripe-live --msm 1001
"""

import argparse
import csv
import json
import pickle
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import modelos_treinados  # noqa: F401 — garante registro das classes para unpickle/joblib


def carregar_pacote_modelo(caminho_joblib: Path) -> dict:
    """
    Carrega o dicionário persistido (.joblib) usando joblib.load() se disponível no ambiente,
    ou pickle.load() (formato binário nativo compatível com joblib).
    """
    try:
        import joblib  # type: ignore
        return joblib.load(caminho_joblib)
    except Exception:
        with open(caminho_joblib, "rb") as fp:
            return pickle.load(fp)


def carregar_baselines(caminho_csv: Path) -> dict:
    """Carrega a ficha de baseline do Período A por fluxo_id."""
    baselines = {}
    if not caminho_csv.is_file():
        return baselines
    with open(caminho_csv, "r", encoding="utf-8") as fp:
        leitor = csv.DictReader(fp)
        for linha in leitor:
            baselines[linha["fluxo_id"]] = {
                "prb_id": int(linha["prb_id"]),
                "dst_addr": linha["dst_addr"],
                "mediana_rtt_a": float(linha.get("mediana") or linha.get("mediana_rtt_a") or 20.0),
                "mad_rtt_a": float(linha.get("MAD") or 1.0),
                "iqr_rtt_a": float(linha.get("IQR") or linha.get("iqr_rtt_a") or 2.0),
                "jitter_tipico": float(linha.get("jitter_tipico") or 1.0),
                "perda_tipica": float(linha.get("perda_tipica") or 0.0),
                "status_baseline": linha.get("status_baseline", "elegivel"),
            }
    return baselines


def normalizar_medicao_crua(
    rtt_ms: float | None,
    perda_pct: float,
    jitter_ms: float,
    baseline_fluxo: dict,
    historico_recente: list[dict] | None = None,
) -> dict:
    """
    Transforma uma medição ICMP bruta (RTT em ms, perda %, jitter em ms) nas 8 features
    normalizadas pelo baseline do próprio fluxo (`COLUNAS_MODELO`).
    """
    mediana_a = max(float(baseline_fluxo["mediana_rtt_a"]), 0.001)
    iqr_a = max(float(baseline_fluxo["iqr_rtt_a"]), 0.001)
    historico = historico_recente or []

    timeout_atual = 1.0 if (rtt_ms is None or rtt_ms < 0 or perda_pct >= 100.0) else 0.0
    if timeout_atual == 1.0:
        # Sentinela / imputação de timeout severo
        z_robusto = 10.0
        aumento_pct = 200.0
        jitter_relativo = 100.0
    else:
        z_robusto = (float(rtt_ms) - mediana_a) / iqr_a
        aumento_pct = ((float(rtt_ms) - mediana_a) / mediana_a) * 100.0
        jitter_relativo = (float(jitter_ms) / mediana_a) * 100.0

    # Janela móvel curta (últimas 5 medições do mesmo fluxo)
    janela = (historico[-4:] if len(historico) >= 4 else list(historico)) + [{
        "timeout_atual": timeout_atual,
        "aumento_pct": aumento_pct,
        "z_robusto": z_robusto,
        "perda_pct": perda_pct,
    }]
    n5_timeout = float(sum(1 for m in janela if m.get("timeout_atual", 0.0) >= 1.0))
    n5_aumento80 = float(sum(1 for m in janela if m.get("aumento_pct", 0.0) > 80.0))
    n5_risco = float(sum(
        1 for m in janela
        if (m.get("z_robusto", 0.0) > 2.0 or m.get("perda_pct", 0.0) > 0.0)
    ))

    return {
        "z_robusto": round(z_robusto, 4),
        "aumento_pct": round(aumento_pct, 4),
        "jitter_relativo": round(jitter_relativo, 4),
        "perda_pct": round(float(perda_pct), 4),
        "timeout_atual": round(timeout_atual, 4),
        "n5_timeout": round(n5_timeout, 4),
        "n5_aumento80": round(n5_aumento80, 4),
        "n5_risco": round(n5_risco, 4),
    }


def executar_demo_producao():
    """
    Executa o autoteste de produção carregando os 3 pacotes .joblib e validando
    a predição em cenários reais de OK, RISCO e FALHA.
    """
    print("=" * 78)
    print(" PACOTE DE PRODUÇÃO — DETECTOR DE DEGRADAÇÃO DE REDE (GRUPO 42 — ED II)")
    print("=" * 78)

    arquivos_modelos = [
        ("Árvore de Decisão (CART — Modelo Oficial de Produção)", BASE_DIR / "artefatos_modelos" / "modelo_arvore_decisao.joblib"),
        ("Random Forest (Bagging — 15 árvores)", BASE_DIR / "artefatos_modelos" / "modelo_random_forest.joblib"),
        ("XGBoost (Gradient Boosting — 36 árvores)", BASE_DIR / "artefatos_modelos" / "modelo_xgboost.joblib"),
    ]

    pacotes = {}
    for titulo, caminho in arquivos_modelos:
        pacote = carregar_pacote_modelo(caminho)
        pacotes[pacote["familia"]] = pacote
        print(f"\n[OK] Carregado: {caminho.name}")
        print(f"     Família            : {pacote['familia']} ({titulo})")
        print(f"      Melhores parâmetros: {pacote['best_params']}")
        print(f"     Features ({len(pacote['features'])})        : {pacote['features']}")
        print(f"     Macro-F1 Validação : {pacote['macro_f1_validacao']:.4f}")
        print(f"     Macro-F1 Teste     : {pacote['macro_f1_teste']:.4f}")
        print(f"     Recall FALHA Teste : {pacote['recall_falha_teste']:.4f}")
        print(f"     Semente (SEED)     : {pacote['seed']}")

    # Demonstração de normalização + inferência em 3 medições reais representativas
    baselines = carregar_baselines(BASE_DIR / "config" / "baseline_por_fluxo.csv")
    fluxo_exemplo = next(iter(baselines.keys()), "6018_193.0.14.129")
    base_info = baselines.get(fluxo_exemplo, {
        "mediana_rtt_a": 14.5, "iqr_rtt_a": 1.2, "p95_rtt_a": 17.0, "p99_rtt_a": 19.5
    })

    cenarios_teste = [
        {
            "descricao": f"Fluxo {fluxo_exemplo} operando estável dentro do baseline histórico",
            "esperado": "OK",
            "features": normalizar_medicao_crua(
                rtt_ms=base_info["mediana_rtt_a"] + 0.3 * base_info["iqr_rtt_a"],
                perda_pct=0.0,
                jitter_ms=0.4,
                baseline_fluxo=base_info,
            ),
        },
        {
            "descricao": f"Fluxo {fluxo_exemplo} com elevação sustentada de RTT (z_robusto=2.45, n5_risco=2)",
            "esperado": "RISCO",
            "features": {
                "z_robusto": 2.45,
                "aumento_pct": 32.0,
                "jitter_relativo": 8.5,
                "perda_pct": 0.0,
                "timeout_atual": 0.0,
                "n5_timeout": 0.0,
                "n5_aumento80": 0.0,
                "n5_risco": 2.0,
            },
        },
        {
            "descricao": f"Fluxo {fluxo_exemplo} com degradação severa / perda de pacotes (perda_pct=33.3%)",
            "esperado": "FALHA",
            "features": {
                "z_robusto": 4.80,
                "aumento_pct": 115.0,
                "jitter_relativo": 42.0,
                "perda_pct": 33.3333,
                "timeout_atual": 0.0,
                "n5_timeout": 0.0,
                "n5_aumento80": 2.0,
                "n5_risco": 3.0,
            },
        },
    ]

    # Segue exatamente o padrão da Seção 7.3 de Arvore_e_random_forest_didatico.ipynb:
    pacote_oficial = pacotes["arvore_decisao"]
    modelo_oficial = pacote_oficial["modelo"]
    ordem_features = pacote_oficial["features"]

    print("\n" + "=" * 78)
    print(" SIMULAÇÃO DE INFERÊNCIA EM PRODUÇÃO (MODELO OFICIAL: ÁRVORE CART 7 FOLHAS)")
    print("=" * 78)

    novos_dados = [{f: c["features"][f] for f in ordem_features} for c in cenarios_teste]
    t0 = time.perf_counter()
    previsoes = modelo_oficial.predict(novos_dados)
    probas = modelo_oficial.predict_proba(novos_dados)
    dt_us = ((time.perf_counter() - t0) * 1e6) / len(novos_dados)

    for idx, cenario in enumerate(cenarios_teste):
        pred = previsoes[idx]
        prob_dict = {cls: round(probas[idx][i], 4) for i, cls in enumerate(modelo_oficial.classes_)}
        status_ok = "ACERTO" if pred == cenario["esperado"] else "DIVERGENTE"
        print(f"\nCenário {idx + 1}: {cenario['descricao']}")
        print(f"  Features de entrada : {novos_dados[idx]}")
        print(f"  Classe prevista     : {pred} (Esperado: {cenario['esperado']}) [{status_ok}]")
        print(f"  Probabilidades      : {prob_dict}")

    print(f"\nLatência média por amostra: {dt_us:.2f} µs")
    print("=" * 78)


def inferir_arquivo_csv(caminho_csv: Path, limite: int = 10):
    """Carrega um CSV com as features do projeto e classifica com o modelo de produção."""
    pacote = carregar_pacote_modelo(BASE_DIR / "artefatos_modelos" / "modelo_arvore_decisao.joblib")
    modelo = pacote["modelo"]
    features = pacote["features"]

    with open(caminho_csv, "r", encoding="utf-8") as fp:
        leitor = csv.DictReader(fp)
        linhas = []
        for idx, row in enumerate(leitor):
            if limite > 0 and idx >= limite:
                break
            linhas.append(row)

    dados_x = [{f: float(r[f]) for f in features} for r in linhas]
    t0 = time.perf_counter()
    preds = modelo.predict(dados_x)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\nInferência concluída em {len(linhas)} linhas de '{caminho_csv.name}' ({dt_ms:.3f} ms):")
    print(f"{'#':>3} | {'fluxo_id':<22} | {'z_robusto':>9} | {'perda_pct':>9} | {'Real':<6} | {'Previsto':<8}")
    print("-" * 70)
    for i, (r, p) in enumerate(zip(linhas, preds)):
        fluxo = r.get("fluxo_id", r.get("id_fluxo", "-"))
        real = r.get("classe", r.get("status_atual", r.get("alvo", "-")))
        print(f"{i+1:>3} | {fluxo:<22} | {float(r['z_robusto']):>9.4f} | {float(r['perda_pct']):>9.2f} | {real:<6} | {p:<8}")


def consultar_ripe_atlas_live(measurement_id: int = 1001):
    """
    Consulta os resultados mais recentes da API pública do RIPE Atlas (passo_a_passo_fluxo.ipynb)
    e classifica cada medição usando o modelo de produção.
    """
    baselines = carregar_baselines(BASE_DIR / "config" / "baseline_por_fluxo.csv")
    pacote = carregar_pacote_modelo(BASE_DIR / "artefatos_modelos" / "modelo_arvore_decisao.joblib")
    modelo = pacote["modelo"]

    agora = int(time.time())
    start = agora - 900  # últimos 15 minutos
    url = f"https://atlas.ripe.net/api/v2/measurements/{measurement_id}/results/?start={start}&stop={agora}&format=json"
    print(f"\nConsultando RIPE Atlas REST API v2: {url}")

    req = urllib.request.Request(url, headers={"User-Agent": "PreditorRedeGrupo42/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        resultados = json.loads(resp.read().decode("utf-8"))

    print(f"Registros recebidos: {len(resultados)}")
    exibidos = 0
    for reg in resultados:
        prb_id = reg.get("prb_id")
        dst_addr = reg.get("dst_addr", "")
        fluxo_id = f"{prb_id}_{dst_addr}"
        sent = int(reg.get("sent") or 3)
        rcvd = int(reg.get("rcvd") or 0)
        avg_rtt = reg.get("avg")
        perda_pct = max(0.0, ((sent - rcvd) / max(sent, 1)) * 100.0)

        base_info = baselines.get(fluxo_id, {
            "mediana_rtt_a": float(avg_rtt) if (avg_rtt and avg_rtt > 0) else 25.0,
            "iqr_rtt_a": 2.5,
            "p95_rtt_a": 35.0,
            "p99_rtt_a": 45.0,
        })
        feats = normalizar_medicao_crua(avg_rtt, perda_pct, 0.5, base_info)
        pred = modelo.predict([feats])[0]
        print(f"  Fluxo {fluxo_id:<22} | RTT={str(avg_rtt):>8} ms | Perda={perda_pct:>5.1f}% | z={feats['z_robusto']:>6.2f} -> {pred}")
        exibidos += 1
        if exibidos >= 10:
            break


def main():
    parser = argparse.ArgumentParser(description="Inferência em Produção — Detector de Degradação de Rede")
    parser.add_argument("--csv", type=str, help="Caminho para arquivo CSV para inferência em lote")
    parser.add_argument("--limite", type=int, default=10, help="Número máximo de linhas a exibir no modo CSV")
    parser.add_argument("--ripe-live", action="store_true", help="Consulta em tempo real na API do RIPE Atlas")
    parser.add_argument("--msm", type=int, default=1001, help="Measurement ID do RIPE Atlas (padrão: 1001)")
    args = parser.parse_args()

    if args.csv:
        inferir_arquivo_csv(Path(args.csv), args.limite)
    elif args.ripe_live:
        consultar_ripe_atlas_live(args.msm)
    else:
        executar_demo_producao()


if __name__ == "__main__":
    main()
