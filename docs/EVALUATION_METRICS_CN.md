# GeoDisk Lab 评价指标与实验方法说明

> 本报告以当前仓库的实际代码、配置和结果表为准，说明项目“评价什么、如何计算、如何比较、能得出什么结论”。可作为论文实验章节和补充材料的基础。

## 1. 评价目标与判定顺序

项目的核心问题是：原始地理空间映射为固定圆盘或圆环分区后，能否在几何合法的前提下，尽可能保留拓扑邻接、局部邻域、方向关系和中心—边缘次序，并在固定几何上稳定表达时间变化。

评价顺序为：

1. **几何合法性是准入条件**：无效多边形、明显重叠或未覆盖区域不能被高拓扑得分掩盖。
2. **Adjacency F1 是主要拓扑指标**：邻接必须从最终显示多边形中重新提取，不使用中间槽位图代替。
3. **用 NP@2、加权邻接和节点误差解释全局 F1**：判断错误来自边界还是内部、短接触还是重要长边界。
4. **方向、径向和面积平衡分开报告**：不用单一综合分数掩盖多目标权衡。
5. **以数据集/区域为统计单位**：同一区域上成对比较方法，不把同一区域内高度相关的单元当作独立样本。
6. **构造性不变量不等于感知优势**：跨月份单元身份和邻接不变，不能代替用户实验。

## 2. 实验对象与公平比较

正式实验对每个数据集生成 Disk 和 Annulus 两种视图，比较 Direct Polar、Harmonic、Area-balanced、Regular Topology、GeoDisk/GeoAnnulus 和 GeoDisk-Final/GeoAnnulus-Final。所有方法使用相同的单元 ID、原始多边形、参考邻接和标量值。

| 数据层 | 当前范围 | 作用 |
|---|---:|---|
| CEG PM2.5 | 8 个预定义省域，每区域 65–142 个单元 | 主实验与成对统计 |
| Natural Earth Africa | 50 个不规则国家多边形 | 不规则行政区泛化 |
| NCEP Africa | 401 个网格单元、12 个月 | 大规模与时间实验 |
| NASA Exoplanet Sky Grid | 162 个天球网格单元 | 非环境科学泛化 |
| Synthetic stress suite | 6 类形状 | 圆形、细长、L 形、凹 U 形、孔洞和非连通压力测试 |

数据集不在看到结果后剔除；方法共用随机种子 `20260827` 和统一参数表。

## 3. 最终显示邻接的提取

设原始参考边集为 \(E_r\)，显示多边形提取的边集为 \(E_d\)。两个显示多边形的边界距离不超过容差 \(\varepsilon\)，且缓冲后的共享区域超过数值噪声阈值时，认定为显示邻接。

- 默认容差：\(\varepsilon=2\times10^{-5}\)。
- 容差敏感性：\(10^{-6},5\times10^{-6},2\times10^{-5},10^{-4},5\times10^{-4}\)。
- 共享边界长度优先使用精确边界交集；只在数值上微小分离但仍处于容差内时，才用缓冲区面积估计长度。

所有正式拓扑得分都来自实际输出的最终多边形。

## 4. 核心拓扑指标

### 4.1 Adjacency Precision / Recall / F1

\[
P=\frac{|E_r\cap E_d|}{|E_d|},\qquad
R=\frac{|E_r\cap E_d|}{|E_r|},\qquad
F_1=\frac{2PR}{P+R}.
\]

- **Precision ↑**：显示邻接中真实邻接的比例；低 Precision 表示新增大量假边。
- **Recall ↑**：原始邻接中被保留的比例；低 Recall 表示丢失大量真实边。
- **F1 ↑**：Precision 和 Recall 的调和平均，是当前论文主要拓扑指标。

同时保留原始边数、显示边数、保留边数、丢失边数和新增边数，用于区分两种失真来源。

### 4.2 k-hop Neighborhood Preservation（NP@2 / NP@3）

对每个节点 \(v\)，取原始图与显示图中 \(k\) 步内的节点集 \(N_r^k(v)\) 和 \(N_d^k(v)\)：

\[
NP@k=\frac{1}{|V|}\sum_{v\in V}
\frac{|N_r^k(v)\cap N_d^k(v)|}{|N_r^k(v)\cup N_d^k(v)|}.
\]

- **NP@2 / NP@3 ↑**：评价比直接邻接更宽的局部结构。
- NP@2 为主要辅助指标，NP@3 保留在详细表中。

### 4.3 共享边界长度加权邻接

二值邻接将很短的接触和很长的共享边界视为同等边。项目使用原始与显示共享边界长度 \(l_r(e)\) 和 \(l_d(e)\) 补充评价：

