# GeoDisk–DeltaAnnulus 最终实验管线审计（修订前基线）

> 审计日期：2026-09-04。本文档先于 E31–E38 修订写入，记录当时仓库的真实状态，不将计划中的工作写成已完成。

## 1. 科学主线与责任边界

本项目的可防御问题不是“如何把地图做成圆盘/圆环”，而是：在真实地理域仍是计算与科学解释依据的前提下，构造保留关键空间结构的 canonical display space，以支持不同区域和多时刻标量场的稳定、紧凑和直接比较。

审计确认的真实主线为：

`Geographic Reference → Structural Abstraction → Structure-aware Slot Embedding → Balanced Power Partition → Final Polygon-level Topology Refinement → GeoDisk/GeoAnnulus → Fixed Cell Identity → Direct Delta Encoding → Evaluation / Geographic Lookup`

Power Diagram、调和布局与力优化均是已知技术。当前代码能支持的新意边界是：参考拓扑监督、确定性多起点、最终 Power 多边形上的真实重评价、几何硬准入，以及节点/共享边界级诊断组成的统一管线。

## 2. 从原始数据到论文证据的现状

| 阶段 | 科学目的 | 真实输入 | 核心代码/函数 | 真实输出 | 论文位置 | 审计时状态 | 不一致/风险 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 原始 CEG PM2.5 | 提供 2000 年日尺度经纬网格标量场 | `../../../data/2000/*.nc`（366 文件） | `DailyNetCDFAdapter` | 只读源数据 | Data | 本地可读；E0 manifest 记录 366 个 SHA-256 | `datasets.yaml` 缺官方 source URL、license、citation；阻断主数据的归档性 claim |
| E0 Data Audit | 确认真实变量、文件、缺失与数值范围 | NetCDF 源文件，`datasets.yaml` | `audit_dataset` | `results/data_audit/dataset_summary.json`、`daily_file_manifest.csv`、缺失/变量表 | Data / Reproducibility | 已运行 | provenance 仍 open；不可由哈希反推数据许可 |
| E1 Reference Space | 将 fine grid 冻结为稳定 macro-cell，定义 Cell ID、4-neighbor 参考图、`theta/rho`、时间序列 | E0 确认的标量变量、省界 GeoJSON、`coarsen_factor=4`、`min_valid_fraction=.25` | `prepare_region_references`、`grid_edges`、`_boundary_radius`、`k_hop_neighborhoods` | 每省 `cells.csv`、`original_geometry.geojson`、`original_adjacency.csv`、`original_local_directions.csv`、`neighborhoods.json`、`reference_metadata.json` | Method: Reference Construction | 8 省已运行 | CEG `cells.csv` 没有显式 boundary 字段；多边形为未裁剪 macro-cell，地理省界单独保留 |
| E2 Baselines | 产生固定对照几何 | E1 reference + 省界 | `direct_polar`、`harmonic_continuous`、`geographic_area_balanced` | `results/spatial/<region>/{direct_polar,harmonic,area_balanced}_{disk,annulus}.geojson` + metadata | Evaluation: Baselines | 已运行 | 是项目内实现，不是独立发表代码；Direct Polar 可能非法，不得与合法分区混为“全面优于” claim |
| E3 Initial GeoDisk / GeoAnnulus | 构造带径向约束的 slot embedding 与初始面积平衡 Power 分区 | E1 reference，`geometry.yaml` 早期权重/层数/迭代数 | `build_topology_embedding`、`regular_polygons`、`proposed_irregular` | `regular_topology_*`、`proposed_disk.geojson`、`proposed_annulus.geojson` | Method precursor / Ablation | 已运行，应保留 | E4 主图在审计时仍将这两个早期产物标为 GeoDisk/GeoAnnulus，与 Final method 不一致 |
| E16 Revised Embedding | 增加 NP@2、局部方向、跨层交换与扩大搜索 | E1 reference + `method_revision` | `build_topology_embedding(... search_mode="expanded_cross")` | `Table_method_revision.csv` | Method ablation / Revision evidence | 已运行 | E16 只评价内存中结果，不保存主几何；最终几何应以 E19 为准 |
| E19 Final Power Refinement | 在每个真实最终平衡 Power 多边形上重新提取邻接，用统一多起点+拓扑力轨迹选出合法候选 | CEG / Natural Earth / NCEP / Synthetic reference，E19 固定 schedule、objective 与 tolerance | `refine_final_power_adjacency`、`_score_candidate`、`_topology_forces` | `results/{spatial_refined,external_refined,synthetic_refined}/.../final_refined_{disk,annulus}.geojson` + candidate history；`Table_final_power_refinement.csv` | Main Method / RQ1 | 已运行；32 行最终几何 invalid=0，overlap/gap 通过 1e-7 准入 | 当前真正 Final Method；旧 E4/E12 图没有使用它 |
| Final GeoDisk / GeoAnnulus | 提供论文主 canonical geometry | E19 所有上游 | `final_refined_disk/annulus.geojson` | CEG 8省、Natural Earth、NCEP、6 synthetic；NASA 由 E22 同步生成 | Main Figures / Main Evaluation | 产物完整 | 主比较图与跨域主表尚未统一指向 Final |
| E17 Advanced Spatial Errors | 评价节点级邻接、NP、度数、局部方向/顺序与共享边界加权拓扑 | 所有 reference + 早期与 Final geometry | `node_level_fidelity`、`weighted_adjacency_scores` | `Table_node_level_errors.csv`、`Table_boundary_interior_errors.csv`、`Table_weighted_adjacency.csv` | RQ1 / Error decomposition | 已运行 | CEG 因缺 `is_boundary` 而在评价时隐式使用 degree<4；定义未在 E1 冻结，且无 geographic sensitivity |
| E20 / E27 Statistics | 以省/数据集为独立单元做配对 bootstrap、exact sign-flip 和 Holm 校正 | E4/E17/E19 结果表 | `E20_refined_statistics.py`、`E27_advanced_statistics.py` | `Table_refined_paired_bootstrap.csv`、`Table_advanced_paired_statistics.csv` | RQ1 / Inference | 已运行 | E20 比较的 baseline 来自 E4 表，Final 来自 E19，逻辑正确；不得将 8 省写成未见 holdout |
| E14/E18/E23–E26 | 检查 contact tolerance、4/8-neighbor、clipping、运行时、组件/目标消融与 5-seed 稳定性 | 冻结 reference/geometry/config | 各 E14/E18/E23–E26 脚本 | sensitivity / runtime / ablation / stability CSV + manifests | RQ2 / Supplement | 已运行 | 最大仅 401 cells，不支持大规模交互或渐近复杂度 claim；无 confirmatory holdout |
| E5 Temporal Delta | 以固定 Final GeoAnnulus 几何编码月度有符号变化 | 12 月 cell values + `final_refined_annulus.geojson` | `encode_temporal`、`_render_delta_small_multiples` | `monthly_delta_encoding.csv`、`Fig_temporal_delta_Hubei/NCEP.png` | RQ3 baseline/auxiliary | 已运行 | 标题虽写 DeltaAnnulus，但图是 12 个 small multiples；M01=0 baseline，没有实现 `D1+Δ12+...Δ11,12` 一体化视图；旧图应保留 |
| E6 Change Metrics | 比较“由绝对值 bins 差分”与“直接对称 delta bins”的数值忠实度 | E5 encoding CSV | `_metrics`、`_evaluate_dataset` | temporal fidelity detailed/summary + bootstrap + manifest | RQ3 | 已运行 | `cell_identity_accuracy=1`、`geometry_centroid_drift=0`、`temporal_adjacency_jaccard=1` 已在 manifest 写明是 construction property；不是算法优势 |
| E21 Perceptual Materials | 准备人因实验刺激与机器可读答案 | Hubei/NCEP temporal CSV + geographic/final annulus polygons | 两条件 stimulus renderer | `user_study/stimuli`、task/response schema、manifest | RQ4 | 材料已生成；0 participant rows | 仅 `geographic_map` vs `delta_annulus`，无法分离 direct-delta、canonicalization、integrated organization；`radial_propagation` 名称容易被误解为因果传播 |
| E28 Failure Cases | 保留局部最差节点而不从汇总排除 | E17 node-level table | `_category` + deterministic ranking | `Table_local_failure_cases.csv`、taxonomy table/manifest | RQ1 diagnostic / Supplement | 已运行 | 没有视觉对应；表内类别由度数反推 preserved/lost/new，新图应从真实 edge sets 直接计算 |
| E9 Case Study | 原计划承载 case study | 无 | 仅打印一行说明 | 无独立 case 产物 | Case Study | 空壳 | 将 E4 主比较图当作 case study，与论文需要不符；没有客观 event selection |

