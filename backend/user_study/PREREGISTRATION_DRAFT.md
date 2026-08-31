# Preregistration Draft

Freeze this document, the commit identifier, and `task_manifest.csv` before the first participant.

## Confirmatory decisions

- Primary outcome: accuracy on change-localization trials.
- Primary contrast: DeltaAnnulus minus geographic map.
- Population: all participants remaining after the protocol's outcome-independent exclusions.
- Model: binomial mixed-effects regression with participant and stimulus random intercepts, plus participant condition slope when convergence permits.
- Alpha: 0.05, two-sided.
- Missing responses: treated as incorrect for the primary intention-to-test analysis; complete-case analysis is secondary.
- Outliers: no response-time trimming in the primary accuracy model. For timing, correct trials below 200 ms are treated as technical errors; otherwise log time is modeled without upper trimming and checked with a robust sensitivity model.
- Multiplicity: the primary contrast is unadjusted; secondary task/outcome contrasts use Holm correction within outcome family.

## Planned robustness checks

- AB versus BA condition order;
- visualization/GIS experience interaction;
- Hubei versus NCEP dataset interaction;
- complete-case versus missing-as-incorrect accuracy;
- model with and without participant random slope when the maximal model is singular.

## Stopping rule

Recruit until 40 participants have started or 34 protocol-valid complete participants are obtained, whichever occurs later, subject to the approved recruitment cap. Do not inspect condition effects during recruitment.

## Reporting guardrails

- Distinguish algorithmic fidelity metrics from human-task outcomes.
- Report exclusions, missingness, training failures, and all preregistered task contrasts.
- Do not describe fixed identity or adjacency across months as perceptual evidence.
- Clearly label any exploratory analysis and preserve the confirmatory analysis unchanged.

