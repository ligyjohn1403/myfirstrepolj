import os
import csv
import logging
from flask import Flask, request
from google.cloud import storage, bigquery

app = Flask(__name__)

@app.route("/", methods=["POST"])
def process_event():
    envelope = request.get_json()

    if not envelope:
        logging.error("No event received")
        return ("Bad Request", 400)

    if "data" not in envelope:
        logging.error("Invalid event payload")
        return ("Bad Request", 400)

    event = envelope["data"]

    bucket_name = event.get("bucket")
    file_name = event.get("name")

    if not bucket_name or not file_name:
        logging.error("Missing bucket or file name")
        return ("Bad Request", 400)

    # Filter only input folder
    if not file_name.startswith("input/"):
        logging.info(f"Ignoring file: {file_name}")
        return ("Ignored", 204)

    logging.info(f"Processing file {file_name} from bucket {bucket_name}")

    storage_client = storage.Client()
    bq_client = bigquery.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    sql = blob.download_as_text()

    job = bq_client.query(sql)
    results = job.result()

    rows = list(results)
    chunk_size = 60000

    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i+chunk_size]
        output_file = f"output/result_{i//chunk_size}.csv"
        out_blob = bucket.blob(output_file)

        tmp_file = f"/tmp/result_{i//chunk_size}.csv"

        with open(tmp_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([field.name for field in results.schema])
            for row in chunk:
                writer.writerow(list(row.values()))

        out_blob.upload_from_filename(tmp_file)

    logging.info("Processing complete")
    return ("Success", 200)
