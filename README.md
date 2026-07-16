# Space-Creating versus Dead Possession

An off-ball **possession-quality** framework for football: separate *unlucky*
possession (that manufactured space it failed to convert) from *dead*
possession (that never moved the opponent's block) — a distinction on-ball
possession value (EPV / VAEP / OBV) cannot make.

Possession percentage is the most-cited and most-misleading number in the game.
Existing possession-value models price the **on-ball** action; the question a
sterile possession actually poses is **off-ball**: did holding the ball create
space?

We answer in two layers.

## Two layers

**1. Event-side junk-possession index.** Split possession into sequences, price
each by its counterfactual threat potential under an expected-threat grid, and —
after reconstructing the live scoreline to drop lead-protecting circulation —
flag low-threat sequences in tied-or-losing game states (`junk-open`).

On the 2026 FIFA World Cup (101 matches, 202 team-matches):

| metric | Team xG | Goals | Points | xG diff |
|---|---|---|---|---|
| `junk-open` | −0.38 | −0.37 | **−0.39** | −0.52 |

Among teams above 55% possession, splitting by efficiency separates the outcome:

![event quadrant](figures/event_quadrant.png)

*Junk dominators (n=8): 0.62 goals, 1.00 points. Efficient dominators (n=62):
2.24 goals, 2.23 points. Possession without threat is close to worthless.*

**Not a repackaging of on-ball value.** With team offensive VAEP and field tilt
held fixed in the same regression, `junk-open` stays a strong negative predictor
of points (p < 10⁻⁴) while **VAEP itself is not significant** (p = 0.40). A
surface correlation of ~0.5 between VAEP and the junk metrics collapses to
nothing once both share a regression — the index carries off-ball information
on-ball action value does not.

**2. Spatial Space-Creation Index (SCI).** For a flagged window, project
broadcast video to pitch coordinates and measure whether the possession pushed
the opponent's block back:

> SCI = Δ(possessor's attacking-third control) + Δ(opponent's advanced-zone collapse)

![sci contrast](figures/sci_contrast.png)

*Two flagged junk windows from the same match (Germany–Paraguay), opposite
verdicts. Left: Paraguay creates space (SCI +18.0). Right: Germany's possession
is dead (SCI −24.4) — it held 73% of the ball and went out on penalties.*

Across 31 flagged windows from nine World Cup matches: **74% spatially dead, 19%
weak progression, 6% genuine space creation** the event flag alone would
misclassify.

## Repository layout

```
src/
  junk_possession.py   # the index: sequence value, junk-open, score-state normalisation
  junk_rank.py         # corpus-wide ranking (per-tournament)
  junk_validate.py     # validation: correlations, weight learning, partial regression,
                       #             VAEP orthogonality, out-of-sample, redemption
  space_signature.py   # Space-Creation Index from projected spatial series
paper/
  latex/main.tex       # the paper (arXiv source) + refs.bib + figures
  possession_quality_EN.md / _KO.md   # summaries
figures/               # figures used in the README and paper
```

## Reproducibility and data

The event-side index, validation battery (including the VAEP orthogonality
regression), and tournament aggregation run on CPU. The **event corpus**
(WhoScored-derived) and the **broadcast footage** used for the spatial layer are
**not redistributable**, so the scripts here are released as the reference
implementation described in the paper rather than a turnkey pipeline; they depend
on an event store and, for SCI, on projected spatial series produced by a
broadcast GSR pipeline. No GPU or cloud expenditure was used for any experiment.

The VAEP baseline is our own implementation of Decroos et al. (2019); `xT`
follows Karun Singh's expected-threat grid.

## Citation

See `CITATION.cff`. Paper: *Space-Creating versus Dead Possession: An Off-Ball
Possession-Quality Index for Broadcast Football* (Seongjin Choi, 2026).

## License

MIT (`LICENSE`).
