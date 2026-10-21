from datetime import datetime, timedelta
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'yudhix-ops',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def evaluate_reply_outcomes():
    logging.info("Checking 24h, 72h, and 7d follow-up sentiment for posted brand replies.")

with DAG(
    'yudhix_reply_outcomes',
    default_args=default_args,
    description='Evaluates sentiment shifts at +24h, +72h, and +7d post-reply and updates Turnaround Rate KPI',
    schedule_interval='0 */2 * * *', # Every 2 hours
    catchup=False,
) as dag:

    outcome_task = PythonOperator(
        task_id='evaluate_outcomes_task',
        python_callable=evaluate_reply_outcomes,
    )
