import os
from google.cloud import storage, bigquery
import csv

def process_file(event, context):
    bucket_name = event['bucket']
    file_name = event['name']

    if not file_name.startswith("input/"):
        return

    storage_client = storage.Client()
    bq_client = bigquery.Client()

    # Read SQL file
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    sql = blob.download_as_text()

    # Run query
    job = bq_client.query(sql)
    results = job.result()

    # Write results in chunks of 60K
    rows = list(results)
    chunk_size = 60000
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]
        output_file = f"output/result_{i//chunk_size}.csv"
        out_blob = bucket.blob(output_file)

        # Write CSV to temp file
        tmp_file = f"/tmp/result_{i//chunk_size}.csv"
        with open(tmp_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([field.name for field in results.schema])
            for row in chunk:
                writer.writerow(list(row.values()))

        out_blob.upload_from_filename(tmp_file)
