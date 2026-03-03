import os
import csv
import logging
from flask import Flask, request, jsonify
from google.cloud import storage
from google.cloud import bigquery

# Configure logging (Cloud Run reads stdout/stderr)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Initialize clients once (faster cold start)
storage_client = storage.Client()
bq_client = bigquery.Client()


@app.route("/", methods=["GET"])
def health():
    return "Service is running", 200


@app.route("/", methods=["POST"])
def process_event():
    """
    Handles Eventarc CloudEvent for GCS object finalized.
    """
    try:
        envelope = request.get_json()

        if not envelope:
            logging.error("No event received")
            return "Bad Request", 400

        # Eventarc CloudEvent structure
        data = envelope.get("data", {})
        bucket_name = data.get("bucket")
        file_name = data.get("name")

        if not bucket_name or not file_name:
            logging.error("Invalid event payload")
            return "Bad Request", 400

        if not file_name.startswith("input/"):
            logging.info("File not in input/ folder. Skipping.")
            return "Ignored", 200

        logging.info(f"Processing file {file_name} from bucket {bucket_name}")

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)

        sql = blob.download_as_text()

        query_job = bq_client.query(sql)

        chunk_size = 60000
        row_iterator = query_job.result(page_size=chunk_size)

        file_index = 0
        rows_buffer = []

        for row in row_iterator:
            rows_buffer.append(row)

            if len(rows_buffer) >= chunk_size:
                write_chunk(bucket, rows_buffer, row_iterator.schema, file_index)
                rows_buffer = []
                file_index += 1

        if rows_buffer:
            write_chunk(bucket, rows_buffer, row_iterator.schema, file_index)

        logging.info("Processing completed successfully")
        return "Success", 200

    except Exception as e:
        logging.exception("Processing failed")
        return jsonify({"error": str(e)}), 500


def write_chunk(bucket, rows, schema, index):
    output_file = f"output/result_{index}.csv"
    tmp_file = f"/tmp/result_{index}.csv"

    with open(tmp_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([field.name for field in schema])
        for row in rows:
            writer.writerow(list(row.values()))

    bucket.blob(output_file).upload_from_filename(tmp_file)

    logging.info(f"Uploaded {output_file}")