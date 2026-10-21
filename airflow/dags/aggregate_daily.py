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

def aggregate_sentiment():
    logging.info("Aggregating daily product sentiments into daily_product_sentiment table.")

with DAG(
    'yudhix_aggregate_daily',
    default_args=default_args,
    description='Rolls up daily sentiment distributions by product, platform, and country',
    schedule_interval='0 1 * * *', # Daily at 01:00 UTC
    catchup=False,
) as dag:

    agg_task = PythonOperator(
        task_id='aggregate_sentiment_task',
        python_callable=aggregate_sentiment,
    )