\[
P_w=\frac{\sum_{e\in E_r\cap E_d}l_d(e)}{\sum_{e\in E_d}l_d(e)},\qquad
R_w=\frac{\sum_{e\in E_r\cap E_d}l_r(e)}{\sum_{e\in E_r}l_r(e)}.
\]

\(F_{1,w}\) 为 \(P_w\) 和 \(R_w\) 的调和平均。还报告归一化边界分布交集：

\[
O_w=\sum_{e\in E_r\cup E_d}
\min\left(\frac{l_r(e)}{\sum l_r},\frac{l_d(e)}{\sum l_d}\right).
\]

Weighted F1 衡量重要长边界是否保留，\(O_w\) 衡量原始与显示的内部边界长度分布是否相似，均为越高越好。

## 5. 节点级与边界/内部误差分解

全局 F1 可能掩盖边界和内部单元的差异。项目对每个单元计算：

| 指标 | 含义 | 方向 |
|---|---|---:|
| Node Adj. Precision / Recall / F1 | 以该节点的入射边为局部边集 | ↑ |
| Node Neighbor Jaccard | 原始和显示一阶邻居集的 Jaccard | ↑ |
| Degree Absolute Error | \(|deg_r(v)-deg_d(v)|\) | ↓ |
| Node Angular Error | 节点相对参考中心的方位角误差 | ↓ |
| Node Radial Rank Error | 原始与显示径向顺序的归一化排名差 | ↓ |
| Node Direction Error | 节点到原始邻居的平均方向误差 | ↓ |
| Neighbor-order Accuracy | 共同邻居对的顺/逆时针次序是否一致 | ↑ |

指标分别对 `boundary`、`interior` 和 `all` 节点求均值。边界组暴露圆形边界压缩和区域裁剪问题，内部组更多反映分区本身的拓扑保持能力。

## 6. 方向、方位与径向指标

### Local Direction Error（LDE）

对每条原始邻接边，比较原始空间与显示空间的方向角，使用环形角度差后求均值。原始经度差使用参考纬度的 \(\cos(\varphi)\) 缩放。

- **LDE（度）↓**：局部邻接方向的改变程度。
- 它是局部平面近似，不是大圆航向距离。

### Angular Error

比较单元在原始区域中相对参考中心的方位角 \(\theta_i\) 与显示质心极角。

- **Angular Error（度）↓**：全局方位保持程度。
- LDE 测局部邻接边方向，Angular Error 测全局方位，两者不可互相替代。

### Radial Spearman

用原始边界归一化径向值 \(\rho_i\) 与显示质心半径 \(r_i\) 计算 Spearman 排名相关系数。

- **Radial Spearman ↑**：“中心—边缘”顺序的保留程度，取值范围 \([-1,1]\)。
- 它只评价次序，不要求径向距离线性保真。

## 7. 几何合法性与面积平衡

| 指标 | 定义 | 方向 |
|---|---|---:|
| Area CV | \(\operatorname{std}(A_i)/\operatorname{mean}(A_i)\) | ↓ |
| Overlap Ratio | \((\sum_i A_i-A_{\cup})/A_{domain}\) | ↓，理想为 0 |
| Gap Ratio | \((A_{domain}-A_{union\cap domain})/A_{domain}\) | ↓，理想为 0 |
| Invalid Polygon Count | 空、无效或面积近零的多边形数 | ↓，理想为 0 |

Area CV 是显示面积均衡性，**不是原始地理面积保持**。比较方法时应先报告 Invalid/Overlap/Gap，再解释拓扑得分；否则 Direct Polar 等方法可能通过自交、重叠或未覆盖区域得到虚高邻接分数。

## 8. 跨视图一致性

对同一方法的 Disk 和 Annulus 边集计算：

\[
J(E_{disk},E_{annulus})=
\frac{|E_{disk}\cap E_{annulus}|}{|E_{disk}\cup E_{annulus}|}.
\]

**Disk–Annulus Edge Jaccard ↑** 衡量两种表达的拓扑相似性。当前只能描述为“相似但不完全相同”，不能声称严格拓扑不变。

## 9. 参考定义、敏感性与消融

### 9.1 4/8 邻域

- **4-neighbor**：只将网格边接触视为邻接（rook adjacency）。
- **8-neighbor**：加入对角线接触（queen adjacency）。

两种定义分别重新计算 Precision、Recall、F1 和 NP@2，用来判断方法排序是否依赖某一邻域规则，而不是为了挑选高分定义。

