import os
import csv
import io
from flask import Flask, request
from google.cloud import storage
from google.cloud import bigquery

app = Flask(__name__)

PROJECT_ID = os.getenv("PROJECT_ID")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")

storage_client = storage.Client()
bq_client = bigquery.Client()

CHUNK_SIZE = 60000


def validate_select_query(query):
    query_clean = query.strip().lower()

    if not query_clean.startswith("select"):
        return False

    forbidden = ["insert", "update", "delete", "create",
                 "drop", "alter", "merge", "truncate"]

    if any(word in query_clean for word in forbidden):
        return False

    return True


@app.route("/", methods=["POST"])
def handle_gcs_event():

    event = request.get_json()

    if not event:
        return "No event received", 400

    bucket_name = event["bucket"]
    file_name = event["name"]

    if not file_name.endswith(".sql"):
        return "Not a SQL file", 200

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    sql_query = blob.download_as_text()

    if not validate_select_query(sql_query):
        return "Only SELECT queries allowed", 400

    query_job = bq_client.query(sql_query)
    results = query_job.result(page_size=CHUNK_SIZE)

    output_bucket = storage_client.bucket(OUTPUT_BUCKET)

    file_index = 1
    rows_buffer = []
    headers_written = False
    column_names = [field.name for field in results.schema]

    for row in results:
        rows_buffer.append(list(row.values()))

        if len(rows_buffer) >= CHUNK_SIZE:
            upload_chunk(output_bucket, file_name, file_index,
                         column_names, rows_buffer)
            file_index += 1
            rows_buffer = []

    # upload remaining rows
    if rows_buffer:
        upload_chunk(output_bucket, file_name, file_index,
                     column_names, rows_buffer)

    return "Query executed and exported in chunks", 200


def upload_chunk(bucket, base_filename, index, headers, rows):

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)

    writer.writerow(headers)
    writer.writerows(rows)

    blob = bucket.blob(
        f"output/{base_filename}_part_{index}.csv"
    )

    blob.upload_from_string(
        csv_buffer.getvalue(),
        content_type="text/csv"
    )
