import os
import csv
import zipfile

# Create a directory to hold the CSV files
os.makedirs("csvfiles", exist_ok=True)

# Generate 1000 small CSV files
for i in range(1000):
    filename = f"csvfiles/file_{i+1}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        # Write a simple header and one line of data
        writer.writerow(["col1", "col2"])
        writer.writerow([f"data{i+1}", f"data{i+1}"])

# Create a zip file containing all the generated CSV files
with zipfile.ZipFile('csv_files.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for i in range(500):
        filename = f"csvfiles/file_{i+1}.csv"
        z.write(filename, arcname=f"file_{i+1}.csv")

print("csv_files.zip created successfully!")
