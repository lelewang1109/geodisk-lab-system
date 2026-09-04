# 面向论文最终实验的系统核查与修订报告

## 1. 原项目存在的主要问题

1. E4 八省主图与 E12 Natural Earth/NCEP 主图仍读取 E3/E11 `proposed_*`，没有使用 E19 Final geometry。
2. CEG boundary 在 E17 评价时才隐式以 degree<4 推导；`cells.csv` 未冻结 topological/geographic 定义。
3. 缺 Reference Structure 和真实 Method Pipeline figures。
4. E5 实际为 fixed-geometry 12-panel small multiples，不是 integrated `D1+Δ` DeltaAnnulus。
5. E21 只有两条件，无法分离 direct delta、canonicalization 和 integrated organization。
6. E28 只有 failure table，E9 是空壳；没有可追溯局部图和客观 temporal event selection。
7. Published baseline、CEG provenance、participant evidence 与 confirmatory holdout 都仍是 open。

## 2. 已修复的问题

- E31/E32 新生成 Final comparison figures，旧 E4/E12 图经 Git blob hash 核对未变。
- E1/`regions.py` 显式写入 `reference_degree`、`is_topological_boundary`、`is_geographic_boundary`与 metadata；E17 主定义可配置，新生成 64 行 sensitivity table。
- E33/E34 从真实 Hubei reference/E19 geometry 生成 PNG 300 dpi + PDF。
- E35 选择设计 B，用同一 Final GeoAnnulus 的确定径向同胚映射表示 D1 和 11 个 delta；旧 E5 图 hash 未变。
- E36 生成四条件、五任务材料，明确 0 participant responses。
- E37 从 reference/display edge sets 重算 preserved/lost/new；E38 在绘图前用预定义规则选出 M11→M12。
- 新增 E31–E38 一键入口、成功 run manifest、产物级测试和 RQ 索引。

## 3. 新增和修改文件

代码：`experiments/E31_*.py`–`E38_*.py`、`experiments/paper_figure_utils.py`、`scripts/run_paper_completion.{sh,py}`、`tests/test_paper_completion.py`。修改：`config/experiment.yaml`、`data/regions.py`、`geometry/mappings.py`、`visualization/figures.py`、`E17_advanced_spatial_errors.py`。

数据/表：8 省 `cells.csv` 和 `reference_metadata.json` 增加 boundary 字段；新增 `Table_final_spatial_comparison`、`Table_final_cross_domain_spatial`、`Table_boundary_definition_sensitivity`、`Table_integrated_delta_annulus_consistency`、`Table_case_hubei_top_changes`，并更新 E17/E28 下游真实表。

文档：`FINAL_PIPELINE_AUDIT_CN.md`、`PUBLISHED_BASELINE_CANDIDATES_CN.md`、`FINAL_EXPERIMENT_INDEX_CN.md`、本报告。Figure 详见第 6 节；每张均同步到 `results/figures` 与 `paper/figures`。

## 4. Final research pipeline

Raw NetCDF / external source → E0 audit → E1 frozen Reference Space → E2 legal/project baselines + E3 early method → E16 revised embedding → E19 final polygon-level Power refinement → Final GeoDisk/GeoAnnulus → E17/E20/E27 spatial/weighted/local/statistical evaluation → E5/E6 temporal encoding/fidelity → E35 integrated DeltaAnnulus → E36 study materials → E37 failure diagnostics / E38 observational case study → geographic lookup and bounded scientific interpretation。

## 5. 每个新实验的 input → method → output

| Stage | Input | Method | Output | RQ | 实际运行 |
| --- | --- | --- | --- | --- | --- |
| E31 | E1 reference + E2/E3 baselines + E19 CEG Final | 同标量/色标/尺寸/线型渲染；重算 binary/weighted/validity | 8 figures + 48-row table + manifest | RQ1 | success |
| E32 | E10 reference + E11 baselines + E19 external Final + E4/E12/E13/E19/E22 tables | Final external rendering + schema-unified real-table merge | 2 figures + 17-dataset/170-row table + manifest | RQ2 | success |
| E33 | Hubei `cells/geometry/adjacency/directions/neighborhoods/metadata` | 真实几何上绘制 scalar/macro-cell/graph/attributes | PNG/PDF + manifest | Method/RQ1 | success |
| E34 | Hubei reference + E19 config/Final geometry | 确定性重构 embedding、pre-final Power，从多边形提取 edge errors | PNG/PDF + manifest | Method/RQ1 | success |
| E35 | E5 temporal CSV + E19 Final annulus | 12 个同胚 concentric layers；D1 sequential / deltas symmetric diverging | 2 figures + 24-row consistency table + manifest | RQ3 | success |
| E36 | Hubei/NCEP temporal + geographic/Final annulus | 四条件、五客观任务、固定 seed | 48 stimuli + 240 task rows + empty response schema + JSON | RQ4 protocol | success; no participants |
| E37 | E17 node rows + reference.edges + Final display adjacency | 确定性最差/类别选择并直接计算 edge status | failure figure + manifest | RQ1 diagnostic | success |
| E38 | Hubei 11 transitions + reference graph + Final annulus | 三指标客观 event score + top-10/neighbor summary | case figure + CSV + JSON | Case/RQ3 | success |

## 6. 每张新 Figure

