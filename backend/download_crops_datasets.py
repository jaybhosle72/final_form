"""
Downloader & File Copy Manager for 12 Kaggle Agricultural Datasets
Uses kagglehub to download datasets independently and copy contents into project data/crops/
Generates data/crops/download_report.json and data/crops/DOWNLOAD_REPORT.md
"""

import os
import sys
import shutil
import json
import datetime
import pathlib
import kagglehub

# Base Target Directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_BASE_DIR = os.path.join(PROJECT_ROOT, "data", "crops")

DATASETS_TO_DOWNLOAD = [
    {
        "id": "sakshi21122001/crop-recommendation-with-water-data",
        "folder": "crop_recommendation_water",
        "label": "Crop Recommendation with Water Data"
    },
    {
        "id": "dsmlindian/crop-data-maharashtra",
        "folder": "maharashtra_crop_data",
        "label": "Crop Data Maharashtra"
    },
    {
        "id": "sushilyeotiwad/crop-recommendation-dataset",
        "folder": "crop_recommendation",
        "label": "Crop Recommendation Dataset"
    },
    {
        "id": "mayankmohapatra77/crop-and-fertilizer-dataset",
        "folder": "crop_fertilizer",
        "label": "Crop and Fertilizer Dataset"
    },
    {
        "id": "irakozekelly/fertilizer-prediction",
        "folder": "fertilizer_prediction",
        "label": "Fertilizer Prediction"
    },
    {
        "id": "vedikasd/crop-data-for-yield-and-recommendation-analysis",
        "folder": "crop_yield_recommendation",
        "label": "Crop Data for Yield & Recommendation Analysis"
    },
    {
        "id": "vishvavardhanbhasham/crop-recommendation-with-medicine",
        "folder": "crop_medicine_recommendation",
        "label": "Crop Recommendation with Medicine"
    },
    {
        "id": "aniketkumaraugustya/soil-type-dataset",
        "folder": "soil_type",
        "label": "Soil Type Dataset"
    },
    {
        "id": "sashankgarg23/crop-dataset",
        "folder": "crop_dataset",
        "label": "Crop Dataset"
    },
    {
        "id": "javakhan/crops-npk-data-set",
        "folder": "crop_npk",
        "label": "Crops NPK Data Set"
    },
    {
        "id": "sanketgondaliya/fertilizer",
        "folder": "fertilizer",
        "label": "Fertilizer Dataset"
    },
    {
        "id": "ziya07/agricultural-nutrient-loss-dataset",
        "folder": "nutrient_loss",
        "label": "Agricultural Nutrient Loss Dataset"
    }
]

def ensure_directory(path):
    os.makedirs(path, exist_ok=True)

def copy_dataset_files(src_dir, dest_dir):
    copied_files = []
    skipped_files = []

    src_path = pathlib.Path(src_dir)
    dest_path = pathlib.Path(dest_dir)

    ensure_directory(dest_path)

    for root, dirs, files in os.walk(src_path):
        rel_root = pathlib.Path(root).relative_to(src_path)
        target_root = dest_path / rel_root
        ensure_directory(target_root)

        for file_name in files:
            src_file = pathlib.Path(root) / file_name
            target_file = target_root / file_name

            file_size = src_file.stat().st_size
            ext = src_file.suffix.lower()

            if target_file.exists() and target_file.stat().st_size == file_size:
                skipped_files.append({
                    "file_name": str(rel_root / file_name),
                    "size_bytes": file_size,
                    "reason": "Identical file already exists"
                })
            else:
                shutil.copy2(src_file, target_file)
                copied_files.append({
                    "file_name": str(rel_root / file_name),
                    "size_bytes": file_size,
                    "format": ext.replace(".", "")
                })

    return copied_files, skipped_files

def run_download_pipeline():
    print(f"=== NABARD Agricultural Datasets Downloader ===")
    print(f"Target Base Path: {TARGET_BASE_DIR}\n")
    ensure_directory(TARGET_BASE_DIR)

    report_entries = []
    total_success = 0
    total_failed = 0

    for item in DATASETS_TO_DOWNLOAD:
        handle = item["id"]
        folder_name = item["folder"]
        label = item["label"]
        dest_folder = os.path.join(TARGET_BASE_DIR, folder_name)

        print(f"Processing ({len(report_entries)+1}/12): {handle} -> {folder_name}")

        entry = {
            "dataset_handle": handle,
            "label": label,
            "destination_folder": dest_folder,
            "status": "PENDING",
            "cache_path": None,
            "copied_files": [],
            "skipped_files": [],
            "error_message": None,
            "timestamp": datetime.datetime.now().isoformat()
        }

        try:
            cache_path = kagglehub.dataset_download(handle)
            entry["cache_path"] = cache_path

            if os.path.exists(cache_path):
                copied, skipped = copy_dataset_files(cache_path, dest_folder)
                entry["copied_files"] = copied
                entry["skipped_files"] = skipped
                entry["status"] = "SUCCESS"
                total_success += 1
                print(f"  -> SUCCESS! Copied {len(copied)} files to {dest_folder}")
            else:
                entry["status"] = "FAILED"
                entry["error_message"] = "Downloaded cache path does not exist."
                total_failed += 1
                print(f"  -> FAILED: Cache path not found.")
        except Exception as e:
            entry["status"] = "FAILED"
            entry["error_message"] = str(e)
            total_failed += 1
            print(f"  -> FAILED: {e}")

        report_entries.append(entry)

    summary_report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_datasets": len(DATASETS_TO_DOWNLOAD),
        "successful_downloads": total_success,
        "failed_downloads": total_failed,
        "destination_base_directory": TARGET_BASE_DIR,
        "datasets": report_entries
    }

    # Save JSON Report
    json_report_path = os.path.join(TARGET_BASE_DIR, "download_report.json")
    with open(json_report_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    # Save Markdown Report
    md_report_path = os.path.join(TARGET_BASE_DIR, "DOWNLOAD_REPORT.md")
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write("# Kaggle Agricultural Datasets Download Report\n\n")
        f.write(f"- **Execution Timestamp**: {summary_report['timestamp']}\n")
        f.write(f"- **Total Datasets Target**: {summary_report['total_datasets']}\n")
        f.write(f"- **Successful Downloads & Copies**: {total_success}\n")
        f.write(f"- **Failed Downloads**: {total_failed}\n")
        f.write(f"- **Destination Directory**: `{TARGET_BASE_DIR}`\n\n")
        f.write("---  \n\n")
        f.write("## Dataset Ingestion Summary\n\n")
        f.write("| # | Dataset Handle | Status | Folder Name | Files Copied | Error Message |\n")
        f.write("|---|---|---|---|---|---|\n")

        for idx, entry in enumerate(report_entries, 1):
            status_icon = "🟢 SUCCESS" if entry["status"] == "SUCCESS" else "🔴 FAILED"
            err = entry["error_message"] or "None"
            f.write(f"| {idx} | `{entry['dataset_handle']}` | {status_icon} | `{entry['destination_folder']}` | {len(entry['copied_files'])} | {err} |\n")

    print(f"\nDownload pipeline finished! Report generated at:")
    print(f" - {json_report_path}")
    print(f" - {md_report_path}")
    return summary_report

if __name__ == "__main__":
    run_download_pipeline()