### 9.2 宏单元与省界裁剪

分别用完整保留宏单元和省界裁剪多边形建立参考邻接，并对单元纳入阈值 \(0,0.25,0.50,0.75\) 分析。两种策略会改变真值边集，必须分表报告，不能混合求均值。

### 9.3 其他敏感性与消融

- 空间粗化系数：3 / 4 / 5。
- 径向层数：4 / 5 / 6。
- 拓扑优化轮数：2 / 5 / 8。
- Warp 强度：0 / 0.01 / 0.02。
- 接触容差：5 个量级。
- 组件消融：拓扑优化、角度代价、径向层级、面积平衡、warp、多起点选择与最终多边形力迭代。

敏感性检查结论是否只在单一参数下成立；消融实验判断改善来自哪个组件。

## 10. 最终 Power Diagram 的内部优化目标

每个候选布局都完整生成平衡 Power 分区，再从最终多边形提取邻接。候选目标为：

\[
S = F_1 + 0.18NP@2
-0.06\frac{LDE}{180}
-0.04\frac{AE}{180}
-0.04\frac{1-\rho_s}{2}
-0.035\min(CV,2).
\]

候选起点包括 topology、harmonic、geographic 和两种 50/50 融合，随后对丢失参考边施加吸引，对新增显示边施加排斥。调度和权重对所有数据集一致，不做数据集级手工调参。

需明确区分：

- \(S\) 是算法选择布局的**内部目标**，不是论文用于声称优势的外部单一总分。
- 参考邻接图参与了优化，所以这是**有参考监督的布局优化**，不是无监督拓扑发现。
- 外部报告还需包括未直接进入目标的加权邻接、节点误差、几何合法性、外部领域和敏感性结果，减少“用同一指标优化又评价”带来的偏差。

## 11. 时间变化编码指标

所有月份复用同一最终几何和单元 ID。对比两种编码：

1. 前后两个月的标量值分箱重建后相减；
2. 直接使用对称发散色标编码月变化量。

标量值以 2%/98% 分位数为重建范围，直接差值以真实变化绝对值的 95% 分位数为对称上限。测试 5 / 7 / 9 / 13 档，9 档是预设主条件。

| 指标 | 计算方式 | 方向 |
|---|---|---:|
| Delta Sign Accuracy | 非零真实变化上预测增/减符号的正确率 | ↑ |
| Delta MAE | \(mean(|\widehat{\Delta}-\Delta|)\) | ↓ |
| Normalized Delta MAE | MAE 除以差值 95% 分位尺度 | ↓ |
| Delta Bias | \(mean(\widehat{\Delta}-\Delta)\) | 越接近 0 越好 |
| Magnitude Spearman | \(|\widehat{\Delta}|\) 与 \(|\Delta|\) 的 Spearman 相关 | ↑ |
| Top-10% Change Jaccard | 真实和预测绝对变化最大 10% 单元的 Jaccard | ↑ |
| High-change Event F1 | 以真实绝对变化的 75% 分位数为事件阈值 | ↑ |

`cell_identity_accuracy=1`、`geometry_centroid_drift=0` 和 `temporal_adjacency_jaccard=1` 是固定几何的构造性质，只证明时间对齐基础成立，不证明用户更准确或更快。

## 12. 统计比较

### 描述统计

每个方法—视图组合报告跨区域 mean、median 和 std，不只报告最优个例。

### Bootstrap 置信区间

- 重采样单位是省/区域，不是网格单元。
- 按区域有放回重采样 10,000 次，用 2.5% 和 97.5% 分位数作为 95% 区间。
- 方法比较先在同一区域计算成对差，再对差值 bootstrap。

### 成对符号翻转和 Holm 校正

对 GeoDisk-Final/GeoAnnulus-Final 与五个比较对象的成对差值使用双侧符号翻转检验。区域数不超过 16 时枚举全部符号组合，更大时用 Monte Carlo 近似。p 值在每个“视图 × 指标”族内对五个比较做 Holm 校正。Bootstrap 区间是未校正的描述性区间，不与校正后 p 值混为同一种推断。

时间编码在预设 9 档条件下，对“直接差值编码 − 由值分箱推导差值”的数据集—月份转换对进行 5,000 次 bootstrap。

## 13. 运行效率

对预定义的 50、130、162 和 401 单元数据集，单进程记录：

- `embedding_seconds`：拓扑嵌入时间。
- `original_power_seconds`：原始 Power 分区生成时间。
- `final_refinement_seconds`：最终 Power 邻接优化时间。
- `refinement_over_original_ratio`：细化时间与单次原始分区时间之比。

