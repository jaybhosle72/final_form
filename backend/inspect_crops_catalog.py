import os
import json
import csv
import glob
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROPS_DIR = os.path.join(BASE_DIR, "data", "crops")
OUTPUT_CATALOG_JSON = os.path.join(BASE_DIR, "data", "catalog.json")
OUTPUT_CATALOG_MD = os.path.join(BASE_DIR, "data", "DATA_CATALOG.md")
OUTPUT_INGESTION_REPORT = os.path.join(BASE_DIR, "data", "ingestion_report.json")

DATASETS_CONFIG = [
    {
        "id": "crop_recommendation_water",
        "handle": "sakshi21122001/crop-recommendation-with-water-data",
        "folder": "crop_recommendation_water",
        "domain": "Crop Recommendation & Water Requirements"
    },
    {
        "id": "maharashtra_crop_data",
        "handle": "dsmlindian/crop-data-maharashtra",
        "folder": "maharashtra_crop_data",
        "domain": "Maharashtra District Crop Production & Yield"
    },
    {
        "id": "crop_recommendation",
        "handle": "sushilyeotiwad/crop-recommendation-dataset",
        "folder": "crop_recommendation",
        "domain": "Soil NPK & Climate Crop Recommendation"
    },
    {
        "id": "crop_fertilizer",
        "handle": "mayankmohapatra77/crop-and-fertilizer-dataset",
        "folder": "crop_fertilizer",
        "domain": "Crop & Fertilizer Requirement Matching"
    },
    {
        "id": "fertilizer_prediction",
        "handle": "irakozekelly/fertilizer-prediction",
        "folder": "fertilizer_prediction",
        "domain": "Soil & Crop Fertilizer Prediction"
    },
    {
        "id": "crop_yield_recommendation",
        "handle": "vedikasd/crop-data-for-yield-and-recommendation-analysis",
        "folder": "crop_yield_recommendation",
        "domain": "Agronomic Crop Yield & Recommendation"
    },
    {
        "id": "crop_medicine_recommendation",
        "handle": "vishvavardhanbhasham/crop-recommendation-with-medicine",
        "folder": "crop_medicine_recommendation",
        "domain": "Crop Disease Protection & Medicine Guidance"
    },
    {
        "id": "soil_type",
        "handle": "aniketkumaraugustya/soil-type-dataset",
        "folder": "soil_type",
        "domain": "Soil Classification & Structural Types"
    },
    {
        "id": "crop_dataset",
        "handle": "sashankgarg23/crop-dataset",
        "folder": "crop_dataset",
        "domain": "General Agricultural & Crop Characteristics"
    },
    {
        "id": "crop_npk",
        "handle": "javakhan/crops-npk-data-set",
        "folder": "crop_npk",
        "domain": "Soil NPK Nutrient Ratios for Crops"
    },
    {
        "id": "fertilizer",
        "handle": "sanketgondaliya/fertilizer",
        "folder": "fertilizer",
        "domain": "Fertilizer Chemical Composition & Dosage"
    },
    {
        "id": "nutrient_loss",
        "handle": "ziya07/agricultural-nutrient-loss-dataset",
        "folder": "nutrient_loss",
        "domain": "Agricultural Runoff & Soil Nutrient Loss"
    }
]

def sanitize_val(val):
    if pd.isna(val):
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return float(val)
    return str(val)

def read_file_safe(file_path):
    encodings = ['utf-8', 'latin1', 'cp1252']
    ext = os.path.splitext(file_path)[1].lower()
    
    for enc in encodings:
        try:
            if ext == '.csv':
                df = pd.read_csv(file_path, encoding=enc)
                return df
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
                return df
            elif ext == '.tsv':
                df = pd.read_csv(file_path, sep='\t', encoding=enc)
                return df
            elif ext == '.json':
                df = pd.read_json(file_path)
                return df
        except Exception:
            continue
    return None

