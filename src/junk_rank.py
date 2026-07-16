"""정크 점유 지수 — 대회/리그 전체 랭킹 + 웹앱용 JSON.

경기별 p90이 아니라 **코퍼스 공통 p90 스케일**로 q를 정규화해 경기 간 비교를 공정하게
한다. 팀별로 여러 경기를 이벤트 가중 합산해 '정크왕/효율왕'을 낸다.

출력: analysis/_data/junk_<league>.json (웹앱 🧪 정크 점유 모드가 읽음)
사용: python junk_rank.py [--league WC] [--min-events 800]
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, "/home/opc/football")
from analysis import corpus, junk_possession as J

DB = "/home/opc/football/analysis/_data/whoscored.duckdb"
OUT_DIR = Path("/home/opc/football/analysis/_data")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="WC")
    ap.add_argument("--min-events", type=int, default=800)
    args = ap.parse_args()

    c = duckdb.connect(DB, read_only=True)
    matches = c.execute(
        "select match_id,date,home,away,home_score,away_score from matches "
        "where league=? and n_events>=? order by date", [args.league, args.min_events]).fetchall()

    # ── 1패스: 전 경기 시퀀스 수집 + 공통 p90 스케일 ──
    per_match = {}
    all_vals = []
    for mid, date, home, away, hs, as_ in matches:
        try:
            seqs = J.sequences(corpus.events_of(mid, con=c))
        except Exception:
            continue
        if not seqs:
            continue
        for s in seqs:
            s["val"] = J.value(s)
            all_vals.append(s["val"])
        per_match[mid] = dict(date=date, home=home, away=away, hs=hs, as_=as_, seqs=seqs)
    scale = float(np.percentile(all_vals, 90)) or 1e-6

    # ── 2패스: 공통 스케일로 q → 팀 집계 + 경기별 행 ──
    team_agg = defaultdict(lambda: defaultdict(float))
    match_rows = []
    for mid, m in per_match.items():
        for s in m["seqs"]:
            s["q"] = float(np.clip(s["val"] / scale, 0, 1))
        teams = sorted({s["team"] for s in m["seqs"]})
        if len(teams) != 2:
            continue
        tot_ev = sum(s["n"] for s in m["seqs"])
        for t in teams:
            ts = [s for s in m["seqs"] if s["team"] == t]
            ev = sum(s["n"] for s in ts)
            w = sum(s["n"] * s["q"] for s in ts)
            junk_ev = sum(s["n"] for s in ts if s["q"] < J.JUNK_Q)
            open_ts = [s for s in ts if s["state"] <= 0]
            open_ev = sum(s["n"] for s in open_ts)
            open_junk = sum(s["n"] for s in open_ts if s["q"] < J.JUNK_Q)
            tilt = float(np.average([s["final_third"] for s in ts], weights=[s["n"] for s in ts]))
            gf = m["hs"] if t == m["home"] else m["as_"]
            ga = m["as_"] if t == m["home"] else m["hs"]
            a = team_agg[t]
            a["ev"] += ev; a["w"] += w; a["raw_ev"] += ev; a["match_ev"] += tot_ev
            a["junk_ev"] += junk_ev; a["open_ev"] += open_ev; a["open_junk"] += open_junk
            a["tilt_w"] += tilt * ev; a["shots"] += sum(s["shot"] for s in ts)
            a["gf"] += gf; a["ga"] += ga; a["games"] += 1
            raw = ev / tot_ev * 100
            eff = w / ev if ev else 0
            won = gf > ga
            # 정크 지배 스코어: 점유 지배(>50)·저효율·못 이김일수록 큼
            sterile = max(0.0, raw - 50) * (1 - eff) * (1.0 if won else 1.6)
            match_rows.append(dict(
                mid=mid, date=m["date"], team=t, opp=(m["away"] if t == m["home"] else m["home"]),
                gf=gf, ga=ga,
                raw=round(raw, 1),
                efficiency=round(eff, 3),
                junk_open=round(open_junk / open_ev * 100, 1) if open_ev else 0,
                tilt=round(tilt * 100, 1),
                sterile=round(sterile, 2),
            ))

    teams_out = []
    for t, a in team_agg.items():
        if a["games"] < 1:
            continue
        teams_out.append(dict(
            team=t, games=int(a["games"]),
            poss=round(a["raw_ev"] / a["match_ev"] * 100, 1),
            efficiency=round(a["w"] / a["ev"], 3) if a["ev"] else 0,
            junk_frac=round(a["junk_ev"] / a["ev"] * 100, 1) if a["ev"] else 0,
            junk_open=round(a["open_junk"] / a["open_ev"] * 100, 1) if a["open_ev"] else 0,
            tilt=round(a["tilt_w"] / a["ev"] * 100, 1) if a["ev"] else 0,
            gd=int(a["gf"] - a["ga"]),
        ))
    # 정크 지배 점수: 점유 높고(>50) 효율 낮을수록 큼
    for r in teams_out:
        r["sterile_idx"] = round((r["poss"] - 50) * (1 - r["efficiency"]), 2)

    out = dict(league=args.league, scale=round(scale, 4), n_matches=len(per_match),
               teams=sorted(teams_out, key=lambda r: -r["sterile_idx"]),
               match_rows=sorted(match_rows, key=lambda r: -r["sterile"]))
    path = OUT_DIR / f"junk_{args.league}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    print(f"=== {args.league} 정크 점유 랭킹 ({len(per_match)}경기, 공통 p90={scale:.3f}) ===")
    print(f"{'팀':<16}{'경기':>4}{'점유%':>7}{'효율':>7}{'정크%':>7}{'정크(열세)%':>12}{'Tilt%':>7}{'GD':>5}{'정크지배':>8}")
    for r in out["teams"][:16]:
        print(f"{r['team']:<16}{r['games']:>4}{r['poss']:>7.1f}{r['efficiency']:>7.2f}"
              f"{r['junk_frac']:>7.0f}{r['junk_open']:>12.0f}{r['tilt']:>7.1f}{r['gd']:>+5}{r['sterile_idx']:>8.1f}")
    print(f"\n→ {path}")
    print("\n[단일경기 최고 정크 지배 — 점유 지배했으나 저효율]")
    for r in out["match_rows"][:8]:
        res = "W" if r["gf"] > r["ga"] else ("D" if r["gf"] == r["ga"] else "L")
        print(f"  {r['team']:<14} vs {r['opp']:<14} {r['gf']}-{r['ga']}[{res}] "
              f"점유{r['raw']:.0f}% 효율{r['efficiency']:.2f} 정크(열세){r['junk_open']:.0f}% tilt{r['tilt']:.0f}%")


if __name__ == "__main__":
    main()