- `Fig_final_spatial_comparison_<8 provinces>.png`：Geographic Reference + 4 baselines + GeoDisk-Final + GeoAnnulus-Final。
- `Fig_final_external_NE-Admin0-Africa.png`、`Fig_final_external_NCEP-AirTemp-Africa-2000.png`：外部数据 Final 对齐图。
- `Fig_reference_structure_Hubei.{png,pdf}`：输入/reference 构造。
- `Fig_geodisk_method_pipeline_Hubei.{png,pdf}`：真实方法过程与 Final edge status。
- `Fig_integrated_delta_annulus_Hubei/NCEP.png`：D1 + 11 delta layers；绝对/变化使用不同色标。
- `Fig_failure_cases_Hubei.png`：5 类节点参考/Final ego neighborhood。Hubei 无 pure under-connected，故真实 mixed panel 显式注明。
- `Fig_case_hubei_temporal.png`：自动选定的 M11→M12 observational case。

所有新 PNG 的实测 metadata 为约 300×300 dpi，已做视觉 QA。

## 7. 每张新 Table

- `Table_final_spatial_comparison.csv`：48 行；包含用户要求的 14 个字段及 source GeoJSON。
- `Table_final_cross_domain_spatial.csv`：17 datasets / 5 families / 170 rows；合并现有真实表，没有 synthetic 伪 GeoJSON。
- `Table_boundary_definition_sensitivity.csv`：64 行；两种 boundary×boundary/interior×Final Disk/Annulus×8 省。
- `Table_integrated_delta_annulus_consistency.csv`：24 行；分开 logical construction guarantee 与 rendered numeric adjacency check。
- `Table_case_hubei_top_changes.csv`：10 行；含 Cell ID、before/after/delta 和 neighbor-level summary。

## 8. 当前真正可以支持的 claims

- E19 Final 在所报告输出上满足 invalid=0 与 1e-7 overlap/gap 准入。
- Final 在 8 省和合法 Harmonic/Area-balanced 基线之间具有可追溯的 binary/weighted adjacency、NP@2 与部分局部方向改善；具体以配对表为准。
- 结论已在 CEG、Natural Earth、NCEP、synthetic 和 NASA Exoplanet 上用同一方法链评价。
- Direct delta 在声明的量化策略下比由绝对值 bins 差分具有更好的数值 fidelity。
- Integrated DeltaAnnulus 真正实现了 D1 + 11 transitions，且不重新优化几何/不重排 Cell ID。

## 9. 当前不能支持的 claims

- 用户更快、更准、认知负担更低；尚无 participant data。
- 全面优于 Direct Polar；其邻接分数可更高，但存在几何非法性。
- 大规模实时/渐近性能；最大仅 401 cells。
- 未见 confirmatory generalization；8 CEG 省在开发期可见。
- 污染传播/气象因果；数据仅有 PM2.5。
- 已与独立 published baseline 公平运行；当前只有候选分析。

## 10. 仍需人工完成

CEG 官方 provenance/许可/引用；选定且冻结 published baseline；预注册和伦理流程；真人招募；新年份/地区 holdout；IEEE 模板主文、无障碍配色/印刷可读性的最终人工编辑。

## 11. 用户实验还缺什么

伦理审批/豁免、知情同意、预注册主指标与排除规则、招募与功效量实施、顺序/学习效应平衡、设备与色觉检查、真实 response rows、正确率/时间/信心/缺失分析。

## 12. Published baseline 还缺什么

建议优先：Natural Earth 上的 Gastner–Seguy–More flow-based cartogram，以及冻结 tile-grid 规则的 Eppstein et al. grid-map matching。还需 repo/commit/license/environment/adapter、预声明参数与 failure policy，并真实保存 GeoJSON/CSV/log/manifest。

## 13. 数据 provenance 还缺什么

CEG 的正式数据集名称、provider URL、download/access date、license/permission、规范 citation/DOI、原始变量和单位定义、质量控制/缺失值文档。已有 366 文件 SHA-256，但哈希不能替代来源与许可。

## 14. 推荐的最终 Figure/Table 编号

- Fig. 1 Reference Structure (Hubei)
- Fig. 2 GeoDisk Method Pipeline (Hubei)
- Fig. 3 Final Spatial Comparison (Hubei；其余省 S1–S7)
- Fig. 4 Cross-domain Final Comparison (Natural Earth + NCEP + NASA，NASA 可并版)
- Fig. 5 Integrated DeltaAnnulus (Hubei + NCEP)
- Fig. 6 Hubei Temporal Case Study
- Fig. S8 Failure Cases
- Table 1 CEG Final Spatial / Geometry Metrics
- Table 2 Cross-domain Spatial Results
- Table 3 Temporal Encoding Fidelity
- Table S1 Boundary Definition Sensitivity
- Table S2 Contact / Neighbor / Clipping Sensitivity
- Table S3 Seed Stability and Ablations
- Table S4 Runtime
- Table S5 Integrated Construction Consistency

## 验证结果

E31–E38 增量脚本完整成功；manifest=`results/run_manifests/paper_completion_20260904T024402Z.json`。新增 6 个产物级测试，与原有测试合计 31/31 通过。旧 E4 CEG、E12 external、E5 temporal PNG 通过 Git blob hash 验证未覆盖。