def inspect_dataset(config):
    dataset_dir = os.path.join(CROPS_DIR, config["folder"])
    result = {
        "dataset_id": config["id"],
        "handle": config["handle"],
        "domain": config["domain"],
        "folder": config["folder"],
        "status": "NOT_FOUND",
        "total_files": 0,
        "total_rows": 0,
        "files": []
    }
    
    if not os.path.exists(dataset_dir):
        return result

    all_files = glob.glob(os.path.join(dataset_dir, "**", "*.*"), recursive=True)
    valid_data_files = [f for f in all_files if os.path.splitext(f)[1].lower() in ['.csv', '.xlsx', '.xls', '.tsv', '.json']]
    
    result["total_files"] = len(valid_data_files)
    if not valid_data_files:
        result["status"] = "NO_DATA_FILES"
        return result

    result["status"] = "INSPECTED"
    grand_total_rows = 0

    for file_path in valid_data_files:
        rel_path = os.path.relpath(file_path, CROPS_DIR)
        file_size = os.path.getsize(file_path)
        df = read_file_safe(file_path)

        file_meta = {
            "file_name": os.path.basename(file_path),
            "relative_path": rel_path,
            "file_size_bytes": file_size,
            "status": "SUCCESS" if df is not None else "READ_ERROR",
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "missing_cells": 0,
            "duplicate_rows": 0,
            "sample_rows": []
        }

        if df is not None:
            file_meta["row_count"] = len(df)
            file_meta["column_count"] = len(df.columns)
            grand_total_rows += len(df)
            
            # duplicates
            try:
                file_meta["duplicate_rows"] = int(df.duplicated().sum())
            except Exception:
                file_meta["duplicate_rows"] = 0
                
            # total missing
            file_meta["missing_cells"] = int(df.isna().sum().sum())
            
            # columns breakdown
            cols_info = []
            for col in df.columns:
                col_data = df[col]
                dtype_str = str(col_data.dtype)
                null_cnt = int(col_data.isna().sum())
                
                col_meta = {
                    "name": str(col),
                    "dtype": dtype_str,
                    "null_count": null_cnt,
                    "null_percentage": round((null_cnt / len(df)) * 100, 2) if len(df) > 0 else 0,
                    "unique_count": int(col_data.nunique(dropna=True))
                }
                
                if pd.api.types.is_numeric_dtype(col_data):
                    clean_num = col_data.dropna()
                    if not clean_num.empty:
                        col_meta["stats"] = {
                            "min": sanitize_val(clean_num.min()),
                            "max": sanitize_val(clean_num.max()),
                            "mean": sanitize_val(clean_num.mean()),
                            "std": sanitize_val(clean_num.std()) if len(clean_num) > 1 else 0
                        }
                else:
                    top_vals = col_data.dropna().value_counts().head(5).to_dict()
                    col_meta["top_categories"] = {str(k): int(v) for k, v in top_vals.items()}
                
                cols_info.append(col_meta)
            
            file_meta["columns"] = cols_info
            
            # Top 5 sample rows
            samples = df.head(5).to_dict(orient="records")
            sanitized_samples = []
            for row in samples:
                sanitized_samples.append({str(k): sanitize_val(v) for k, v in row.items()})
            file_meta["sample_rows"] = sanitized_samples
            
        result["files"].append(file_meta)

    result["total_rows"] = grand_total_rows
    return result