当前每个规模只运行 1 次，所以只是工程量级参考。正式效率结论建议在固定设备上预热后至少重复 10 次，补充中位数、IQR 和峰值内存。

## 14. 当前结果的正确解释

| 数据族 | 方法 | 视图 | 优化前 F1 | 最终 F1 | NP@2 | Invalid |
|---|---|---|---:|---:|---:|---:|
| CEG (8) | GeoDisk-Final | Disk | 0.660 | 0.780 | 0.644 | 0 |
| CEG (8) | GeoAnnulus-Final | Annulus | 0.630 | 0.748 | 0.640 | 0 |
| External (2) | GeoDisk-Final | Disk | 0.560 | 0.738 | 0.636 | 0 |
| External (2) | GeoAnnulus-Final | Annulus | 0.510 | 0.650 | 0.545 | 0 |
| Synthetic (6) | GeoDisk-Final | Disk | 0.618 | 0.771 | 0.636 | 0 |
| Synthetic (6) | GeoAnnulus-Final | Annulus | 0.605 | 0.715 | 0.605 | 0 |

在 8 个 CEG 区域上：

- GeoDisk-Final 对 Harmonic 的 F1 平均差为 `+0.053`，95% CI `[+0.017,+0.103]`；对 Area-balanced 为 `+0.046`，95% CI `[+0.031,+0.061]`。
- GeoAnnulus-Final 对 Harmonic 的 F1 平均差为 `+0.057`，对 Area-balanced 为 `+0.097`。
- Direct Polar 的平均邻接 F1 仍更高（Disk 0.862，Annulus 0.824），但部分输出存在无效、重叠或未覆盖几何。

因此可防御的结论是：**最终 Power 细化在保持几何合法的方法中建立了拓扑优势，但未建立对所有基线，特别是 Direct Polar 的无条件全面优势。**

NASA 天球网格上，GeoDisk-Final F1 为 0.764，高于最优合法 Disk 基线 Area-balanced 的 0.741；Direct Polar 受天球经度接缝影响，F1 为 0.324 且有 128 个无效多边形。这支持跨领域泛化，但仍只是一个非地理外部实例。

时间实验在 9 档、99 个数据集—转换对上，直接差值编码的符号准确率为 0.839，由值分箱推导为 0.702；归一化 MAE 为 0.0646 对 0.1127，幅度 Spearman 为 0.865 对 0.681。这支持“直接编码变化量更忠实”，仍不是人类感知结论。

## 15. 系统中的年度状态与迁移路径指标

前端还展示早期工程的“年度状态”和“迁移路径”。当前独立仓库为了可移植性，只携带 `frontend/public/data/legacy-insights.json` 结果快照，不携带它们的完整原始算法工程。因此本节定位为**系统展示和探索性证据**，不并入正式核心推断。

### 15.1 年度污染状态

快照包含：

- 176 个固定单元、2,112 条单元—月份记录；
- 全年 PM2.5 80% 分位阈值 `66.0268564`；
- S1（1–3 月）、S2（4–9 月）和 S3（10–12 月）的状态集合；
- 相邻月份热点 Jaccard、热点中心距离、中心相似度、面积相似度和复合相似度；
- 单元热点频率、年均 PM2.5 和 S1/S2/S3 成员关系；
- 圆环 Area CV `0.2665`，对原始邻接 F1 `0.6065`，对上一步布局邻接 F1 `0.8046`。

热点状态、重叠类型和连接桥是模式摘要，不是有标注真值的分类准确率。如要成为论文主实验，需恢复完整源码、固定复合相似度公式，并增加状态分段基线和变点检测评价。

### 15.2 迁移路径

快照中的路径评价字段包括：

- **Temporal Edge F1 ↑**：预测时间有向边与参考边的 F1。
- **Move-edge F1 ↑**：只评价跨区域移动边，排除原地停留边。
- **Sequence Accuracy ↑**：路径序列与参考序列的状态一致程度。
- **Transition Accuracy ↑**：连续时刻转移判定正确率。
- **Normalized Edit Distance ↓**：预测路径与参考路径的归一化编辑距离。

快照使用 0–6 号窗口开发、7–10 号窗口缓冲、11–17 号窗口留出评价。面积归一化 Gateway 在留出集上的 Move-edge F1 为 `0.2286`、Temporal Edge F1 为 `0.2476`、Sequence Accuracy 为 `0.2857`、Normalized Edit Distance 为 `0.6429`。

这些结果表明迁移推断仍很弱，只适合方法流程展示和失败分析，不支持高准确路径预测声称。由于独立仓库只有快照，本文档不把字段名的常见解释冒充为已审计的精确旧代码公式。

