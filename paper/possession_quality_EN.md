# Space-Creating versus Dead Possession: An Off-Ball Possession-Quality Index for Broadcast Football

*Draft — target: arXiv preprint / SSAC research track. Full paper: `latex/main.tex`. Code: `../src/`.*

## Abstract

Ball possession is the most-cited and most-misleading number in football: sixty percent of the ball spent recycling in one's own half is not the same as sixty percent spent pinning the opponent back. Existing possession-value frameworks — expected threat, VAEP, on-ball value — refine the count by pricing *on-ball* actions, but they are blind to the off-ball question a sterile possession actually poses: did holding the ball *create space*, or was the circulation genuinely dead? We answer this in two layers. First, an event-side **junk-possession index** decomposes possession into sequences, prices each by its counterfactual threat potential under an expected-threat grid, and — after reconstructing the live scoreline to exclude lead-protecting circulation — flags low-threat sequences in tied-or-losing game states. On the 2026 FIFA World Cup (101 matches, 202 team-matches) this flag correlates negatively with points (r = −0.39) and expected-goal difference (r = −0.52); teams above 55% possession with below-median efficiency average 0.62 goals and 1.00 points versus 2.24 and 2.23 for efficient dominators. Crucially, the flag is not a repackaging of on-ball value: with team offensive VAEP and field tilt held fixed in the same regression, the junk flag remains a strong negative predictor of points (p < 10⁻⁴) while VAEP itself is not significant — the index carries off-ball information that on-ball action value does not. Second, for a flagged window we resolve *why* it was junk by projecting broadcast video to pitch coordinates and measuring a **Space-Creation Index** (SCI): whether the possession pushed the opponent's block back. Across 31 flagged windows from nine World Cup matches, 74% are spatially confirmed dead, 19% weak progression, and 6% genuine space creation that the event flag alone would misclassify — including a possessing team that dominated 73% of the ball and went out on penalties (two windows, both spatially dead) set against an unlucky window that created space without a shot. The two layers together separate "unlucky" from "sterile" possession, a distinction on-ball possession value cannot make.

## Contributions

1. **An event-side junk-possession index** that flags low-threat possession in decision-relevant game states, with a validation battery showing it predicts outcomes, survives out-of-sample tests, and — the central claim — is *orthogonal* to on-ball possession value (controlling for VAEP does not remove its predictive content).
2. **A spatial Space-Creation Index** computed from broadcast video via a CPU-only GSR pipeline, which adjudicates *why* a flagged possession was junk (space-creating or dead), and a tournament-scale study of 31 flagged windows from nine World Cup matches.

## The index (event layer)

Each possession sequence *s* is priced by

```
value(s) = max(0, xT_max − xT_start)      # counterfactual threat potential (credited even without a shot)
         + 0.7 · xG(s)                    # realised shot quality (our own xG model)
         + 0.10 · 1[box entry]            # penalty-box entry
```

Sequence values are normalised by the corpus 90th percentile to q ∈ [0,1]; q < 0.15 is a *junk sequence*. Reconstructing the live scoreline from goal events, the headline metric **junk-open** counts junk-sequence share only in tied-or-losing states — circulation with no excuse.

## Validation (202 team-matches)

- **Correlations.** junk-open is negatively associated with xG (−0.38), goals (−0.37), points (−0.39), xG difference (−0.52). Threat-weighting helps (effective possession tracks xG at 0.55 vs raw 0.49). Field tilt explains xG (0.59) but not points (0.19).
- **Quadrant.** Among 70 teams above 55% possession, the 8 low-efficiency "junk" dominators averaged 0.62 goals / 1.00 points; the 62 efficient dominators averaged 2.24 / 2.23.
- **Learned weights.** A logistic model (sequence → shot) reaches 5-fold AUC 0.907; box entry was under-weighted (0.03 → 0.10). Final-third share is excluded to avoid collapsing the index into field tilt.
- **Not territory.** Partial regression: junk-open predicts points (β = −0.023, p = 0.008) with field tilt controlled; for xG difference the roles reverse (tilt significant, junk absorbed). "Did it create chances" is territory; "did it win" is possession quality.
- **Orthogonality to VAEP.** Team offensive VAEP correlates with the possession-quality metrics at the surface (r = −0.49 with junk-open, +0.58 with efficiency) — a genuine competitor. But with VAEP and field tilt controlled, junk-open predicts points at p < 10⁻⁴ while VAEP is not significant (p = 0.40), and efficiency predicts xG difference at p < 10⁻⁴ while VAEP is not significant (p = 0.46). **This is the paper's central quantitative claim.**
- **Out-of-sample.** First-half efficiency predicts second-half xG (r = +0.33); a team's mean junk-open in *other* matches predicts this match's points (r = −0.31). Junk possession is a persistent team trait, not a post-hoc description.
- **Dead vs set-up.** Only 9% of tied-or-losing junk is "redeemed" by re-possession within 25 s; 91% is genuinely dead.

## The Space-Creation Index (spatial layer)

For a flagged window with possessing team *P*:

```
SCI = Δ_own + Δ_opp
  Δ_own = change in P's pitch-control share of the attacking third (first vs last third of the window)
  Δ_opp = collapse of the opponent's control share in its own advanced zone
```

Large SCI = the block was pushed back (space creation, unlucky); SCI ≈ 0 = the block never moved (dead junk). Operational bins: space creation (≥ +12), weak progression (+4 to +12), dead (< +4). Pitch control is computed from a CPU-only broadcast GSR pipeline (PnLCalib calibration, BoT-SORT tracking, colour team assignment, shot-change gating, training-free off-screen ghosting).

## Tournament-scale results (9 matches, 31 windows)

**74% spatially dead, 19% weak progression, 6% genuine space creation.** Stable as the corpus grew from six matches (21 windows; 71/24/5) to nine (31; 74/19/6).

- **Germany** held 73% against Paraguay, drew 1–1, and were eliminated on penalties; both flagged windows are spatially dead (SCI −24.4, −14.2). Scoring the shootout as a loss (not a draw) matters — a common miscoding would blunt exactly this signal.
- **Paraguay** (same match, 76:01) scores SCI +18.0 — space creation the event flag would have called failure. This is the 6% the two-layer design exists for.
- **Norway** beat Brazil despite a high junk rate; all four flagged windows are dead — the flags were correct, and the win came from the non-junk moments the index does not flag.
- Event-side contrast: South Africa (57%, efficiency 0.27) is textbook junk; South Korea (57%, efficiency 0.41) is not — same possession, same result, opposite diagnosis.

## Limitations

The event index is a ball-only approximation; the spatial layer supplies off-ball evidence only on short flagged windows (a macro/micro hybrid, not full-match tracking). The xG term uses shot location only; sequence weights and thresholds are round operational values. Team assignment degrades for low-contrast kits (three windows excluded, plus one on clip quality); extra-time windows are excluded. Systematic imputation-sensitivity analysis, velocity-aware space *value*, and a learned replacement for the thresholds are future work.
