from datetime import datetime, timedelta
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests

default_args = {
    'owner': 'yudhix-ops',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=10),
}

def purge_expired_comment_texts():
    pulse_url = "http://yudhix-pulse:8085/api/v1/comments/retention/enforce"
    logging.info("Enforcing GDPR/DPDP comment retention policy: %s", pulse_url)
    try:
        response = requests.post(pulse_url, timeout=120)
        logging.info("Retention enforcement response: %s", response.status_code)
    except Exception as e:
        logging.warning("Pulse service retention call logged: %s", str(e))

with DAG(
    'yudhix_retention_enforcer',
    default_args=default_args,
    description='Nightly automated purge of expired raw comment text adhering to regional privacy laws',
    schedule_interval='0 3 * * *', # Daily at 03:00 UTC
    catchup=False,
) as dag:

    retention_task = PythonOperator(
        task_id='enforce_retention_task',
        python_callable=purge_expired_comment_texts,
    )
