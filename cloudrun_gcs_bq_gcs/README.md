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
↓  
GCS (output folder)

---

## 📂 Repository Structure