## 3. 外部数据链

- E10 准备 Natural Earth Admin-0 Africa、NCEP Africa 2000 以及 6 个确定性 synthetic topology cases；各数据集保存与 E1 同构的 reference artifacts。
- E11 生成 Natural Earth/NCEP 项目内 baselines 与早期 `proposed_*`；E12 审计时仍用 `proposed_*` 绘制 `Fig_external_*`，因而与 E19 Final 不一致。
- E13 对 synthetic cases 在内存中生成/评价早期方法，但不保存 baseline GeoJSON；E19 单独保存 synthetic Final GeoJSON。统一 cross-domain 表可从 E13 与 E19 真实表合并，不应伪造缺失几何。
- E22 NASA Exoplanet 的同一脚本已生成 baselines、early proposed 和 Final，其现有主图的 GeoDisk/GeoAnnulus 已指向 `GeoDisk-Final/GeoAnnulus-Final`；这是当前唯一已对齐 Final 的 cross-domain 图。

## 4. 方法/评价接口核查

- Cell identity：GeoJSON `cell_id` 集合在 E4/E12/E19 及测试中核对；Final temporal encoding 对所有月复用同一 GeoAnnulus geometry。
- Reference adjacency：CEG 默认为 macro-grid rook/4-neighbor，由 `grid_edges` 生成；E18 另评价 8-neighbor sensitivity。
- Display adjacency：由最终多边形边界接触及声明的 tolerance 提取，不是从 slot graph 直接拷贝。
- Final selection：对每个候选重建 balanced Power cells，重算 adjacency/NP@2/方向/径向/面积 CV；只允许 invalid=0 且 overlap/gap≤1e-7 的候选胜出。
- Figure scalar encoding：旧 comparison helper 已在单张图内共用 2–98% normalization 和 `viridis`，但 DPI=260，低于新主图要求的 300 dpi。
- Weighted adjacency：precision 使用 display shared-boundary length，recall 使用 reference shared-boundary length；不与 binary F1 混合。

