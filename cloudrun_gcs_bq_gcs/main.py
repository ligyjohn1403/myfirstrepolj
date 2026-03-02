import os
import csv
import io
from flask import Flask, request
from google.cloud import storage
from google.cloud import bigquery

app = Flask(__name__)

# Environment Variables
PROJECT_ID = os.getenv("PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")
INPUT_PREFIX = os.getenv("INPUT_PREFIX", "input/")
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "output/")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 60000))

storage_client = storage.Client(project=PROJECT_ID)
bq_client = bigquery.Client(project=PROJECT_ID)


# ------------------------------
# Validate SELECT-only query
# ------------------------------
def validate_select_query(query: str) -> bool:
    query_clean = query.strip().lower()

    if not query_clean.startswith("select"):
        return False

    forbidden = [
        "insert", "update", "delete",
        "create", "drop", "alter",
        "merge", "truncate"
    ]

    return not any(word in query_clean for word in forbidden)


# ------------------------------
# Upload chunk to GCS
# ------------------------------
def upload_chunk(bucket, base_filename, index, headers, rows):

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)

    writer.writerow(headers)
    writer.writerows(rows)

    blob = bucket.blob(
        f"{OUTPUT_PREFIX}{base_filename}_part_{index}.csv"
    )

    blob.upload_from_string(
        csv_buffer.getvalue(),
        content_type="text/csv"
    )


# ------------------------------
# Main Cloud Run entry point
# ------------------------------
@app.route("/", methods=["POST"])
def handle_gcs_event():

    event = request.get_json()

    if not event:
        return "No event received", 400

    bucket_name = event.get("bucket")
    file_name = event.get("name")

    if bucket_name != BUCKET_NAME:
        return "Wrong bucket", 200

    # Prevent infinite loop
    if not file_name.startswith(INPUT_PREFIX):
        return "Not an input file", 200

    if not file_name.endswith(".sql"):
        return "Not a SQL file", 200

    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)
    sql_query = blob.download_as_text()

    # Validate query
    if not validate_select_query(sql_query):
        return "Only SELECT queries allowed", 400

    # Execute query
    query_job = bq_client.query(sql_query)
    results = query_job.result(page_size=CHUNK_SIZE)

    column_names = [field.name for field in results.schema]

    base_filename = file_name.replace(INPUT_PREFIX, "").replace(".sql", "")

    file_index = 1
    rows_buffer = []

    for row in results:
        rows_buffer.append(list(row.values()))

        if len(rows_buffer) >= CHUNK_SIZE:
            upload_chunk(bucket, base_filename, file_index,
                         column_names, rows_buffer)
            file_index += 1
            rows_buffer = []

    # Upload remaining rows
    if rows_buffer:
        upload_chunk(bucket, base_filename, file_index,
                     column_names, rows_buffer)

    return "Query executed successfully", 200
