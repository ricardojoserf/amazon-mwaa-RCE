from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def say_hello():
    print("Hello World from Airflow!")

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    dag_id='test_3',
    default_args=default_args,
    description='Un DAG cualquiera',
    schedule_interval='@daily',
    start_date=datetime(2025, 5, 7),
    catchup=False,
    tags=['ejemplo'],
    doc_md="""
    # Test 1
    {{ 3*3 }}
    """
) as dag:
    tarea_1 = PythonOperator(
        task_id='di_hola',
        python_callable=say_hello,
    )