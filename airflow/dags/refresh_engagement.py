from datetime import datetime, timedelta
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'yudhix-ops',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def refresh_metrics():
    logging.info("Refreshing like and reply velocity snapshots for active comments across platforms.")

with DAG(
    'yudhix_refresh_engagement',
    default_args=default_args,
    description='Refreshes likes/reply counts for recent comments to compute velocity and recalculate priority',
    schedule_interval='*/30 * * * *',
    catchup=False,
) as dag:

    refresh_task = PythonOperator(
        task_id='refresh_engagement_task',
        python_callable=refresh_metrics,
    )
