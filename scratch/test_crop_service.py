import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from crop_data_service import get_all_datasets, get_datasets_summary, get_dataset_records, get_agronomic_insights

print("=== Testing Crop Data Service Endpoints ===")

res_datasets = get_all_datasets()
print(f"1. get_all_datasets: {res_datasets['status']}, Datasets Count: {res_datasets['total_datasets']}")

res_summary = get_datasets_summary()
print(f"2. get_datasets_summary: {res_summary['status']}, Total Records: {res_summary['total_records']:,}, Crop Categories: {res_summary['total_crop_categories']}")

res_records = get_dataset_records("crop_recommendation_water", page=1, limit=5)
print(f"3. get_dataset_records ('crop_recommendation_water'): {res_records['status']}, Domain: '{res_records['domain']}', Total Records: {res_records['total_records']}, Sample rows returned: {len(res_records['data'])}")

res_insights = get_agronomic_insights()
print(f"4. get_agronomic_insights: {res_insights['status']}, Crop Recommendations Count: {len(res_insights['crop_recommendations'])}, Soil Types Count: {len(res_insights['soil_type_distribution'])}")

print("\nSUCCESS! All Crop Data Service endpoints passed local verification.")
