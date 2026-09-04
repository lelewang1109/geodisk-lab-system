# Published Baseline 候选与公平比较边界

> 核查日期：2026-09-04。本文仅做候选与接口分析；仓库尚未运行任何下述独立实现，因此 `published_baseline_implementation` 必须继续标记为 **open**。

## 选择原则

只有同时满足以下条件的方法才能进入正式主比较：能使用冻结 Cell ID；不从 PM2.5 结果反向调参；能导出点或多边形与 Cell ID 的确定映射；参数对所有数据集统一；对其本来不保证的属性不设置不公平的硬门槛。

| 类别 | 候选论文/方法 | 公开代码核查 | 与本项目的输入兼容性 | 可公平比较 | 不可直接比较 | 建议 |
| --- | --- | --- | --- | --- | --- | --- |
| topology / neighborhood-preserving grid layout | Eppstein, van Kreveld, Speckmann, Staals, *Improved Grid Map Layout by Point Set Matching*, IEEE PacificVis 2013 / IJCGA 2015，DOI 10.1109/PacificVis.2013.6596124。论文将区域质心与网格 tile 的一对一匹配作为核心。[作者论文页](https://fstaals.net/publications/visualization/gridmaps2013/) | 作者页提供论文/幻灯片，但本次未核实到可直接冻结的官方参考实现；另有 `gridmappr` 等后续工具，但不能默认为原论文算法的等价实现 | CEG/NCEP 的 macro-cell 质心和 Cell ID 可直接适配；Natural Earth 也可用 polygon centroid。需先声明 tile grid 尺寸与空 tile 策略 | Cell identity、binary adjacency F1、NP@2、relative direction/location error、runtime | area CV/overlap/gap 与 GeoDisk Power cells 不同义；非 disk/annulus domain；不能比 radial Spearman 作为共同主目标 | **高优先级候选**。先取得/实现论文匹配求解器，预声明 tile 数和并列规则，作为 canonical grid 类 baseline，不宣称它是 disk 竞争者 |
| topology-preserving projection | Doraiswamy et al., *TopoMap: A 0-dimensional Homology Preserving Projection of High-Dimensional Data*, TVCG 2021。它保持 Rips filtration 的 0-dimensional persistence diagram，而不是保证用户给定的 rook-adjacency graph。[论文预印本](https://arxiv.org/abs/2009.01512) | 论文存在；本次没有核实到能在当前 Python 3.9 环境直接冻结的官方版本/许可，故不记为可运行 | 需把地理单元变成距离或特征点云；可输出 2D points，但需另外定义 polygonization，且会改变原方法的评价对象 | 若只比点布局：Cell ID、kNN/NP@k、局部方向、runtime | 不能把 0D homology guarantee 写成 reference adjacency guarantee；没有同构 polygon partition 时不能公平比 area CV、gap/overlap、shared-boundary F1；不受 disk/annulus 约束 | **只建议 Supplement/概念对照**。不是当前主问题最直接的 published baseline |
| contiguous / area-balanced cartogram | Gastner, Seguy, More, *Fast flow-based algorithm for creating density-equalizing map projections*, PNAS 2018，DOI 10.1073/pnas.1712674115。流场映射生成连续面积 cartogram。[论文 PDF](https://michael-gastner.com/publications/full_text_pub/GastnerSeguyMore2018.pdf) | 论文明确附 C 代码；现有公开 WebAssembly 封装也声明源自参考实现，并要求输入为等积投影的 Polygon/MultiPolygon GeoJSON。[`go-cart-wasm`](https://github.com/riatelab/go-cart-wasm) | Natural Earth 多边形最兼容。CEG/NCEP 可将 macro-cell 在等积 CRS 中建图，但要先决定外部空白域与目标面积；直接用 EPSG:4326 是错误接口 | Cell identity、polygon validity、binary/weighted adjacency、方向/相对位置误差、area error、runtime | 它保留原地理外形，不构造 canonical disk/annulus；radial order 不是其目标；不能用本项目 circular-domain gap 直接惩罚 | **最值得真实集成的 cartogram baseline**。建议先在 Natural Earth 上做可复现 adapter，再预声明 CEG 等积投影和统一面积目标 |
| canonical circular / disk-like cartogram | Kämper, Kobourov, Nöllenburg, *Circular-Arc Cartograms*, PacificVis 2013 / arXiv:1112.4626。用圆弧多边形表示平面拓扑。[论文 PDF](https://www2.cs.arizona.edu/~kobourov/circcarto-pacificvis.pdf) | 本次未核实到受支持的公开参考实现；不得根据论文图自行写一个“看起来像”的替代物 | 输入需要平面邻接图与可实现条件；CEG 4-neighbor graph 是平面的，但 hole/disconnected/Natural Earth 需要单独检查方法前提 | 若能运行：Cell ID、binary adjacency、NP@2、polygon validity、area error | 方法追求平面拓扑/面积的可表示性，不等于本项目的径向/角度地理约束；不能假定任意输入都有解 | **理论相关度高，工程风险高**。只在找到可许可、可编译的作者实现并确认输入可实现后加入 |
| hybrid data-spatial grid map | van Beusekom, Meulemans, Speckmann, Wood, *Data-Spatial Layouts for Grid Maps*, GIScience 2023，DOI 10.4230/LIPIcs.GIScience.2023.10。在 spatial 与 data-driven tile placement 之间提供连续权衡。[开放论文](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.GIScience.2023.10)，[软件链接](https://github.com/nvbeusekom/dataspatia) | 论文页声明 supplementary source code；尚未在本仓库冻结 commit/许可/环境 | 需区域质心、标量值和目标网格；可用于 CEG/NCEP，但 data-driven 权重会把时间标量混入 geometry，与 fixed-geometry 目标冲突 | 冻结 spatial-only 参数时：Cell ID、adjacency/NP@2、方向/位置误差、runtime | 不能让每月数值重排 geometry 后再与 fixed-identity temporal claim 比较；非 polygon Power partition，非 disk/annulus | **适合 Supplement 稳健性对照**。只使用事先冻结的 spatial-only 设定，或将 data-driven 版本明确标为不同任务 |

## 推荐的最小可执行路线

1. 主集成优先选 Gastner–Seguy–More，但先限定 Natural Earth：它有真实多边形、最少的语义转换和可核对的官方算法链。
2. 主 canonical-layout 对照优先选 Eppstein et al. grid map，但必须先解决参考实现与 tile-grid 尺寸的预声明。
3. TopoMap 不应被当成“更强的拓扑保留”主基线：它保证的拓扑不变量与本项目的 reference adjacency 不同。
4. Circular-Arc Cartograms 只在真实实现可获得且输入满足前提时加入；否则只用于 Related Work，不伪造 implementation。

## 当前 TODO

- TODO：对最终选定的第三方实现冻结 repository URL、commit、license、编译环境与输入/输出 adapter。
- TODO：在查看结果前声明参数、失败处理、运行时范围和公共指标。
- TODO：真实运行并保存 GeoJSON/CSV/log/manifest；在此之前不向主论文添加数值。
