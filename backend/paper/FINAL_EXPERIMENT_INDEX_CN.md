# GeoDisk–DeltaAnnulus 最终论文实验索引

> 生成/核查日期：2026-09-04。本索引只把真实已运行的代码与产物标记为 complete；真人用户证据、published baseline、CEG provenance 和 confirmatory holdout 保持 open。

## RQ1：Canonicalization 是否在合法几何约束下保持关键空间结构？

| 证据 | Figure / Table | Producer | 状态 | 论文建议 |
| --- | --- | --- | --- | --- |
| 真实输入→稳定 macro-cell→参考图→`theta/rho`/boundary | `Fig_reference_structure_Hubei.{png,pdf}` | E1 + E33 | complete；130 cells / 225 edges | Main Method Fig. 1 |
| reference→slot initialization→assignment optimization→Power→Final | `Fig_geodisk_method_pipeline_Hubei.{png,pdf}` | E34（使用 E19 固定配置） | complete；slot objective 0.5410→0.5656；Final Disk preserved/lost/new=214/11/136 | Main Method Fig. 2 |
| 8 省 Final 主比较 | `Fig_final_spatial_comparison_<Province>.png` | E31 | complete；所有 GeoDisk/Annulus panel 指向 `spatial_refined/final_refined_*` | Hubei 主文，其余 Supplement |
| binary adjacency、weighted adjacency、NP@2、direction/radial 与 validity | `Table_final_spatial_comparison.csv` | E31 | complete；48 真实行 | Main Table 1 |
| Final geometry admissibility | `Table_final_power_refinement.csv` | E19 | complete；Final invalid=0，overlap/gap≤1e-7 | Main Table 1 / Supplement |
| 节点级 boundary/interior 误差 | `Table_boundary_interior_errors.csv` | E17 | complete；主定义由 config 声明为 topological | Main/Supplement |
| 共享边界加权拓扑 | `Table_weighted_adjacency.csv` | E17 | complete | Main Table 1 |
| 配对 bootstrap / exact sign-flip / Holm | `Table_refined_paired_bootstrap.csv`、`Table_advanced_paired_statistics.csv` | E20 / E27 | complete | Main statistics + Supplement |
| 局部失败真实可视化 | `Fig_failure_cases_Hubei.png`、`Table_local_failure_cases.csv` | E17/E28/E37 | complete；Hubei 无 pure under-connected 节点，图中显式标注 mixed case | Supplement，不应隐藏 |

可写入主文的结果：8 省 Final 均值 GeoDisk-Final binary F1=0.7782、weighted F1=0.8884；GeoAnnulus-Final binary F1=0.7481、weighted F1=0.8096；Final 行 invalid=0。GeoDisk-Final 相对 Harmonic/Area-balanced 的 weighted F1 配对均值提高分别为 0.0522/0.0698，GeoAnnulus-Final 为 0.0495/0.1096；对 Direct Polar 不宣称原始邻接全面更优，因其平均 invalid count=3.375 且存在 gap/overlap。

## RQ2：对数据类型、参考定义、容差、种子与目标是否稳健？

| 证据 | Figure / Table | Producer | 状态 | 论文建议 |
| --- | --- | --- | --- | --- |
| Natural Earth / NCEP Final 主图 | `Fig_final_external_NE-Admin0-Africa.png`、`Fig_final_external_NCEP-AirTemp-Africa-2000.png` | E32 | complete；不覆盖 E12 旧图 | Main cross-domain figure |
| CEG + Natural Earth + NCEP + Synthetic + NASA | `Table_final_cross_domain_spatial.csv` | E32，整合 E4/E12/E13/E19/E22 | complete；17 datasets / 170 rows | Main Table 2 / Supplement |
| NASA Exoplanet Final 图/表 | `Fig_external_NASA-Exoplanet-SkyGrid.png`、`Table_astronomy_generalization.csv` | E22 | 原有逻辑已使用 Final，保留 | Main/Supplement |
| topological vs geographic boundary | `Table_boundary_definition_sensitivity.csv` | E1 + E17 | complete；64 rows | Supplement sensitivity |
| 4/8-neighbor，full/clipped reference | neighbor/clipping sensitivity tables | E18 | complete | Supplement |
| contact tolerance | `Table_contact_tolerance_sensitivity.csv` | E14 | complete | Supplement |
| 5 seeds × 8 省 | seed stability tables | E26 | complete | Supplement |
| component/objective ablation | E24/E25 tables | E24/E25 | complete | Supplement |
| runtime up to 401 cells | `Table_runtime_scalability.csv` | E23 | complete | Supplement；不支持超过 401 cells 的实时 claim |

