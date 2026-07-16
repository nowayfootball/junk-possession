"""정크(가짜) 점유 지수 — 점유율의 허수를 벗겨낸다.

점유율 70%도 자기진영 횡패스면 무의미하다. possession 시퀀스(chain) 단위로 **위협
잠재력**을 매겨 raw 점유 대비 effective 점유를 낸다. (사용자 설계 반영)

시퀀스 가치(잠재력 중심):
  · peak_xt_gain : 사슬 중 도달한 최고 위협 국면 − 시작  ← ★counterfactual/잠재력
                    (실제 슛 안 돼도 위험 위치까지 갔으면 인정)
  · shot         : 사슬이 슛으로 끝나면 이진 보너스 (실현된 시도)
  · box_reach    : 상대 박스 진입 보너스
  q ∈ [0,1] = 시퀀스 가치를 코퍼스 분위수로 정규화. junk = q 낮은 점유.

★국면 정규화: 골 이벤트로 실시간 스코어를 복원해 각 시퀀스의 스코어 상태를 태깅.
  리드 지키며 도는 순환(state>0)은 정상 전술 → 헤드라인 정크는 '동점/열세(state<=0)'
  국면의 순환만 센다(junk_open). 그게 진짜 실패한 가짜 지배.

데이터 주의: 이 WhoScored 피드의 shot_statsbomb_xg는 전 슛 0.05 고정 플레이스홀더 → 폐기.
  대신 **우리가 코퍼스로 학습한 xG 모델(analysis/xg.py)**을 슛 위치로 추론해 슛 '질'을 반영한다
  (바디/상황 미보유 → foot·open_play 근사). 모델 로드 실패 시 이진 보너스로 폴백.

지표(팀별): RawPoss% · Efficiency(평균 q) · EffectiveShare% · Junk%p(=Raw−Eff) ·
  JunkFrac%(자기 점유 중 q<.15) · JunkOpen%(동점/열세 국면 한정) · FieldTilt%.
사용: python junk_possession.py [--match <id>]   (생략 시 데이터 최다 경기)
"""
import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/opc/football")
from analysis import corpus, metrics
from analysis.sources_whoscored import _shot_geometry

ON_BALL = {"Pass", "Carry", "TakeOn", "BallTouch", "Shot", "Dribble"}
GRID = metrics.load_xt()
ROWS, COLS = GRID.shape
JUNK_Q = 0.15   # 이 q 미만 = 정크 시퀀스
PITCH_L, PITCH_W = 120.0, 80.0   # DB 좌표계(_shot_geometry는 0~100 기대 → 변환)

# ★슛 가치 = 이 피드의 flat 0.05 플레이스홀더가 아니라, 우리가 학습한 xG 모델을
#   슛 위치로 추론해 쓴다(바디/상황은 최빈값 foot·open_play 근사). 로드 실패 시 이진 폴백.
try:
    from analysis import xg as _XG
    _XG._load("gbm")
    _HAS_XG = True
except Exception:
    _HAS_XG = False


def real_shot_xg(df):
    """Shot 이벤트 → 우리 xG 모델 추론값 dict{df_index: xg}. (모델 없으면 빈 dict.)"""
    sh = df[df["type_name"] == "Shot"]
    sh = sh[sh["x"].notna() & sh["y"].notna()]
    if sh.empty or not _HAS_XG:
        return {}
    rows = []
    for x, y in zip(sh["x"], sh["y"]):
        dist, ang = _shot_geometry(x / PITCH_L * 100, y / PITCH_W * 100)
        rows.append(dict(distance=dist, angle=ang, body="foot", situation="open_play",
                         assisted=0, first_touch=0, volley=0))
    preds = _XG.predict(pd.DataFrame(rows))
    return dict(zip(sh.index, (float(p) for p in preds)))


def xtv(x, y):
    if pd.isna(x) or pd.isna(y):
        return np.nan
    r, c = metrics._cell(x, y, ROWS, COLS)
    return float(GRID[r, c])


def in_box(x, y):
    return x >= 102 and 18 <= y <= 62      # 상대 박스(120×80)


def goals(df):
    """(minute, second, team_name) 골 리스트 — outcome_name=='Goal'인 슛."""
    g = df[(df["type_name"] == "Shot") & (df["outcome_name"] == "Goal")]
    return sorted((int(r.minute), int(r.second), r.team_name) for r in g.itertuples())


