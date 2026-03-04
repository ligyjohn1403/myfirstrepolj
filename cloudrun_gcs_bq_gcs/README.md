# GCS → Eventarc → Cloud Run → BigQuery Pipeline

## 📌 Overview

This project implements a serverless data pipeline using:

- Google Cloud Storage (GCS)
- Eventarc
- Cloud Run
- BigQuery

When a SQL file is uploaded to the `input/` folder in GCS, the system:

1. Triggers Eventarc
2. Invokes Cloud Run
3. Executes SQL in BigQuery
4. Writes results to the `output/` folder in GCS

---

## 🏗 Architecture

GCS (input folder)  
↓  
Eventarc Trigger  
↓  
Cloud Run Service  
↓  
BigQuery Query Execution 

## Pre-requisite 
1)Enabling all API
eventarc-gcloud services enable eventarc.googleapis.com
gcloud services enable \
  eventarc.googleapis.com \
  pubsub.googleapis.com \
  storage.googleapis.com

2)Setup service accounts
  Grant access default service account with 967826726064-compute@developer.gserviceaccount.com
   for cloud build 
  cloud run deployment SA-cloudrun-bq-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com
  eventarc SA-eventarc-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com 
  Access BQ access SA-cloudrun-bq-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com
                 
3)creation of GCS buckets
4)creation of github trigger
5)Creation of BQ dataset and tables
6)Deployment of cloud run 
7)Creation of event arc

**##Deployments steps**
**1.Creation of artifact repository regsitry  repo and access :**

gcloud artifacts repositories create cloud-run-source-deploy \
  --repository-format=docker \
  --location=us-central1 \
  --description="Repo for Cloud Run images"

 gcloud artifacts repositories add-iam-policy-binding cloud-run-source-deploy \
  --location=us-central1 \
  --member="serviceAccount:967826726064-compute@developer.gserviceaccount.com	" \
  --role="roles/artifactregistry.reader"

gcloud artifacts repositories add-iam-policy-binding cloud-run-source-deploy \
  --location=us-central1 \
  --member="serviceAccount:967826726064-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"

gcloud artifacts repositories list --location=us-central1

**2.Git Push the code from GIT HUB  and also create the GCS buckets **

**3.Creating GITHUB trigger in cloudbuild**
**3.1.Create a trigger from UI **
name :github-trigger
region:us-central1 (Iowa)
Event:Push to a branch
Source:Cloud Build repositories
Repo gen:1st gen
Repo:repo path
Branch:^main$
Config:
  Type:Cloud Build configuration file (yaml or json)
  Location:Repository
  file loacation :cloudrun_gcs_bq_gcs/cloudbuild.yaml

**3.2.Grant access to default service account** - <projectnumber>-compute@developer.gserviceaccount.com 
Artifact Registry Reader
Artifact Registry Writer
Cloud Build Service Account
Cloud Run Admin
Logs Writer
Storage Admin



**4.Deploying the cloud run:**
  gcloud run deploy cloudrun-bq-service \
  --image us-central1-docker.pkg.dev/project-9d5f3da8-f37e-45f7-b07/cloud-run-source-deploy/cloudrun-bq-service:**4563798** \
  --region us-central1 \
  --service-account cloudrun-bq-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com \
  --memory 1Gi \
  --cpu 1 \
  --timeout 900 \
  --concurrency 5 \
  --no-allow-unauthenticated
 replace image last version details with latest cloud buildimage number from the cloud build logs

 gcloud run services add-iam-policy-binding cloudrun-bq-service \
  --member="serviceAccount:cloudrun-bq-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-central1

  gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/run.admin"

 gcloud iam service-accounts add-iam-policy-binding \
  cloudrun-bq-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
Incase of error check in cloud run logs to troubleshoot.

**5.Eventarch creation:**
Role behind scene:
  GCS
  ↓ (publish event)
Pub/Sub topic (managed by Eventarc)
  ↓
Eventarc
  ↓
Cloud Run

**5.1)Create service account :**
gcloud iam service-accounts create eventarc-sa \
  --display-name="Eventarc Service Account"

gcloud run services add-iam-policy-binding cloudrun-bq-service \
  --region us-central1 \
  --member="serviceAccount:eventarc-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
  
gcloud projects add-iam-policy-binding project-9d5f3da8-f37e-45f7-b07 \
  --member="serviceAccount:eventarc-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com" \
  --role="roles/eventarc.eventReceiver"
  
gcloud projects add-iam-policy-binding project-9d5f3da8-f37e-45f7-b07 \
  --member="serviceAccount:eventarc-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"
  
  gcloud projects add-iam-policy-binding project-9d5f3da8-f37e-45f7-b07 \
  --member="serviceAccount:service-967826726064@gs-project-accounts.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
  
  gcloud projects add-iam-policy-binding project-9d5f3da8-f37e-45f7-b07 \
  --member="serviceAccount:eventarc-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
  
gcloud projects add-iam-policy-binding project-9d5f3da8-f37e-45f7-b07 \
  --member="serviceAccount:eventarc-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com" \
  --role="roles/eventarc.eventReceiver"

**5.2)create event arc trigger for gcs file**
gcloud eventarc triggers create gcs-trigger \
  --location=us \
  --destination-run-service=cloudrun-bq-service \
  --destination-run-region=us-central1 \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=lj_cloudrun_poc" \
  --service-account=eventarc-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com
  
**5.3)check if eventarc created :**
gcloud eventarc triggers list --location=us

**6.Creation of BQ dataset & tables:**
1)Created the dataset in UI
2)Creation of table and loading from csv file in gcs bucket 
LOAD DATA INTO `project-9d5f3da8-f37e-45f7-b07.sales_db.sales_raw`
(
  order_id INT64,
  segment STRING,
  country STRING,
  product STRING,
  discount_band STRING,
  units_sold INT64,
  manufacturing_price NUMERIC,
  sale_price NUMERIC,
  gross_sales NUMERIC,
  discounts NUMERIC,
  sales NUMERIC,
  cogs NUMERIC,
  profit NUMERIC,
  date STRING,
  month_number INT64,
  month_name STRING,
  year INT64
)
FROM FILES (
  format = 'CSV',
  uris = ['gs://lj_data_layer/sales.csv'],
  skip_leading_rows = 1
);
CREATE OR REPLACE TABLE `project-9d5f3da8-f37e-45f7-b07.sales_db.sales_tbl` AS
SELECT
  order_id,
  segment,
  country,
  product,
  discount_band,
  units_sold,
  manufacturing_price,
  sale_price,
  gross_sales,
  discounts,
  sales,
  cogs,
  profit,
  PARSE_DATE('%d-%m-%Y', date) AS sale_date,
  month_number,
  month_name,
  year
FROM `project-9d5f3da8-f37e-45f7-b07.sales_db.sales_raw`;
3) Grant Access permissions to cloudrun service account to access the table data
gcloud projects add-iam-policy-binding project-9d5f3da8-f37e-45f7-b07 \
  --member="serviceAccount:cloudrun-bq-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"
  gcloud projects add-iam-policy-binding project-9d5f3da8-f37e-45f7-b07 \
  --member="serviceAccount:cloudrun-bq-sa@project-9d5f3da8-f37e-45f7-b07.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"


## Testing
 1. Place a query file -gsutil cp query.sql gs://lj_cloudrun_poc/input/query.sql
 2. Files are created in output folder in GCS  gs://lj_cloudrun_poc/output/
---

## 📂 Repository Structure

