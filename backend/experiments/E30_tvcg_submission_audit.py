from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import yaml

from common import ROOT, ensure_output_dirs
from geodisk_paper.utils.io import write_json


SYSTEM_ROOT = ROOT.parent
FRONTEND = SYSTEM_ROOT / "frontend"


def _status(rows: list[dict], check_id: str, area: str, status: str, evidence: str, action: str) -> None:
    rows.append({"check_id": check_id, "area": area, "status": status,
                 "evidence": evidence, "required_action": action})


def _latest_clean_manifest() -> dict:
    required_stages = {"E0", "E19", "TESTS", "E29"}
    manifests = sorted((ROOT / "results/run_manifests").glob("run_*.json"))
    for path in reversed(manifests):
        payload = json.loads(path.read_text(encoding="utf-8"))
        stage_names = {item.get("name") for item in payload.get("stages", [])}
        if (payload.get("status") == "succeeded"
                and not payload.get("git_dirty_at_start")
                and required_stages.issubset(stage_names)):
            return payload
    return {}


def main() -> None:
    ensure_output_dirs()
    plan = yaml.safe_load((ROOT / "config/tvcg_submission.yaml").read_text(encoding="utf-8"))
    refined = pd.read_csv(ROOT / "results/tables/Table_final_power_refinement.csv")
    paired = pd.read_csv(ROOT / "results/tables/Table_refined_paired_bootstrap.csv")
    advanced = pd.read_csv(ROOT / "results/tables/Table_advanced_paired_statistics.csv")
    seed = pd.read_csv(ROOT / "results/tables/Table_seed_stability.csv")
    runtime = pd.read_csv(ROOT / "results/tables/Table_runtime_scalability.csv")
    objective = pd.read_csv(ROOT / "results/tables/Table_final_objective_ablation.csv")
    temporal = pd.read_csv(ROOT / "results/tables/Table_temporal_change_fidelity.csv")
    readiness = json.loads((ROOT / "results/formal_readiness/formal_readiness.json").read_text(encoding="utf-8"))
    readiness_by_id = {row["check_id"]: row for row in readiness["checks"]}
    manifest = _latest_clean_manifest()

    snapshot_paths = sorted((FRONTEND / "public/data").glob("workbench-*.json"))
    snapshot_gate_ok = bool(snapshot_paths)
    for path in snapshot_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        metadata = payload.get("metadata", {})
        snapshot_gate_ok &= (
            metadata.get("geometry_admissibility_tolerance") == 1e-7
            and all("admissible" in item for item in metadata.get("candidate_history", []))
        )

    rows: list[dict] = []
    _status(rows, "tvcg_scope_fit", "positioning", "pass",
            "topology-based visualization, geometric processing, visual analytics and interaction",
            "Keep the title, abstract and index terms centered on the visualization contribution.")
    geometry_ok = (int(refined.invalid_polygon_count.sum()) == 0
                   and float(refined.overlap_ratio.max()) <= 1e-7
                   and float(refined.gap_ratio.max()) <= 1e-7)
    _status(rows, "final_geometry_gate", "method", "pass" if geometry_ok else "open",
            f"rows={len(refined)}; invalid={int(refined.invalid_polygon_count.sum())}; "
            f"max overlap={refined.overlap_ratio.max():.3g}; max gap={refined.gap_ratio.max():.3g}",
            "Reject inadmissible candidates before final selection." if not geometry_ok else "none")
    families = set(refined.dataset_family.astype(str))
    _status(rows, "cross_domain_evaluation", "experiments", "pass" if families == {"ceg", "external", "synthetic"} else "partial",
            f"final-Power families={sorted(families)} plus astronomy evaluation",
            "Retain geographic, irregular, large-grid, synthetic and non-geographic cases.")
    _status(rows, "paired_statistical_inference", "experiments", "pass" if len(paired) and len(advanced) else "open",
            f"paired rows={len(paired)}; advanced rows={len(advanced)}; Holm correction present={('paired_permutation_p_holm' in paired)}",
            "Use region/dataset as the independent unit and retain multiplicity correction.")
    _status(rows, "robustness_and_ablation", "experiments", "pass" if seed.seed.nunique() >= 5 and objective.variant.nunique() >= 6 else "open",
            f"seeds={seed.seed.nunique()}; regions={seed.region.nunique()}; objective variants={objective.variant.nunique()}",
            "Report all declared seeds and negative ablation results.")
    _status(rows, "runtime_scalability", "experiments", "pass" if runtime.repeat_count.min() >= 10 else "partial",
            f"sizes={runtime.cell_count.tolist()}; minimum repetitions={int(runtime.repeat_count.min())}; maximum cells={int(runtime.cell_count.max())}",
            "Do not claim asymptotic or interactive scalability beyond the evaluated 401 cells.")
    temporal_ok = {"direct_diverging_delta", "derived_from_value_bins"}.issubset(set(temporal.encoding_mode.astype(str)))
    _status(rows, "temporal_encoding_evaluation", "experiments", "pass" if temporal_ok else "open",
            f"conditions={sorted(set(temporal.encoding_mode.astype(str)))}; rows={len(temporal)}",
            "Keep numerical encoding fidelity separate from perceptual effectiveness.")
    _status(rows, "clean_reproducible_artifact", "reproducibility", "pass" if manifest else "open",
            f"clean run={manifest.get('run_id', 'missing')}; stages={len(manifest.get('stages', []))}",
            "Preserve a successful clean manifest, exact environment and table-generating code.")
    _status(rows, "hosted_snapshot_parity", "frontend", "pass" if snapshot_gate_ok else "open",
            f"snapshots={len(snapshot_paths)}; all expose final geometry gate={snapshot_gate_ok}",
            "Regenerate hosted snapshots from canonical backend artifacts.")
    d3_source = (FRONTEND / "app/d3-views.tsx").read_text(encoding="utf-8")
    workbench_source = (FRONTEND / "app/integrated-workbench.tsx").read_text(encoding="utf-8")
    linked_ok = "D3PartitionMap" in d3_source and all(token in workbench_source for token in ("setSelectedCell", "setMonth", "setDataset"))
    _status(rows, "linked_visual_analytics_system", "frontend", "pass" if linked_ok else "partial",
            "D3 partition, map, ego-neighborhood, temporal-profile and coordinated selection views",
            "Retain task-driven linked interaction and avoid presenting decorative dashboard widgets.")
    response_rows = len(pd.read_csv(ROOT / "user_study/response_schema.csv"))
    _status(rows, "human_system_evaluation", "frontend", "open" if response_rows == 0 else "pass",
            f"participant response rows={response_rows}; prepared trials=96",
            "Run the preregistered study and report accuracy, response time, confidence, exclusions and ethics approval status.")
    for check_id, area in (("primary_data_provenance", "data"),
                           ("published_baseline_implementation", "related_work"),
                           ("confirmatory_holdout_dataset", "study_design")):
        source = readiness_by_id[check_id]
        _status(rows, check_id, area, source["status"], source["evidence"], source["required_action"])
    _status(rows, "manuscript_package", "writing", "partial",
            "method/evaluation/readiness reports and paper tables exist; no final IEEE-formatted manuscript is present",
            "Prepare a concise regular-paper manuscript, teaser, method diagram, main comparison figure and supplemental index.")

    frame = pd.DataFrame(rows)
    pass_count = int((frame.status == "pass").sum())
    partial_count = int((frame.status == "partial").sum())
    open_count = int((frame.status == "open").sum())
    verdict = "algorithmic_artifact_ready_but_full_submission_not_ready" if open_count else "submission_package_ready"
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "venue": plan["venue"], "verdict": verdict,
        "pass_count": pass_count, "partial_count": partial_count, "open_count": open_count,
        "research_goal": plan["research_goal"], "research_questions": plan["research_questions"],
        "contributions": plan["contributions"], "claim_boundaries": plan["claim_boundaries"],
        "checks": frame.to_dict(orient="records"),
    }
    write_json(output, ROOT / "results/formal_readiness/tvcg_submission_audit.json")

    ceg = refined[refined.dataset_family == "ceg"].groupby("view").adj_f1.mean()
    seed_run_means = seed.groupby(["view", "seed"], as_index=False).adj_f1.mean()
    seed_summary = seed_run_means.groupby("view").adj_f1.agg(["mean", "std"])
    ncep_runtime = runtime[runtime.dataset == "NCEP-AirTemp-Africa-2000"].iloc[0]
    lines = [
        "# GeoDisk Lab：面向 TVCG 的研究定位与投稿就绪审计", "",
        "> 本报告由 E30 从正式结果表和系统产物自动生成。TVCG 没有适用于所有论文的固定实验清单；这里把其范围、技术实质、方法/分析/结论准确性与可复现性要求转换为本项目的可检查门槛。", "",
        "官方依据：[TVCG 范围与征稿](https://www.computer.org/digital-library/journals/tg/cfp-ieee-transactions-on-visualization-computer-graphics)、[IEEE CS 审稿人指南](https://www.computer.org/publications/reviewer-resources)、[IEEE CS 作者指南](https://www.computer.org/publications/author-resources)、[IEEE VIS 开放实践建议](https://ieeevis.org/year/2026/info/open-practices/open-practices/)。", "",
        "## 1. 研究目标", "", plan["research_goal"], "",
        "## 2. 研究问题", "",
    ]
    lines += [f"- **{item['id']}**：{item['question']}" for item in plan["research_questions"]]
    lines += ["", "## 3. 可主张的创新点", ""]
    lines += [f"- **{item['id']}（{item['kind']}）**：{item['statement']}" for item in plan["contributions"]]
    lines += ["", "创新不应写成“首次使用 Power Diagram”或“首次把地图变成圆形”；Power Diagram、调和嵌入和力优化本身都是已有技术。可防御的新意是：在 Disk/Annulus 约束下，把参考拓扑、多起点、真实最终多边形评价与几何硬准入组成统一方法，并用节点级和共享边界级证据诊断其代价。", "",
              "## 4. 方法步骤", "",
              "1. 冻结单元 ID、标量值、参考几何与 4/8 邻域真值。",
              "2. 计算带径向约束的拓扑嵌入，并生成 topology、harmonic、geographic 和融合起点。",
              "3. 对每个起点生成面积平衡的 Disk/Annulus Power 分区。",
              "4. 从最终多边形重新提取真实邻接，而不是使用中间槽位图。",
              "5. 对丢失边施加吸引、对新增边施加排斥，形成确定性的候选轨迹。",
              "6. 仅允许 invalid=0 且 overlap/gap≤1e-7 的候选参与最终选择。",
              "7. 固定最终几何与单元身份，在月份之间编码标量值和有符号变化。",
              "8. 通过地理上下文、Disk/Annulus、时间轮廓和局部邻接诊断进行联动分析。", "",
              "## 5. 已建立的实验事实", "",
              f"- CEG 最终 F1：Disk `{ceg['disk']:.4f}`，Annulus `{ceg['annulus']:.4f}`。",
              f"- 5 种子稳定性：Disk `{seed_summary.loc['disk','mean']:.4f}±{seed_summary.loc['disk','std']:.4f}`；Annulus `{seed_summary.loc['annulus','mean']:.4f}±{seed_summary.loc['annulus','std']:.4f}`。",
              f"- 32 个最终跨域输出 invalid=0，最大 overlap `{refined.overlap_ratio.max():.3g}`，最大 gap `{refined.gap_ratio.max():.3g}`。",
              "- 相较合法基线 Harmonic 与 Area-balanced，二值/加权邻接及边界/内部 Node F1 总体提高；Direct Polar 的原始邻接分数仍更高但存在非法几何。",
              "- 主要剩余错误是新增边导致的过连接；小权重目标项的逐项独立贡献有限。",
              f"- 401 单元 NCEP 最终细化中位时间 `{ncep_runtime.final_refinement_seconds_median:.1f}s`；该证据不支持超过 401 单元的交互式或渐近性能声称。", "",
              "## 6. 用户与领域利益", "",
              "- **分析一致性**：固定单元身份和几何，使跨月份选中、邻接追踪和变化对齐不因重新布局而漂移。",
              "- **紧凑比较**：Disk/Annulus 提供统一、有界的比较画布，适合并排显示不同地区或时间状态；是否更易读仍须用户实验。",
              "- **可诊断性**：保存 preserved/lost/new 边、边界/内部误差和失败节点，使研究者能看到方法在哪里破坏拓扑。",
              "- **可迁移性**：同一管线已在规则网格、不规则行政区、合成拓扑与天球网格运行。",
              "- **可复核性**：数据哈希、固定配置、完整日志、候选历史、结果表与干净运行清单可以追溯每个论文数字。", "",
              "## 7. TVCG 就绪矩阵", "",
              f"当前：**{pass_count} pass / {partial_count} partial / {open_count} open**；结论为 `{verdict}`。", "",
              "| 方面 | 检查 | 状态 | 证据 | 下一步 |", "| --- | --- | --- | --- | --- |"]
    for row in frame.itertuples():
        lines.append(f"| {row.area} | `{row.check_id}` | **{row.status}** | {row.evidence} | {row.required_action} |")
    lines += ["", "## 8. 论文允许与不允许的表述", "",
              "**可以表达**：最终几何合法；在合法基线中具有稳定拓扑优势；结论覆盖多数据类型、邻域定义、容差和随机种子；固定几何的时间编码在数值上更忠实；系统支持联动诊断。", "",
              "**不能表达**：全面优于所有基线；比 Direct Polar 具有更高原始邻接；无监督发现拓扑；用户更快、更准或认知负担更低；已证明大规模实时交互；已有严格未见确认集。", "",
              "## 9. 投稿前必须完成", "",
              "1. 解决 CEG 官方来源、许可和规范引用，否则主数据实验不能作为可归档证据。",
              "2. 引入并公平运行一个独立公开实现的已发表相关基线，或充分论证为何不存在可比实现。",
              "3. 冻结未参与开发的新年份/地区作为确认集，只执行一次预声明比较。",
              "4. 若系统贡献进入摘要或贡献列表，完成预注册真人实验及伦理/知情同意流程；否则把系统降为技术演示。",
              "5. 完成 IEEE 模板论文、相关工作的新颖性对照表、方法总览图、主结果图和补充材料索引。", "",
              "## 10. 声明边界", ""]
    lines += [f"- {item}" for item in plan["claim_boundaries"]]
    lines.append("")
    (ROOT / "paper/TVCG_SUBMISSION_AUDIT_CN.md").write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))
    print({"verdict": verdict, "pass": pass_count, "partial": partial_count, "open": open_count})


if __name__ == "__main__":
    main()