def sequences(df):
    """team_name 연속 구간 = possession. 각 시퀀스 dict 리스트 반환(스코어 상태 태깅)."""
    df = df.sort_values(["minute", "second"]).reset_index(drop=True)
    gls = goals(df)
    xgmap = real_shot_xg(df)          # df_index → 우리 xG 모델 추론값
    pid = (df["team_name"] != df["team_name"].shift()).cumsum()
    seqs = []
    for _, g in df.groupby(pid):
        onball = g[g["type_name"].isin(ON_BALL)]
        if onball.empty:
            continue
        xt = [xtv(x, y) for x, y in zip(onball["x"], onball["y"])]
        xt = [v for v in xt if not np.isnan(v)]
        if not xt:
            continue
        team = g["team_name"].iloc[0]
        t0 = (int(onball["minute"].iloc[0]), int(onball["second"].iloc[0]))
        t1 = (int(onball["minute"].iloc[-1]), int(onball["second"].iloc[-1]))
        gf = sum(1 for m, s, tm in gls if (m, s) <= t0 and tm == team)
        ga = sum(1 for m, s, tm in gls if (m, s) <= t0 and tm != team)
        shot_idx = g.index[g["type_name"] == "Shot"]
        shot_xg = max((xgmap.get(i, 0.0) for i in shot_idx), default=0.0)
        seqs.append(dict(
            team=team,
            n=len(onball),
            start_xt=xt[0], peak_xt=max(xt),
            shot=int(len(shot_idx) > 0),
            shot_xg=float(shot_xg),                           # ★우리 xG 모델(슛 질)
            box=any(in_box(x, y) for x, y in zip(onball["x"], onball["y"]) if not pd.isna(x)),
            final_third=float(np.mean(onball["x"] >= 80)),   # 최종third 비율
            state=gf - ga,                                    # 시퀀스 시작 시점 득실차(자기 관점)
            start_min=t0[0],                                  # 시작 분(전/후반 분리용)
            start_t=t0[0] * 60 + t0[1], end_t=t1[0] * 60 + t1[1],   # 절대 초(연쇄 연결용)
        ))
    return seqs


def value(s):
    """시퀀스 잠재-위협 가치(비음수).
    = peak_xt 상승(잠재/counterfactual) + 우리 xG모델 슛질(실현) + 박스진입.
    슛질은 xG 모델(0~0.7 가중); 모델 없으면 이진 0.08로 폴백.
    ★box 가중 0.10 = junk_validate 로지스틱(AUC 0.91)이 박스진입을 강한 위협신호로
    지목 → 종전 0.03은 과소가중. final_third는 value에 안 넣음(field_tilt로 붕괴 방지)."""
    shot_term = 0.7 * s.get("shot_xg", 0.0) if _HAS_XG else 0.08 * s["shot"]
    return max(0.0, s["peak_xt"] - s["start_xt"]) + shot_term + 0.10 * s["box"]


def mark_redemption(seqs, gap_s=25, redeem_gain=0.04):
    """★다음-소유 연쇄로 정크를 '죽은 정크' vs '셋업 정크'로 분해 (정크 특화 확장).

    정크(q<JUNK_Q) 시퀀스라도 같은 팀이 gap_s 초 안에 **다시 소유해 위협**(peak 상승≥redeem_gain
    또는 박스 진입)에 도달했다면 = 무의미 순환이 아니라 셋업(빌드업) → 구제(dead_junk=False).
    표준 possession-value(VAEP류 next-k)와 달리 '정크 라벨'을 소유 경계 넘어 재판정하는 게 핵심.
    선행: q 부여됨. seqs 시간순 가정."""
    for i, s in enumerate(seqs):
        s["dead_junk"] = bool(s.get("q", 1.0) < JUNK_Q)
        if not s["dead_junk"]:
            continue
        for j in range(i + 1, len(seqs)):
            nx = seqs[j]
            if nx["start_t"] - s["end_t"] > gap_s:
                break                              # 시간순 → 이후는 더 멂
            if nx["team"] != s["team"]:
                continue                           # 상대의 짧은 개입은 건너뜀
            gain = max(0.0, nx["peak_xt"] - nx["start_xt"])
            if gain >= redeem_gain or nx["box"]:
                s["dead_junk"] = False             # 셋업으로 구제
            break                                  # 같은 팀 '다음' 소유 하나만
    return seqs


