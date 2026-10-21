from datetime import datetime, timedelta
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests

default_args = {
    'owner': 'yudhix-ops',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': True,
    'email': ['ops@yudhix.io'],
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

def poll_all_sources():
    gateway_url = "http://yudhix-gateway:8080/api/v1/connectors/poll"
    logging.info("Triggering connector source poll via gateway: %s", gateway_url)
    # In production, pass internal system auth token
    response = requests.post(gateway_url, headers={"X-Internal-Call": "true"}, timeout=60)
    logging.info("Poll response status: %s", response.status_code)

with DAG(
    'yudhix_ingest_sources',
    default_args=default_args,
    description='Polls registered social media sources every 5 minutes for incremental comments',
    schedule_interval='*/5 * * * *',
    catchup=False,
    max_active_runs=1,
) as dag:

    poll_task = PythonOperator(
        task_id='poll_sources_task',
        python_callable=poll_all_sources,
    )
