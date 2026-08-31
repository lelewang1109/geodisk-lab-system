# GeoDisk–DeltaAnnulus User-Study Protocol

## Status

The study package is implementation-ready, but no participant has been recruited and no human response has been collected. All generated answers in `task_manifest.csv` are algorithmic ground truth, not user-study results.

## Research questions and hypotheses

- RQ-U1: Does DeltaAnnulus improve change-localization accuracy relative to geographic small multiples?
- RQ-U2: Does DeltaAnnulus reduce completion time for increase/decrease and temporal-comparison tasks?
- RQ-U3: Does any benefit depend on task type or dataset geometry?
- H1 (primary): DeltaAnnulus improves change-localization accuracy.
- H2: DeltaAnnulus reduces log completion time for temporal comparison.
- H3: DeltaAnnulus does not reduce confidence after controlling for task difficulty.

The primary endpoint is binary trial accuracy for `change_localization`. All other hypotheses are secondary.

## Design

- Within-subject comparison of `geographic_map` and `delta_annulus`.
- Two datasets: Hubei PM2.5 and NCEP Africa air temperature.
- Four tasks: change localization, increase/decrease judgment, temporal comparison, and radial propagation.
- Six predeclared month transitions per dataset: M01–M02, M03–M04, M05–M06, M07–M08, M09–M10, M11–M12.
- Condition order is counterbalanced with an AB/BA scheme. Trial order within each condition/task block is randomized from the fixed manifest.
- The full bank contains 96 trials. A balanced subset should be sampled per participant to keep the main session within 25–30 minutes; every stimulus must receive approximately equal exposure across participants.

## Power and recruitment

A two-sided paired-test approximation with effect size `dz=0.50`, `alpha=0.05`, and power `0.80` requires 34 complete participants. The recruitment target is 40 to allow approximately 15% attrition. The final primary analysis uses a mixed-effects logistic model; this paired calculation is a conservative planning approximation, not a substitute for the preregistered model.

Inclusion criteria:

- age 18 or older;
- normal or corrected-to-normal vision;
- no self-reported red–green color-vision deficiency;
- desktop/laptop display with viewport width at least 1200 px;
- informed consent completed.

Recruitment should target both visualization/GIS-experienced and general university participants. Experience level is recorded before training and used as a prespecified moderator.

## Procedure

1. Consent, demographics, visualization/GIS experience, and color-vision screening.
2. Technique explanation without disclosing hypotheses.
3. Four guided training trials per condition followed by two criterion trials. Participants must answer at least one criterion trial correctly per condition; one retraining attempt is allowed.
4. Counterbalanced experimental blocks with a mandatory short break between conditions.
5. Per-trial response, completion time, and confidence on a 1–7 scale.
6. Post-condition workload questionnaire and final qualitative preference question.

Timing begins after the complete stimulus and answer controls are visible and ends on response submission. Browser tab visibility loss pauses timing and is logged.

## Exclusion rules

Apply these rules without examining the direction of the condition effect:

- withdrawal or missing consent;
- failure of both criterion attempts;
- more than 20% missing experimental responses;
- median completion time below 500 ms;
- more than 25% of trials affected by focus loss or rendering failure;
- duplicate participant/device record according to the ethics-approved recruitment identifier.

Report the number excluded by each rule. Do not add post-hoc accuracy-based exclusions.

## Measures and analysis

Primary model:

```text
correct ~ condition * task + dataset + experience + condition_order
        + (1 + condition | participant) + (1 | stimulus)
```

Use a binomial mixed-effects model. Report odds ratio, 95% confidence interval, estimated marginal means, and the raw accuracy difference. Analyze completion time with a log-normal mixed model on correct trials. Analyze confidence with an ordinal mixed model where available, otherwise a preregistered cumulative-link or participant-clustered sensitivity analysis.

Secondary pairwise contrasts are Holm-corrected within each outcome family. Report all task-wise outcomes, including null or adverse results. Device/render failures are summarized separately.

## Materials and data handling

- `task_manifest.csv`: fixed stimuli, options, and ground truth.
- `stimuli/`: generated PNG stimuli.
- `response_schema.csv`: raw response columns; never overwrite the manifest with participant data.
- `study_manifest.json`: design and power-analysis metadata.
- `PREREGISTRATION_DRAFT.md`: analysis decisions to freeze before recruitment.

Participant identifiers must be pseudonymous. Consent/contact records, if required, remain outside the analysis repository. Obtain institutional ethics approval or exemption before recruitment.

