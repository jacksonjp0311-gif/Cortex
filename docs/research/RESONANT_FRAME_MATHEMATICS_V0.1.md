# Resonant Frame Mathematics v0.1

Engineering specification for Cortex v7.3.0. Thresholds are **bootstrap defaults**, not universal constants.

## 1. Notation

Frame \(F=\{x_i(\tau)\}\) for channels \(i=1..K\), ticks \(\tau=1..W\).  
Activity \(x_i(\tau)\in[0,1]\), reliability \(r_i\in[0,1]\).  
\(\varepsilon=10^{-12}\). Natural logs unless noted.

## 2. Channel sampling

Bounded \(K\in[6,12]\). One sample vector per fusion/activation tick. Paths live in metadata.

## 3. Baseline distributions

Per channel, categorical over `event_key × activity_bin` (8 bins). Cap 64 event keys + OTHER. Rolling blend updates only under epoch-current, non-stale, non-corrupt conditions.

## 4. Jensen–Shannon nonrandomness

\[
M=\tfrac12(P^F+P^B),\quad
\mathrm{JSD}=\tfrac12\mathrm{KL}(P^F\|M)+\tfrac12\mathrm{KL}(P^B\|M),\quad
\nu_i=\mathrm{JSD}/\ln 2\in[0,1]
\]

\[
N_F=\frac{\sum_i r_i\nu_i}{\sum_i r_i}
\]

only over channels with warmed baseline; else \(N_F=\mathrm{null}\).

\[
\dot N_F=\min\bigl(1,|N_F-N_{\mathrm{prev}}|/(q_{95}(\Delta N)+\varepsilon)\bigr)
\]

Default \(q_{95}=0.12\) until calibrated.

## 5. Lagged coordination matrix

For nonconstant pairs, Pearson \(c_{ij}(\ell)\) for \(\ell\in\{-L_{\max},\ldots,L_{\max}\}\), \(L_{\max}=3\), ≥5 overlap.

\[
\rho_{ij}=\max_\ell|c_{ij}(\ell)|,\quad
\ell^*_{ij}=\arg\max_\ell|c_{ij}(\ell)|
\]

Tie-break: smallest \(|\ell|\), then negative lag, then lexical channels.  
\(w_{ij}=r_i r_j\).

## 6. Integration

\[
I_F=\frac{\sum_{i<j}w_{ij}\rho_{ij}}{\sum_{i<j}w_{ij}},\quad
S_F=\frac{\sum_{i<j}w_{ij}|c_{ij}(0)|}{\sum_{i<j}w_{ij}},\quad
L_F=\frac{\sum_{i<j}w_{ij}|\ell^*_{ij}|/L_{\max}}{\sum_{i<j}w_{ij}}
\]

## 7. Effective-rank differentiation

Standardize eligible nonconstant rows → \(Z\).  
\(C=ZZ^\top/(W-1)\). Eigenvalues \(\lambda_1\ge\cdots\ge\lambda_{K'}\ge0\) (tiny negatives clipped).

\[
p_j=\lambda_j/\sum_m\lambda_m,\quad
H_\lambda=-\sum_j p_j\ln(p_j+\varepsilon),\quad
\mathrm{erank}=e^{H_\lambda}
\]

\[
D_F=\frac{\mathrm{erank}-1}{K'-1}\quad(K'>1)
\]

## 8. Common-mode domination

\[
M_F=\lambda_1/\sum_j\lambda_j
\]

## 9. Participation entropy

\[
\pi_i=\frac{r_i\sum_\tau x_i(\tau)}{\sum_j r_j\sum_\tau x_j(\tau)},\quad
H_P=\frac{-\sum_i\pi_i\ln(\pi_i+\varepsilon)}{\ln K}
\]

## 10. Active coordination graph

Edge if \(\rho_{ij}\ge\tau_\rho\) (default 0.45).  
\(G_F=|\mathrm{LCC}|/K'\).

## 11. Evidence-memory comparator

Distributions \(p_E\) (verified external only), \(p_M\) (memory families).

\[
A_F=1-\mathrm{JSD}(p_E\|p_M)/\ln 2,\quad
C_F=\frac{\mathrm{contradictory\_matched\_mass}}{\mathrm{total\_matched\_mass}+\varepsilon},\quad
Q_F=A_F(1-C_F)
\]

If either side absent: `comparator_available=false`, \(A_F=Q_F=\mathrm{null}\).

## 12. Transition pressure

\[
T_F=0.40\Delta_A+0.30\Delta_P+0.20\Delta_N+0.10\Delta_q
\]

(components clipped to [0,1]). Verified epoch drift ⇒ \(T_F=1\). Weights versioned in threshold config digest.

## 13. Frame vector

\[
R_F=(N_F,\dot N_F,I_F,S_F,L_F,D_F,M_F,H_P,G_F,Q_F,\eta_E,\eta_M,T_F)
\]

Never blended into constitutional authority.

## 14. Deterministic classification

Order: INDETERMINATE → TRANSITION → QUIESCENT → STALE_ECHO → OVERBOUND → FRAGMENTED → COHERENT_DIFFERENTIATED → else INDETERMINATE.  
See `classify_frame` in `cortex/resonant_frame.py`.

## 15. Calibration

After ≥16 valid epoch-current frames: shadow quantile candidates. Never auto-promote. Preserve defaults. No learning from SIMULATED as live evidence.

## 16. Numerical edge cases

- Constant channels excluded from pairs/eigen.
- Null metrics never invented as midpoints.
- Empty comparator → unavailable.
- Division by zero guarded by \(\varepsilon\).

## 17. Complexity bounds

\(O(K^2 W L)\) with \(K\le12\), \(W\le32\), \(L\le3\). Full eigen only on frame close/cadence, not every token.