## 5. 审计后的 P0/P1 修订顺序

1. P0：增加不覆盖旧 E4/E12 产物的 Final CEG 与 Final external 主图/表。
2. P0：在 E1 显式冻结 topological/geographic boundary，使 E17 的主定义可配置并新增 sensitivity。
3. P0：基于真实 Hubei reference/E19 geometry 生成 Reference Structure 与 Method Pipeline figures。
4. P0：保留 E5 small multiples，新实现 `D1+Δ` integrated DeltaAnnulus 与 construction-consistency table。
5. P1：增加四条件 user-study v2 材料，但严格声明没有 participant data。
6. P1：将 E28 表与真实 preserved/lost/new edges 连接成 failure figure；增加客观选事件的 Hubei temporal case。
7. P1：写入 published-baseline 候选与兼容性分析，但在未实际集成独立代码前保持 open。
8. 最后：生成 RQ 索引、增量一键脚本与独立 run manifest，执行新增阶段和测试。

## 6. 审计时的 claim 门槛

已有代码/结果可支持：Final geometry 合法；在合法项目内 baselines 中具有可量化的拓扑优势；固定几何上的 direct delta 数值重建比由量化绝对值差分更忠实；误差、失败点、容差、种子与目标消融可追溯。

审计时不可支持：人的准确率/速度/认知负担改善；全面优于 Direct Polar；超过 401 cells 的实时或渐近性能；未见确认集泛化；PM2.5 变化的气象/传输因果；已完成独立 published baseline 比较；主 CEG 数据的完整归档 provenance。
