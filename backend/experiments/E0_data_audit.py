from common import ROOT, dataset_config, ensure_output_dirs, resolve_project_path
from geodisk_paper.data.adapters import DailyNetCDFAdapter
from geodisk_paper.data.audit import audit_dataset


def main():
    ensure_output_dirs()
    config = dataset_config()
    adapter = DailyNetCDFAdapter(resolve_project_path(config["raw_dir"]), config["filename_glob"], config.get("scalar_variable"))
    summary = audit_dataset(adapter, ROOT / "results/data_audit", config)
    print(summary)


if __name__ == "__main__":
    main()