## 16. 用户实验指标（已设计，尚未采集）

已生成 96 个试次，覆盖 Geographic Map 和 DeltaAnnulus 两条件、两数据集、六个时间转换与四类任务：变化定位、增减判断、时间比较和径向传播。

- **主结局**：变化定位准确率。
- **主对比**：DeltaAnnulus 减 Geographic Map。
- **次要结局**：各任务准确率、正确试次的对数反应时、信心度。
- **主模型**：二项混合效应回归，参与者和刺激为随机截距，收敛时加入参与者条件随机斜率。
- **样本量**：\(d_z=0.5\)、双侧 \(\alpha=0.05\)、power = 0.80 时需 34 名有效完整参与者；考虑 15% 损耗后招募 40 人。

现阶段没有参与者数据，不能宣称感知准确率、完成时间或认知效率优势。

## 17. 论文中建议的指标层级

### 主指标

1. Invalid Polygon Count、Overlap Ratio、Gap Ratio。
2. Adjacency F1。
3. 区域级成对差、95% bootstrap CI、符号翻转 p 值和 Holm 校正。

### 关键辅助指标

1. NP@2 和共享边界加权 F1。
2. 边界/内部 Node F1、方向误差和邻居环序准确率。
3. LDE、Angular Error 和 Radial Spearman。
4. Area CV、4/8 邻域、裁剪策略和容差敏感性。

### 时间编码指标

1. Delta Sign Accuracy 和 Normalized Delta MAE。
2. Magnitude Spearman、Top-10% Jaccard 和 High-change Event F1。
3. 将固定身份/质心/邻接指标明确标为构造性质。

### 附录或探索性内容

NP@3、边数详细分解、单次运行时间、年度状态摘要、当前尚弱的迁移路径快照和尚未实施的用户实验。

## 18. 当前不能推出的结论

- 不能声称 GeoDisk/GeoAnnulus 在所有数据和所有基线上全面最优。
- 不能忽略 Direct Polar 的几何非法性，也不能隐藏它在 CEG 邻接 F1 上仍更高。
- 不能将 Area CV 描述为地理面积保真。
- 不能将跨月份几何不变描述为用户认知性能证据。
- 不能把旧工程结果快照视为与当前 E0–E24 一样可完整复现的实验。
- 不能用单次运行时间声称稳定效率优势。
- 用户实验完成前，不能声称“更易读”、“更快”或“认知负担更低”。

## 19. 指标与代码/结果的对应

| 内容 | 位置 |
|---|---|
| 拓扑、邻域、方向、径向和节点级指标 | `backend/src/geodisk_paper/metrics/spatial.py` |
| 显示邻接、共享边界和几何合法性 | `backend/src/geodisk_paper/metrics/geometry.py` |
| 第一轮空间评价 | `backend/experiments/E4_spatial_fidelity.py` |
| 节点分解和加权邻接 | `backend/experiments/E17_advanced_spatial_errors.py` |
| 4/8 邻域和裁剪敏感性 | `backend/experiments/E18_reference_sensitivity.py` |
| 最终 Power 细化 | `backend/experiments/E19_final_power_refinement.py` |
| 成对统计检验 | `backend/experiments/E20_refined_statistics.py` |
| 时间变化指标 | `backend/experiments/E6_change_metrics.py` |
| 用户实验 | `backend/experiments/E21_user_study_materials.py` 和 `backend/user_study/PREREGISTRATION_DRAFT.md` |
| 运行时间 | `backend/experiments/E23_runtime_scalability.py` |
| 核心结果表 | `backend/results/tables/` |
| 论文用表 | `backend/paper/tables/` |
| 历史状态/迁移快照 | `frontend/public/data/legacy-insights.json` |

## 20. 可直接用于论文的总结表述

> 我们将几何合法性与空间忠实度分开评价。所有邻接均从最终显示多边形中重新提取。主要拓扑指标为 Adjacency F1，辅以 NP@2、共享边界长度加权 F1、边界/内部节点误差、局部方向误差、角度误差和径向 Spearman 相关。方法差异在区域级成对计算，使用 10,000 次 bootstrap 置信区间和成对符号翻转检验，并在同一视图—指标族内进行 Holm 校正。结果表明，GeoDisk-Final 和 GeoAnnulus-Final 在保持零无效多边形的同时，优于 Harmonic 和 Area-balanced 等合法几何基线；但 Direct Polar 在 CEG 邻接 F1 上仍更高且伴随几何无效与重叠，因此我们不作无条件全面优越的声称。

