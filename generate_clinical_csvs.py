import os
import csv
import random
import string
from datetime import datetime, timedelta

# Create a directory to hold the CSV files
os.makedirs("csvfiles", exist_ok=True)

# Function to generate random date within a range
def random_date(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

# Function to generate a random Subject ID
def generate_subject_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Generate 500 unique CSV files
for i in range(500):
    filename = f"csvfiles/clinical_trial_{i+1}.csv"
    
    # Randomize the number of rows to vary file size (between 40,000 and 120,000 rows)
    num_rows = random.randint(40000, 120000)
    
    # Define start and end dates for the trial period
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 1, 1)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write the header
        writer.writerow([
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
            
            writer.writerow([
                subject_id, age, gender, visit_date,
                heart_rate, systolic_bp, diastolic_bp, body_temp,
                hemoglobin, wbc_count, adverse_event
            ])
    
    print(f"Generated {filename}")

print("All CSV files have been generated successfully!")
