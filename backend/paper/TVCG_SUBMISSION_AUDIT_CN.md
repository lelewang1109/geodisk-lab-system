# GeoDisk Lab：面向 TVCG 的研究定位与投稿就绪审计

> 本报告由 E30 从正式结果表和系统产物自动生成。TVCG 没有适用于所有论文的固定实验清单；这里把其范围、技术实质、方法/分析/结论准确性与可复现性要求转换为本项目的可检查门槛。

官方依据：[TVCG 范围与征稿](https://www.computer.org/digital-library/journals/tg/cfp-ieee-transactions-on-visualization-computer-graphics)、[IEEE CS 审稿人指南](https://www.computer.org/publications/reviewer-resources)、[IEEE CS 作者指南](https://www.computer.org/publications/author-resources)、[IEEE VIS 开放实践建议](https://ieeevis.org/year/2026/info/open-practices/open-practices/)。

## 1. 研究目标

将固定地理或空间分区转换为紧凑的圆盘与圆环 Power Diagram，在几何合法的前提下尽可能 保留参考邻接、局部邻域、方向和中心—边缘次序，并复用相同单元身份与几何进行稳定的时间 比较和联动诊断。

## 2. 研究问题

- **RQ1**：方法能否始终返回满足几何准入条件的最终 Power 分区？
- **RQ2**：直接优化最终多边形邻接，能否相对合法基线提高拓扑保持？
- **RQ3**：剩余错误集中在哪里，结论能否跨参考定义、参数和数据领域保持稳定？
- **RQ4**：固定几何能否支持数值忠实的时间变化编码？
- **RQ5**：联动系统能否提高人的准确率、速度或理解质量？

## 3. 可主张的创新点

- **C1（algorithm）**：一种参考拓扑监督的多起点圆盘/圆环布局：在真实最终面积平衡 Power 多边形上评价候选， 并使用全局几何硬门槛约束最终选择。
- **C2（diagnostic_evaluation）**：一套结合二值邻接、共享边界长度加权邻接、k-hop 邻域、边界/内部节点误差和局部失败案例的 拓扑诊断协议。
- **C3（temporal_representation）**：一种固定身份的 DeltaAnnulus 时间表示，将有符号变化与标量值分开编码，并在无几何漂移的 月份序列上评价。
- **C4（system）**：一个 D3 联动分析系统，连接地理上下文、最终分区、年度状态、时间轮廓与局部邻接诊断。

创新不应写成“首次使用 Power Diagram”或“首次把地图变成圆形”；Power Diagram、调和嵌入和力优化本身都是已有技术。可防御的新意是：在 Disk/Annulus 约束下，把参考拓扑、多起点、真实最终多边形评价与几何硬准入组成统一方法，并用节点级和共享边界级证据诊断其代价。

## 4. 方法步骤

1. 冻结单元 ID、标量值、参考几何与 4/8 邻域真值。
2. 计算带径向约束的拓扑嵌入，并生成 topology、harmonic、geographic 和融合起点。
3. 对每个起点生成面积平衡的 Disk/Annulus Power 分区。
4. 从最终多边形重新提取真实邻接，而不是使用中间槽位图。
5. 对丢失边施加吸引、对新增边施加排斥，形成确定性的候选轨迹。
6. 仅允许 invalid=0 且 overlap/gap≤1e-7 的候选参与最终选择。
7. 固定最终几何与单元身份，在月份之间编码标量值和有符号变化。
8. 通过地理上下文、Disk/Annulus、时间轮廓和局部邻接诊断进行联动分析。

## 5. 已建立的实验事实

- CEG 最终 F1：Disk `0.7782`，Annulus `0.7481`。
- 5 种子稳定性：Disk `0.7812±0.0017`；Annulus `0.7498±0.0032`。
- 32 个最终跨域输出 invalid=0，最大 overlap `1.7e-15`，最大 gap `2.83e-15`。
- 相较合法基线 Harmonic 与 Area-balanced，二值/加权邻接及边界/内部 Node F1 总体提高；Direct Polar 的原始邻接分数仍更高但存在非法几何。
- 主要剩余错误是新增边导致的过连接；小权重目标项的逐项独立贡献有限。
- 401 单元 NCEP 最终细化中位时间 `39.7s`；该证据不支持超过 401 单元的交互式或渐近性能声称。

## 6. 用户与领域利益

- **分析一致性**：固定单元身份和几何，使跨月份选中、邻接追踪和变化对齐不因重新布局而漂移。
- **紧凑比较**：Disk/Annulus 提供统一、有界的比较画布，适合并排显示不同地区或时间状态；是否更易读仍须用户实验。
- **可诊断性**：保存 preserved/lost/new 边、边界/内部误差和失败节点，使研究者能看到方法在哪里破坏拓扑。
- **可迁移性**：同一管线已在规则网格、不规则行政区、合成拓扑与天球网格运行。
- **可复核性**：数据哈希、固定配置、完整日志、候选历史、结果表与干净运行清单可以追溯每个论文数字。

## 7. TVCG 就绪矩阵

当前：**10 pass / 1 partial / 4 open**；结论为 `algorithmic_artifact_ready_but_full_submission_not_ready`。

| 方面 | 检查 | 状态 | 证据 | 下一步 |
| --- | --- | --- | --- | --- |
| positioning | `tvcg_scope_fit` | **pass** | topology-based visualization, geometric processing, visual analytics and interaction | Keep the title, abstract and index terms centered on the visualization contribution. |
| method | `final_geometry_gate` | **pass** | rows=32; invalid=0; max overlap=1.7e-15; max gap=2.83e-15 | none |
| experiments | `cross_domain_evaluation` | **pass** | final-Power families=['ceg', 'external', 'synthetic'] plus astronomy evaluation | Retain geographic, irregular, large-grid, synthetic and non-geographic cases. |
| experiments | `paired_statistical_inference` | **pass** | paired rows=50; advanced rows=120; Holm correction present=True | Use region/dataset as the independent unit and retain multiplicity correction. |
| experiments | `robustness_and_ablation` | **pass** | seeds=5; regions=8; objective variants=6 | Report all declared seeds and negative ablation results. |
| experiments | `runtime_scalability` | **pass** | sizes=[50, 130, 162, 401]; minimum repetitions=10; maximum cells=401 | Do not claim asymptotic or interactive scalability beyond the evaluated 401 cells. |
| experiments | `temporal_encoding_evaluation` | **pass** | conditions=['derived_from_value_bins', 'direct_diverging_delta']; rows=8 | Keep numerical encoding fidelity separate from perceptual effectiveness. |
| reproducibility | `clean_reproducible_artifact` | **pass** | clean run=20260901T151745Z; stages=32 | Preserve a successful clean manifest, exact environment and table-generating code. |
| frontend | `hosted_snapshot_parity` | **pass** | snapshots=22; all expose final geometry gate=True | Regenerate hosted snapshots from canonical backend artifacts. |
| frontend | `linked_visual_analytics_system` | **pass** | D3 partition, map, ego-neighborhood, temporal-profile and coordinated selection views | Retain task-driven linked interaction and avoid presenting decorative dashboard widgets. |
| frontend | `human_system_evaluation` | **open** | participant response rows=0; prepared trials=96 | Run the preregistered study and report accuracy, response time, confidence, exclusions and ethics approval status. |
| data | `primary_data_provenance` | **open** | missing fields: ['source_url', 'license', 'citation'] | Obtain and freeze the official CEG source URL, license/permission and citation before submission. |
| related_work | `published_baseline_implementation` | **open** | Current baselines are project-local implementations. | Add or justify at least one independently published topology-preserving/cartogram baseline and verify parameter parity. |
| study_design | `confirmatory_holdout_dataset` | **open** | The eight CEG regions were available during method development. | Freeze an untouched year or region before tuning, then run the declared primary comparison once. |
| writing | `manuscript_package` | **partial** | method/evaluation/readiness reports and paper tables exist; no final IEEE-formatted manuscript is present | Prepare a concise regular-paper manuscript, teaser, method diagram, main comparison figure and supplemental index. |

## 8. 论文允许与不允许的表述

**可以表达**：最终几何合法；在合法基线中具有稳定拓扑优势；结论覆盖多数据类型、邻域定义、容差和随机种子；固定几何的时间编码在数值上更忠实；系统支持联动诊断。

**不能表达**：全面优于所有基线；比 Direct Polar 具有更高原始邻接；无监督发现拓扑；用户更快、更准或认知负担更低；已证明大规模实时交互；已有严格未见确认集。

## 9. 投稿前必须完成

1. 解决 CEG 官方来源、许可和规范引用，否则主数据实验不能作为可归档证据。
2. 引入并公平运行一个独立公开实现的已发表相关基线，或充分论证为何不存在可比实现。
3. 冻结未参与开发的新年份/地区作为确认集，只执行一次预声明比较。
4. 若系统贡献进入摘要或贡献列表，完成预注册真人实验及伦理/知情同意流程；否则把系统降为技术演示。
5. 完成 IEEE 模板论文、相关工作的新颖性对照表、方法总览图、主结果图和补充材料索引。

## 10. 声明边界

- Power Diagram、调和嵌入与力优化都是已有技术；新意在受约束的统一流程与最终多边形接受策略。
- 方法使用参考邻接监督，不是无监督拓扑发现算法。
- Direct Polar 可能有更高原始邻接分数，但在多边形非法或重叠时不能支持合法分区优势结论。
- 固定身份和零几何漂移是构造保证，不是感知收益证据。
- 准确率、速度、可用性与认知负担结论需要真实参与者数据。
- 当前基准最大为 401 个单元，不能证明渐近复杂度或大规模交互性能。
