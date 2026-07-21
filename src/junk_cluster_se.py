"""P2 논문 중심 주장(부분회귀·VAEP 직교성)을 match-clustered robust SE로 재검증.

리뷰어 반복 지적(F2): 206 팀-경기는 103경기의 짝(paired)이라 독립 아님 →
match(mid)로 클러스터한 sandwich SE로 p값을 보수적으로 다시 계산한다.

실행: .venv/bin/python ops/junk_cluster_se.py
재사용: analysis/junk_validate.collect() (동일 파이프라인 → 논문 수치와 일관).
"""
import sys
import numpy as np
from scipy import stats

sys.path.insert(0, "/home/opc/football")
from analysis import junk_validate as JV


def cluster_ols(y, Xcols, df, cluster):
    """OLS + (a) iid SE, (b) match-clustered robust SE. 반환 dict per coef."""
    names = ["const"] + Xcols
    X = np.column_stack([np.ones(len(y))] + [df[c].values.astype(float) for c in Xcols])
    y = np.asarray(y, float)
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    n, k = X.shape

    # iid
    dof = n - k
    s2 = (resid @ resid) / dof
    se_iid = np.sqrt(np.diag(s2 * XtX_inv))

    # cluster-robust (CR1)
    g = np.asarray(cluster)
    groups = np.unique(g)
    G = len(groups)
    meat = np.zeros((k, k))
    for gid in groups:
        m = g == gid
        Xg = X[m]
        ug = resid[m]
        sg = Xg.T @ ug
        meat += np.outer(sg, sg)
    corr = (G / (G - 1.0)) * ((n - 1.0) / (n - k))
    V = corr * (XtX_inv @ meat @ XtX_inv)
    se_cl = np.sqrt(np.diag(V))

    out = []
    for i, nm in enumerate(names):
        t_iid = beta[i] / se_iid[i]
        p_iid = 2 * (1 - stats.t.cdf(abs(t_iid), dof))
        t_cl = beta[i] / se_cl[i]
        p_cl = 2 * (1 - stats.t.cdf(abs(t_cl), G - 1))   # G-1 dof, 보수적
        out.append(dict(name=nm, beta=beta[i], se_iid=se_iid[i], p_iid=p_iid,
                        se_cl=se_cl[i], p_cl=p_cl))
    return out, G, n


def show(title, rows, G, n):
    print(f"\n[{title}]  (n={n} team-matches, G={G} match clusters)")
    print(f"  {'term':<12}{'beta':>10}{'p(iid)':>11}{'p(cluster)':>13}")
    for r in rows:
        star = "***" if r["p_cl"] < 0.001 else "**" if r["p_cl"] < 0.01 else "*" if r["p_cl"] < 0.05 else ""
        print(f"  {r['name']:<12}{r['beta']:>+10.4f}{r['p_iid']:>11.4g}{r['p_cl']:>13.4g} {star}")


def main():
    tdf, _seq, _scale, _pm = JV.collect("WC")
    tdf = tdf.copy()
    print(f"수집: {len(tdf)} 팀-경기")

    # 중심 주장 1: points ~ raw + tilt + junk_open
    rows, G, n = cluster_ols(tdf["points"].values, ["raw_poss", "field_tilt", "junk_open"],
                             tdf, tdf["match"].values)
    show("points ~ raw_poss + field_tilt + junk_open", rows, G, n)

    # 중심 주장 2 (P2 핵심): points ~ VAEP + tilt + junk_open
    d = tdf.dropna(subset=["team_vaep"]).copy()
    rows, G, n = cluster_ols(d["points"].values, ["team_vaep", "field_tilt", "junk_open"],
                             d, d["match"].values)
    show("points ~ team_vaep + field_tilt + junk_open", rows, G, n)

    # 중심 주장 3: xg_diff ~ VAEP + tilt + efficiency
    rows, G, n = cluster_ols(d["xg_diff"].values, ["team_vaep", "field_tilt", "efficiency"],
                             d, d["match"].values)
    show("xg_diff ~ team_vaep + field_tilt + efficiency", rows, G, n)


if __name__ == "__main__":
    main()
