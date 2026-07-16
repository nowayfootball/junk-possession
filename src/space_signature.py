"""공간창출 시그니처 — GSR 트래킹으로 '정크 vs 공간창출' 점유를 판정한다.

이벤트 정크지수(analysis/junk_possession.py)는 공만 보고 '점유가 위협으로 이어졌나'를
잰다. 하지만 '왜 정크였나' — 상대 블록을 실제로 밀어냈나 vs 애초에 죽은 순환인가 — 는
공 없는 21명 위치가 있어야 안다. 그게 GSR 공간레이어다.

spatial_value.py가 낸 시계열(spatial.json)에서:
  · d_own = 점유팀의 상대-공격third 지배 변화(초반1/3 → 후반1/3)
  · d_opp = 상대의 전진(자기 공격third) 지배 붕괴량
  · Space-Creation Index(SCI) = d_own + d_opp
    SCI 크다 = 점유로 상대 블록을 밀어내 위험공간 장악(공간창출, 아까운 점유).
    SCI ≈ 0  = 블록 안 흔들림 → 진짜 죽은 정크(이벤트지수의 '가짜 지배' 확증).

점유팀(possessor)은 인자로 받거나, 자동(공간가치 점유율 높은 팀)으로 정한다.
사용: python space_signature.py out/<클립>/spatial.json [--possessor 0|1] [--no-chart]
출력: out/<클립>/space_signature.json (+ space_signature.png)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from analysis import _mplfont  # noqa: F401  한글 폰트(Noto Sans CJK KR) 자동 적용


def _smooth(a, k=5):
    a = np.asarray(a, float)
    if len(a) < k:
        return a
    return np.convolve(a, np.ones(k) / k, mode="same")


def signature(series, possessor):
    """spatial.json series + 점유팀(0/1) → SCI dict."""
    t = np.asarray(series["t"], float)
    own = np.asarray(series[f"fz{possessor}"], float) * 100      # 점유팀 공격third 지배
    opp = np.asarray(series[f"fz{1 - possessor}"], float) * 100  # 상대 전진 지배
    n = len(t)
    a, b = max(1, n // 3), 2 * n // 3
    d_own = float(own[b:].mean() - own[:a].mean())
    d_opp = float(opp[:a].mean() - opp[b:].mean())              # 붕괴량(양수=상대 밀림)
    sci = d_own + d_opp
    verdict = ("공간창출(아까운 점유)" if sci >= 12 else
               "약한 전진" if sci >= 4 else "죽은 정크(블록 안 흔들림)")
    return dict(
        possessor=possessor, sci=round(sci, 1), verdict=verdict,
        own_third_early=round(float(own[:a].mean()), 1), own_third_late=round(float(own[b:].mean()), 1),
        opp_advance_early=round(float(opp[:a].mean()), 1), opp_advance_late=round(float(opp[b:].mean()), 1),
        d_own=round(d_own, 1), d_opp_collapse=round(d_opp, 1), n_frames=n,
        window_s=[round(float(t[0]), 1), round(float(t[-1]), 1)],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spatial", help="out/<클립>/spatial.json")
    ap.add_argument("--possessor", type=int, default=-1, help="점유팀 0/1 (기본 자동=공간가치 우세팀)")
    ap.add_argument("--no-chart", action="store_true")
    args = ap.parse_args()

    sp_path = Path(args.spatial)
    sp = json.loads(sp_path.read_text())
    series, summ = sp["series"], sp["summary"]

    poss = args.possessor
    if poss not in (0, 1):
        svs = summ.get("spatial_value_share", [50, 50])
        poss = 0 if svs[0] >= svs[1] else 1

    sig = signature(series, poss)
    out = sp_path.with_name("space_signature.json")
    out.write_text(json.dumps(sig, ensure_ascii=False, indent=1))

    print(f"=== 공간창출 시그니처 (점유팀 = Team{poss}) ===")
    print(f"  점유팀 공격third 지배 {sig['own_third_early']}% → {sig['own_third_late']}%  (Δ{sig['d_own']:+})")
    print(f"  상대 전진 지배        {sig['opp_advance_early']}% → {sig['opp_advance_late']}%  (붕괴 {sig['d_opp_collapse']:+})")
    print(f"  → Space-Creation Index = {sig['sci']:+}  →  {sig['verdict']}")
    print(f"→ {out}")

    if not args.no_chart:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            t = np.asarray(series["t"], float)
            own = _smooth(np.asarray(series[f"fz{poss}"]) * 100)
            opp = _smooth(np.asarray(series[f"fz{1 - poss}"]) * 100)
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.plot(t, own, color="navy", lw=2.3, label=f"Team{poss} (점유) — 상대 골문쪽 third 지배")
            ax.plot(t, opp, color="#888", lw=2.3, label=f"Team{1-poss} — 자기 공격third 지배(전진)")
            ax.fill_between(t, own, opp, where=(own >= opp), alpha=.12, color="navy")
            ax.set_title(f"공간창출 시그니처 · SCI {sig['sci']:+} → {sig['verdict']}", fontsize=11)
            ax.set_xlabel("time (s)"); ax.set_ylabel("final-third space control (%)")
            ax.legend(fontsize=8); ax.grid(alpha=.3)
            fig.tight_layout(); fig.savefig(sp_path.with_name("space_signature.png"), dpi=115)
            print(f"→ {sp_path.with_name('space_signature.png')}")
        except Exception as e:
            print("차트 스킵:", e)


if __name__ == "__main__":
    main()
