# Space-Creating versus Dead Possession: An Off-Ball Possession-Quality Index for Broadcast Football

*Draft — target: arXiv preprint / SSAC research track. Full paper: `latex/main.tex`. Code: `../src/`.*

## Abstract

Ball possession is the most-cited and most-misleading number in football: sixty percent of the ball spent recycling in one's own half is not the same as sixty percent spent pinning the opponent back. Existing possession-value frameworks — expected threat, VAEP, on-ball value — refine the count by pricing *on-ball* actions, but they are blind to the off-ball question a sterile possession actually poses: did holding the ball *create space*, or was the circulation genuinely dead? We answer this in two layers. First, an event-side **junk-possession index** decomposes possession into sequences, prices each by its peak threat gain (credited even without a shot) under an expected-threat grid, and — after reconstructing the live scoreline to exclude lead-protecting circulation — flags low-threat sequences in tied-or-losing game states. On the 2026 FIFA World Cup (103 matches, 206 team-matches) this flag correlates negatively with points (r = −0.37) and expected-goal difference (r = −0.51); team-matches above 55% possession with below-median efficiency average 0.62 goals and 1.00 points versus 2.24 and 2.24 for efficient dominators. Crucially, the flag is not a repackaging of on-ball value: with team offensive VAEP and field tilt held fixed in the same regression, the junk flag remains a strong negative predictor of points (p < 10⁻⁴, and under match-clustered standard errors) while VAEP itself is not significant — the index adds outcome-relevant information beyond this on-ball action-value model. Second, for a flagged window we resolve *why* it was junk by projecting broadcast video to pitch coordinates and measuring a **Space-Creation Index** (SCI): a net pitch-control change capturing whether the possession seized space or pushed the opponent's block back. Across 31 flagged windows from nine World Cup matches, 74% are spatially non-space-creating, 19% weak progression, and 6% space-creating windows the event flag alone would score as failure — including a possessing team that dominated 73% of the ball and went out on penalties (two non-creating windows) set against a space-creating window that produced no shot. The two layers together separate "unlucky" from "sterile" possession, a distinction on-ball possession value cannot make.

## Contributions

1. **An event-side junk-possession index** that flags low-threat possession in decision-relevant game states, with a validation battery showing it predicts outcomes, survives out-of-sample tests, and — the central claim — is *not reducible* to on-ball possession value (controlling for VAEP does not remove its predictive content).
2. **A spatial Space-Creation Index** computed from broadcast video via a CPU-only GSR pipeline, which adjudicates *why* a flagged possession was junk (space-creating or not), and a tournament-scale study of 31 flagged windows from nine World Cup matches.

## The index (event layer)

Each possession sequence *s* is priced by

```
value(s) = max(0, xT_max − xT_start)      # peak threat gain (credited even without a shot)
         + 0.7 · xG(s)                    # realised shot quality (our own xG model)
         + 0.10 · 1[box entry]            # penalty-box entry
```

Sequence values are divided by the corpus 90th percentile and clipped to q ∈ [0,1]; q < 0.15 is a *junk sequence*. Reconstructing the live scoreline from goal events, the headline metric **junk-open** counts junk-sequence share only in tied-or-losing states — circulation with no excuse.

## Validation (206 team-matches)

- **Correlations.** junk-open is negatively associated with xG (−0.38), goals (−0.38), points (−0.37), xG difference (−0.51). Threat-weighting helps in this sample (effective possession tracks xG at 0.56 vs raw 0.50). Field tilt correlates with xG (0.58) but weakly with points (0.18).
- **Quadrant.** Among 71 team-match observations above 55% possession, the 8 below the corpus-wide median efficiency averaged 0.62 goals / 1.00 points; the 63 above it averaged 2.24 / 2.24. (Central regressions hold under match-clustered standard errors.)
- **Learned weights.** A logistic model (sequence → shot) reaches 5-fold AUC 0.907; box entry was under-weighted (0.03 → 0.10). Final-third share is excluded to avoid collapsing the index into field tilt.
- **Not territory.** Partial regression: junk-open predicts points (β = −0.020, p = 0.017) with field tilt controlled; for xG difference the roles reverse (tilt significant, junk absorbed). "Did it create chances" is territory; "did it win" is possession quality.
- **Orthogonality to VAEP.** Team offensive VAEP correlates with the possession-quality metrics at the surface (r = −0.49 with junk-open, +0.58 with efficiency) — a genuine competitor. But with VAEP and field tilt controlled, junk-open predicts points at p < 10⁻⁴ (also under match-clustered SEs) while VAEP is not significant (p = 0.34), and efficiency predicts xG difference at p < 10⁻⁴ while VAEP is not significant (p = 0.46). **This is the paper's central quantitative claim.**
- **Out-of-sample.** First-half efficiency predicts second-half xG (r = +0.32); a team's mean junk-open in *other* matches predicts this match's points (r = −0.30). Junk possession behaves like a team trait (a cross-fitted association), not a post-hoc description.
- **Dead vs set-up.** Only 9% of tied-or-losing junk is "redeemed" by re-possession within 25 s; the remaining 91% is not redeemed under this rule.

## The Space-Creation Index (spatial layer)

For a flagged window with possessing team *P*:

```
SCI = Δ_own + Δ_opp
  Δ_own = change in P's pitch-control share of the attacking third (first vs last third of the window)
  Δ_opp = collapse (early − late) of the opponent's control share in its own attacking third
```

SCI is a net two-zone change: large positive = the possession seized the attacking third and/or pushed the block back (space-creating); ≈ 0 = the block held shape; strongly negative = the possessing team lost control while the block advanced. Operational bins: space creation (≥ +12), weak progression (+4 to +12), non-space-creating (< +4). All windows are already junk-flagged; SCI subdivides them. Pitch control is computed from a CPU-only broadcast GSR pipeline (PnLCalib calibration, BoT-SORT tracking, colour team assignment, shot-change gating, training-free off-screen ghosting).

## Tournament-scale results (9 matches, 31 windows)

**74% spatially non-space-creating, 19% weak progression, 6% space-creating.** Proportions shifted only modestly as the sample grew from six matches (21 windows; 71/24/5) to nine (31; 74/19/6).

- **Germany** held 73% against Paraguay, were held level at 1–1, and lost the shootout; both flagged windows are strongly negative — Germany lost attacking-third control while Paraguay's block advanced (SCI −24.4, −14.2). Scoring the shootout as a loss (not a draw) matters — a common miscoding would blunt exactly this signal.
- **Paraguay** (same match, 76:01) scores SCI +18.0 — space-creating (Δ_own +28, though the opponent block did not itself collapse) that the event flag would have called failure. This is the 6% the two-layer design exists for.
- **Norway** beat Brazil despite a high junk rate; all four flagged windows are non-space-creating — the flags correctly mark the possessions that created no space, and Norway still won elsewhere.
- Event-side contrast: South Africa (57%, efficiency 0.27) is textbook junk; South Korea (57%, efficiency 0.41) is less sterile by this index — same possession, same result, opposite diagnosis.

## Limitations

The event index is a ball-only approximation; the spatial layer supplies off-ball evidence only on short flagged windows (a macro/micro hybrid, not full-match tracking). The xG term uses shot location only; sequence weights and thresholds are round operational values. Team assignment degrades for low-contrast kits (three windows excluded, plus one on clip quality); extra-time windows are excluded. Systematic imputation-sensitivity analysis, velocity-aware space *value*, and a learned replacement for the thresholds are future work.
