# Formal Experiment Readiness Audit

> `pass` means the artifact exists and satisfies the declared minimum; `open` is retained explicitly and must not be hidden in the paper.

| Area | Check | Severity | Status | Evidence | Required action |
| --- | --- | --- | --- | --- | --- |
| data | `primary_data_provenance` | blocker | **open** | missing fields: ['source_url', 'license', 'citation'] | Obtain and freeze the official CEG source URL, license/permission and citation before submission. |
| data | `primary_file_hashes` | major | **pass** | 366 files; sha256 column=True | none |
| topology | `final_contact_tolerance` | major | **pass** | methods=['Area-balanced', 'Direct Polar', 'GeoAnnulus', 'GeoAnnulus-Final', 'GeoDisk', 'GeoDisk-Final', 'Harmonic', 'Regular Topology'] | none |
| local_error | `advanced_cross_domain_errors` | major | **pass** | dataset_count=17 | none |
| ablation | `final_objective_ablation` | major | **pass** | variant_count=6 | none |
| robustness | `multi_seed_stability` | major | **pass** | seeds=5; regions=8/8 | none |
| efficiency | `runtime_repetitions` | major | **pass** | minimum repeat_count=10 | none |
| statistics | `advanced_paired_inference` | major | **pass** | advanced paired table exists | none |
| diagnostics | `failure_case_retention` | minor | **pass** | ranked failure table exists | none |
| user_study | `human_participant_results` | blocker | **open** | response rows=0 | Collect the preregistered participant study before making perceptual-efficiency claims. |
| reproducibility | `clean_full_pipeline_manifest` | major | **open** | successful clean manifests=0; total manifests=0 | Run scripts/run_formal_experiment.sh from a clean frozen commit and preserve its manifest. |
| baselines | `published_baseline_implementation` | major | **open** | Current baselines are project-local implementations. | Add or justify at least one independently published topology-preserving/cartogram baseline and verify parameter parity. |
| reproducibility | `backend_environment_lock` | major | **pass** | requirements-lock.txt present | none |

## Interpretation

Algorithmic claims and perceptual claims have separate gates. Missing participant responses block only perceptual-efficiency claims. Missing primary-data provenance blocks archival publication of the main CEG experiment even when numerical results are reproducible locally.