def main():
    print("=== NABARD Agricultural Datasets Inspection & Cataloguing ===")
    
    os.makedirs(os.path.dirname(OUTPUT_CATALOG_JSON), exist_ok=True)
    catalog = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "total_datasets": len(DATASETS_CONFIG),
        "datasets": []
    }
    
    total_ingested_rows = 0
    total_data_files = 0
    
    for cfg in DATASETS_CONFIG:
        print(f"Inspecting dataset: {cfg['id']} ({cfg['handle']})...")
        res = inspect_dataset(cfg)
        catalog["datasets"].append(res)
        total_ingested_rows += res["total_rows"]
        total_data_files += res["total_files"]
        print(f"  -> Status: {res['status']}, Files: {res['total_files']}, Rows: {res['total_rows']}")
        
    catalog["summary"] = {
        "total_datasets": len(DATASETS_CONFIG),
        "total_data_files": total_data_files,
        "total_ingested_rows": total_ingested_rows,
        "status": "COMPLETE"
    }

    # Save catalog.json
    with open(OUTPUT_CATALOG_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    print(f"\nSaved catalog JSON: {OUTPUT_CATALOG_JSON}")
    
    # Save ingestion_report.json
    ingestion_report = {
        "ingestion_timestamp": pd.Timestamp.now().isoformat(),
        "datasets_processed": len(catalog["datasets"]),
        "total_files": total_data_files,
        "total_rows": total_ingested_rows,
        "status": "SUCCESS",
        "dataset_summaries": [
            {
                "id": ds["dataset_id"],
                "domain": ds["domain"],
                "files": ds["total_files"],
                "rows": ds["total_rows"],
                "status": ds["status"]
            } for ds in catalog["datasets"]
        ]
    }
    with open(OUTPUT_INGESTION_REPORT, "w", encoding="utf-8") as f:
        json.dump(ingestion_report, f, indent=2)
    print(f"Saved ingestion report: {OUTPUT_INGESTION_REPORT}")

    # Save DATA_CATALOG.md
    md_lines = [
        "# NABARD Agricultural Data Catalog",
        "",
        "## Summary Overview",
        f"- **Catalog Generated At**: `{catalog['generated_at']}`",
        f"- **Total Datasets Catalogued**: `{catalog['summary']['total_datasets']}`",
        f"- **Total Ingested Data Files**: `{catalog['summary']['total_data_files']}`",
        f"- **Total Records / Rows Ingested**: `{catalog['summary']['total_ingested_rows']:,}`",
        "",
        "---",
        "",
        "## Detailed Dataset Catalog",
        ""
    ]
    
    for ds in catalog["datasets"]:
        md_lines.append(f"### {ds['dataset_id']} — {ds['domain']}")
        md_lines.append(f"- **Kaggle Handle**: `{ds['handle']}`")
        md_lines.append(f"- **Status**: `{ds['status']}`")
        md_lines.append(f"- **Total Rows**: `{ds['total_rows']:,}`")
        md_lines.append(f"- **Total Files**: `{ds['total_files']}`")
        md_lines.append("")
        
        for f in ds["files"]:
            md_lines.append(f"#### File: `{f['relative_path']}`")
            md_lines.append(f"- **Size**: `{f['file_size_bytes']:,} bytes` | **Rows**: `{f['row_count']:,}` | **Columns**: `{f['column_count']}`")
            md_lines.append(f"- **Missing Cells**: `{f['missing_cells']}` | **Duplicates**: `{f['duplicate_rows']}`")
            md_lines.append("")
            md_lines.append("| Column Name | Data Type | Null Count | Null % | Unique Values | Details / Stats |")
            md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            
            for col in f["columns"]:
                details = ""
                if "stats" in col:
                    st = col["stats"]
                    details = f"Min: {st['min']}, Max: {st['max']}, Mean: {st['mean']:.2f}"
                elif "top_categories" in col:
                    top_str = ", ".join([f"{k} ({v})" for k, v in list(col["top_categories"].items())[:3]])
                    details = f"Top: {top_str}"
                md_lines.append(f"| `{col['name']}` | `{col['dtype']}` | {col['null_count']} | {col['null_percentage']}% | {col['unique_count']} | {details} |")
            md_lines.append("")
            
    with open(OUTPUT_CATALOG_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Saved DATA_CATALOG.md: {OUTPUT_CATALOG_MD}")

if __name__ == "__main__":
    main()