def analyze(df, scale=None):
    """시퀀스 → 팀별 지표 dict. scale=코퍼스 p90(없으면 경기 내 p90)."""
    seqs = sequences(df)
    if not seqs:
        return None
    val = np.array([value(s) for s in seqs])
    sc = scale or (np.percentile(val, 90) or 1e-6)
    for s, vi in zip(seqs, val):
        s["val"] = float(vi)
        s["q"] = float(np.clip(vi / sc, 0, 1))
    mark_redemption(seqs)                          # 죽은 정크 vs 셋업 정크 분해

    teams = sorted({s["team"] for s in seqs})
    if len(teams) != 2:
        return None
    tot_ev = sum(s["n"] for s in seqs)
    tot_w = sum(s["n"] * s["q"] for s in seqs)
    out = {}
    for t in teams:
        ts = [s for s in seqs if s["team"] == t]
        ev = sum(s["n"] for s in ts)
        w = sum(s["n"] * s["q"] for s in ts)
        junk_ev = sum(s["n"] for s in ts if s["q"] < JUNK_Q)
        open_ts = [s for s in ts if s["state"] <= 0]          # 동점/열세 국면만
        open_ev = sum(s["n"] for s in open_ts)
        open_junk = sum(s["n"] for s in open_ts if s["q"] < JUNK_Q)
        open_dead = sum(s["n"] for s in open_ts if s.get("dead_junk"))   # 셋업 제외한 죽은 정크
        out[t] = dict(
            raw=ev / tot_ev * 100 if tot_ev else 0,
            eff_share=w / tot_w * 100 if tot_w else 0,
            efficiency=w / ev if ev else 0,
            junk_frac=junk_ev / ev * 100 if ev else 0,
            junk_open=open_junk / open_ev * 100 if open_ev else 0,   # ★국면정규화
            junk_dead=open_dead / open_ev * 100 if open_ev else 0,   # ★셋업 제외(다음-소유 연쇄)
            open_share=open_ev / ev * 100 if ev else 0,              # 점유 중 동점/열세 비중
            field_tilt=float(np.average([s["final_third"] for s in ts],
                                        weights=[s["n"] for s in ts]) * 100),
            box_seq=sum(1 for s in ts if s["box"]),
            shots=sum(s["shot"] for s in ts),
            nseq=len(ts), ev=ev,
        )
    return out, teams, seqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", type=int, default=0)
    args = ap.parse_args()

    import duckdb
    c = duckdb.connect("/home/opc/football/analysis/_data/whoscored.duckdb", read_only=True)
    mid = args.match or c.execute(
        "select match_id from events group by 1 order by count(*) desc limit 1").fetchone()[0]
    meta = c.execute("select home,away,home_score,away_score from matches where match_id=?", [mid]).fetchone()
    res = analyze(corpus.events_of(mid, con=c))
    if not res:
        print("분석 불가"); return
    rows, teams, _ = res

    print(f"=== 정크 점유 지수 — {meta[0]} {meta[2]}-{meta[3]} {meta[1]} (match {mid}) ===")
    print(f"{'팀':<14}{'Raw%':>7}{'Eff%':>7}{'Junk%p':>8}{'효율':>7}{'정크%':>7}{'정크(동점/열세)%':>16}{'Tilt%':>8}{'슛':>5}")
    for t in teams:
        r = rows[t]
        junk = r["raw"] - r["eff_share"]
        print(f"{t:<14}{r['raw']:>7.1f}{r['eff_share']:>7.1f}{junk:>+8.1f}{r['efficiency']:>7.2f}"
              f"{r['junk_frac']:>7.0f}{r['junk_open']:>16.0f}{r['field_tilt']:>8.1f}{r['shots']:>5}")
    print("\nJunk%p=점유율−위협가중점유(허수) · 효율=점유의질(0~1) · 정크%=자기점유 중 q<.15")
    print("정크(동점/열세)%=리드지키기 제외한 '진짜 실패' 순환 · Tilt=최종third 비율")


if __name__ == "__main__":
    main()