边界定义已被冻结为：`is_topological_boundary = reference_degree < 4`；`is_geographic_boundary = 未裁剪 macro-cell 与真实省界相交/相触或在 1e-9 尺度的声明数值容差内`。论文主实验使用 topological，geographic 为 sensitivity。Hubei 两者分别标记 47/56 cells，差异不被隐藏。

## RQ3：固定 canonical geometry + direct delta 能否稳定表达时间变化？

| 证据 | Figure / Table | Producer | 状态 | 论文建议 |
| --- | --- | --- | --- | --- |
| 旧 fixed-geometry small multiples | `Fig_temporal_delta_Hubei.png`、`Fig_temporal_delta_NCEP.png` | E5 | 保留且 hash 未改 | Temporal baseline / Supplement |
| `D1+Δ12+...Δ11,12` integrated view | `Fig_integrated_delta_annulus_Hubei.png`、`Fig_integrated_delta_annulus_NCEP.png` | E35 | complete；设计 B；每层是同一 Final GeoAnnulus 的确定径向同胚映射 | Main temporal figure |
| integrated construction checks | `Table_integrated_delta_annulus_consistency.csv` | E35 | complete；24 rows；Cell ID=1，mismatch=0，no reoptimization | Supplement；必须标为 construction guarantee |
| direct delta numerical fidelity | temporal fidelity detailed/summary/bootstrap | E6 | complete | Main Table 3 |

9-bin 设置下，direct delta 相对从绝对值 bins 差分：sign accuracy 0.8388 vs 0.7024，normalized MAE 0.0646 vs 0.1127，magnitude Spearman 0.8648 vs 0.6806。`cell_identity_accuracy=1`、`geometry_centroid_drift=0`、`temporal_adjacency_jaccard=1` 是固定几何构造属性，不是“击败 baseline”的性能数据。一体化径向压缩后重新从浮点多边形提取的 adjacency Jaccard 最低为 Hubei 0.9818 / NCEP 0.9963；表中同时保留逻辑同胚保证和这个数值渲染检查，不混为一个 claim。

## RQ4：是否提升用户 perceptual task performance？

| 证据 | Artifact | Producer | 状态 | 论文建议 |
| --- | --- | --- | --- | --- |
| C1 geographic states / C2 geographic direct delta / C3 canonical annulus direct delta / C4 integrated DeltaAnnulus | `user_study_v2/stimuli/`、`task_manifest.csv`、`response_schema.csv`、`study_manifest.json` | E36 | materials complete；48 stimuli / 240 task rows / **0 responses** | 只能写 materials/protocol，不能写 perceptual result |
| five objective tasks | localization、sign、magnitude、temporal comparison、center/periphery pattern | E36 | complete | radial ground truth 由 median-ρ 两组 mean absolute delta 自动计算，不使用“传播”因果语言 |

当前状态：**NO PARTICIPANT DATA COLLECTED**。准确率、完成时间、置信度、认知负担与主观偏好均为 open。

## Case Study：Hubei temporal

E38 在绘图前对 11 个 transition 计算 mean absolute delta、p95 absolute delta、high-change cell fraction，对三者 min-max normalization 后等权汇总；客观选出 M11→M12，而不是人工挑月份。

- Figure：`Fig_case_hubei_temporal.png`（before / after / geographic delta / Final GeoAnnulus delta / integrated layer / top cells）。
- Table：`Table_case_hubei_top_changes.csv`（10 行，before/after/delta、Cell ID、rho/theta、reference neighbors、neighbor mean delta/same-sign fraction）。
- Metadata：`results/temporal/case_hubei_manifest.json`，保存全部 11 transition scores、选择规则与解释边界。
- 可用语言：spatially coherent increase/decrease、center-periphery shift、localized/distributed change、persistent/reversed change。
- 禁止语言：污染由 A 传播到 B，或任何无 meteorology/wind/transport model 支持的因果解释。

## 仍然 open

- Published baseline：已在 `PUBLISHED_BASELINE_CANDIDATES_CN.md` 核对候选、代码状态与公平性，但没有伪造 implementation/数字。
- User study：需伦理/知情同意、预注册、招募、排除规则、真实 responses 和统计分析。
- CEG provenance：仍缺官方 source URL、license/permission、citation。
- Confirmatory holdout：8 省均在方法开发期可见，尚无冻结后仅运行一次的新年份/地区。

## 一键增量入口与追溯

`scripts/run_paper_completion.sh` 仅运行 E31–E38，前置产物缺失时 fail-fast；每次生成 `results/run_manifests/paper_completion_*.json`，记录 UTC timestamp、Git commit/dirty state、Python version、所有 YAML SHA-256、每阶段 return code/duration/stdout/stderr 和输出。本次成功 manifest：`paper_completion_20260904T024402Z.json`。
