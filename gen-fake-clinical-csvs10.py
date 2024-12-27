import os
import csv
import random
import string
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient

# Retrieve the Azure Storage key from an environment variable
azure_storage_key = os.getenv("AZURE_STORAGE_KEY")
if not azure_storage_key:
    raise ValueError("Azure Storage key not found. Please set the AZURE_STORAGE_KEY environment variable.")

# Azure Storage account details
storage_account_name = "tenderstorage1_1735252879821"
container_name = "clinical-trials"

# Initialize the BlobServiceClient
blob_service_client = BlobServiceClient(
    f"https://{storage_account_name}.blob.core.windows.net", 
    credential=azure_storage_key
)

# Ensure the container exists
try:
    blob_service_client.create_container(container_name)
except Exception as e:
    if "ContainerAlreadyExists" not in str(e):
        raise e

# Function to generate random date within a range
def random_date(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

# Function to generate a random Subject ID
def generate_subject_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Function to generate and upload a CSV file to Azure
def generate_and_upload_csv(file_number):
    blob_name = f"clinical_trial_{file_number}.csv"

    # Generate CSV content in memory
    output = []
    # Randomize the number of rows to vary file size (between 40,000 and 120,000 rows)
    num_rows = random.randint(40000, 120000)
    
    # Define start and end dates for the trial period
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 1, 1)

    # Write the header
    output.append([
        "Subject ID", "Age", "Gender", "Visit Date",
        "Heart Rate (bpm)", "Systolic BP (mmHg)", "Diastolic BP (mmHg)", "Body Temp (°C)",
        "Hemoglobin (g/dL)", "WBC Count (K/uL)", "Adverse Event"
    ])
    
    # Write random clinical trial data
    for _ in range(num_rows):
        subject_id = generate_subject_id()
        age = random.randint(18, 85)
        gender = random.choice(["Male", "Female"])
        visit_date = random_date(start_date, end_date).strftime("%Y-%m-%d")
        heart_rate = random.randint(60, 100)
        systolic_bp = random.randint(90, 140)
        diastolic_bp = random.randint(60, 90)
        body_temp = round(random.uniform(36.0, 38.5), 1)
        hemoglobin = round(random.uniform(12.0, 18.0), 1)
        wbc_count = round(random.uniform(4.0, 11.0), 1)
        adverse_event = random.choice(["Yes", "No"])
        
        output.append([
            subject_id, age, gender, visit_date,
            heart_rate, systolic_bp, diastolic_bp, body_temp,
            hemoglobin, wbc_count, adverse_event
        ])

    # Convert the output to CSV format as a string
    csv_content = '\n'.join([','.join(map(str, row)) for row in output])

    # Upload CSV to Azure Blob Storage
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.upload_blob(csv_content, overwrite=True)

    print(f"Generated and uploaded {blob_name} to Azure Storage")

# Generate 10 unique CSV files and upload them
for i in range(10):
    generate_and_upload_csv(i + 1)

print("All CSV files have been generated and uploaded successfully!")