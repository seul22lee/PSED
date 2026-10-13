# Cross-paper comparisons we could draw from the Cremers 2019 review

Notes from reading Cremers et al., Appl. Phys. Rev. 6, 021302 (2019). The factual claims below (marked "Claim:") are not yet verified; check each against the review and the source papers.

## A. What Cremers wanted but could not do

### 1. One process across several test structures (benchmark)
- In the outlook (Sec. VII) the authors say it would be useful to measure one process on different test structures and cross-compare. In Sec. IV A they note that the coated EAR of TMA/H2O ranges from 5 to 1750 depending on structure and conditions.
- Claim: of the 12 TMA/H2O rows in Table II, only 6 give an exposure. The record row (AAO, 1750:1) has none. The variable this comparison needs most is already missing at the review stage.
- What we can do: go back to the sources and fill the blanks, or confirm that the source does not state them; then put coated EAR against exposure and compare with Gordon's a² scaling (the Monte Carlo curves of Fig. 17).
- Units: the tables give exposure in 10³ L (1 Pa·s ≈ 7500 L). The conversion printed in Sec. II D looks garbled in the extracted text; check it on the page.

### 2. Automatic EAR conversion and a check of the tables
- Cremers gives EAR formulas per structure (Sec. II G): circular or square hole L/w, trench L/(2w), elongated hole L(w+z)/(2wz), pillar arrays from Monte Carlo.
- The EAR values in Tables II–IV were converted by the authors. If the KB computes EAR from the source's L, w and structure type with a transform, it can reproduce and check the review's tables.
- Example: Werbrouck 2021 (10.1116/6.0001094) states AR 20 and EAR 10 for a trench, consistent with the trench formula.

### 3. Continuing the tables after 2019 (living table)
- The review's tables end in early 2019. The 44 papers already hold candidate new rows:
  - Mo in a trench, top/side/bottom 100/95/90% (10.1116/6.0002804)
  - WCx in a trench, step coverage about 80% (10.1021/acs.chemmater.6c00816)
  - AlN with Kr co-flow, step coverage 1.6 (10.1021/acs.jpclett.4c03545)
  - PD50% of three plasma LHAR papers (10.1021/acs.jpcc.9b08176, 10.1063/5.0168768, 10.1021/acs.jpcc.5c06502)
- "The review's tables, updated automatically" is a candidate headline result for the perspective paper.

## B. What only shows when tables are joined

### 4. Recombination probability against coated EAR (Table IV × Table VII)
- Claim: Cremers states only qualitatively that metal surfaces have a high r, so plasma ALD of metals reaches a lower coated EAR (largest 30 for oxides, 17 for metals).
- Attaching the r of the deposited material's surface (Table VII) to each process's coated EAR (Table IV) would test this quantitatively.
- Putting the r values the 44 papers obtain from LHAR slopes (case C2) beside the older Table VII values also compares measurement methods. Example: O on alumina is 0.0021 in one source and 0.0097 in another.

### 5. Same film, different oxidant (Table II × III × IV)
- Some films appear with thermal, ozone and plasma processes. Claim: for Al2O3 the largest coated EAR is about 1750, 20 and 30 respectively. TiO2, HfO2, Ru, Pt and ZnO also have pairs.
- Only pairs with matching structure and exposure can show the effect of the process mode. The review compares maxima without matching.

### 6. Why sticking probabilities scatter (Table V)
- Claim: TMA alone has 8 values from 0.001 to 0.1 (DFT 0.1–0.9), and Cremers only suggests the methods may differ.
- A definition issue is mixed in. Table V says "sticking probability", but, claim: Ylilammi's 0.00572 is an initial sticking coefficient s0. The review itself defines s and s0 separately.
- Tagging each value with method, model, data_kind and s/s0 may explain part of the spread. Adding post-2019 values (Yim 2020, sse.2022, the slope method of d1cp04758b) gives a literature prior for the warm start of the twin's parameter estimation (Case 2-2).

## C. About the nature of the data itself

### 7. Many coated EAR values are lower bounds
- By the table headers' definition, coated EAR equals the structure's EAR when the structure was fully coated (including "Conformal"), and is PD50% only when coverage was incomplete. So "1750" means "at least 1750", while "75 (D)" is a measured value.
- Mixing the two on one plot is wrong. This supports a qualifier on coated_aspect_ratio such as {basis=complete (lower bound) | PD50%}. Another case of "comparable is not identical".

### 8. The "(D)" mark is a collection priority list
- (D) means the paper reported a thickness profile. These are the papers we can digitize and use for model calibration.
- Cremers Sec. VI B 3: fixing s0 needs dense points in the slope region (Fig. 22). Counting the points in the slope region of each profile gives a score for whether it is fit for calibration, a direct input to the twin.
- This list decides which of the 283 papers to request through the library first.

### 9. Growth type classification (Fig. 4)
- The concept of telling diffusion-, reaction- and recombination-limited growth apart by profile shape (Sec. II F). Together with case N7 (parameter sensitivity), it gives a case that classifies "which type is this process" across the literature.
