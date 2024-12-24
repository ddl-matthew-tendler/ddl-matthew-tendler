from google.cloud import storage
import pandas as pd
import streamlit as st

# Function to download file from GCS
def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    try:
        # Initialize a client
        storage_client = storage.Client()
        # Retrieve bucket
        bucket = storage_client.bucket(bucket_name)
        # Retrieve blob (file)
        blob = bucket.blob(source_blob_name)
        # Download the file locally
        blob.download_to_filename(destination_file_name)
        st.success(f"Downloaded {source_blob_name} to {destination_file_name}")
    except Exception as e:
        st.error(f"Error downloading file: {e}")

# Streamlit App
st.title("Clinical Data Viewer")

# Google Cloud Storage bucket details
bucket_name = "csv-fake-clinical-data"  # Replace with your bucket name
folder_name = "clinical_trial_data/"  # Folder within the bucket

# List of files
clinical_files = [
    "clinical_trial_1.csv",
    "clinical_trial_2.csv",
    "clinical_trial_3.csv",
    "clinical_trial_4.csv",
    "clinical_trial_5.csv",
    "clinical_trial_6.csv",
    "clinical_trial_7.csv",
    "clinical_trial_8.csv",
    "clinical_trial_9.csv",
    "clinical_trial_10.csv"
]

# Dropdown to select a file
selected_file = st.selectbox("Select a clinical trial file to visualize:", clinical_files)

if selected_file:
    source_blob_name = folder_name + selected_file  # Full path to the file in the bucket
    destination_file_name = selected_file  # Local file name to save

    # Button to download the file
    if st.button("Download and View Data"):
        # Download the file
        download_from_gcs(bucket_name, source_blob_name, destination_file_name)

        # Load the CSV into a Pandas DataFrame
        try:
            data = pd.read_csv(destination_file_name)
            st.write(f"Displaying the first 5 rows of `{selected_file}`:")
            st.dataframe(data.head())  # Display the first 5 rows in the Streamlit app
        except Exception as e:
            st.error(f"Error loading the file: {e}")
