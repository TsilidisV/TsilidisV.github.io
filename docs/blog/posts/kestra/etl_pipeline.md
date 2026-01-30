---
date: 2026-01-22
categories:
  - Data Engineering
  - Orchestration
  - Tutorials
tags:
  - Kestra
  - ETL
  - Python
  - PostgreSQL
  - Docker
  - Data Normalization
title: "Constructing an ETL pipeline with Kestra"
description: "Construct a robust, containerized ETL pipeline using Kestra to orchestrate the ingestion of Greek road traffic data into PostgreSQL. The guide details extracting API data, normalizing JSON with Python/Pandas, and ensuring data integrity through staging tables and SQL merge strategies."
---
# {{ title }}
{{ description }}

<!-- more -->


# Building an ETL pipeline with Kestra

Extract, transform, load (ETL) is a three-phase computing process where data is extracted from an input source, transformed (including cleaning), and loaded into an output data container. The data can be collected from one or more sources and it can also be output to one or more destinations. 

In this article we will use Kestra to build an ETL framework for extracting data from https://data.gov.gr/datasets concerning the [road traffic for the Attica region](https://data.gov.gr/datasets/road_traffic_attica), transform it using Python and load it into an postegreSQL database.

## Preliminaries
We're going to use the following `docker-compose.yml` file for a dockerized version of Kestra and postegreSQL:

```yaml
volumes:
  traffic_postgres_data:
    driver: local
  kestra_postgres_data:
    driver: local
  kestra_data:
    driver: local

services:
  pgdatabase:
    image: postgres:18
    environment:
      POSTGRES_USER: root
      POSTGRES_PASSWORD: root
      POSTGRES_DB: traffic
    ports:
      - "5432:5432"
    volumes:
      - traffic_postgres_data:/var/lib/postgresql

  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@admin.com
      - PGADMIN_DEFAULT_PASSWORD=root
    ports:
      - "8085:80"

  kestra_postgres:
    image: postgres:18
    volumes:
      - kestra_postgres_data:/var/lib/postgresql
    environment:
      POSTGRES_DB: kestra
      POSTGRES_USER: kestra
      POSTGRES_PASSWORD: k3str4
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -d $${POSTGRES_DB} -U $${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 10

  kestra:
    image: kestra/kestra:v1.1
    pull_policy: always
    # Note that this setup with a root user is intended for development purpose.
    # Our base image runs without root, but the Docker Compose implementation needs root to access the Docker socket
    # To run Kestra in a rootless mode in production, see: https://kestra.io/docs/installation/podman-compose
    user: "root"
    command: server standalone
    volumes:
      - kestra_data:/app/storage
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp/kestra-wd:/tmp/kestra-wd
    environment:
      KESTRA_CONFIGURATION: |
        datasources:
          postgres:
            url: jdbc:postgresql://kestra_postgres:5432/kestra
            driverClassName: org.postgresql.Driver
            username: kestra
            password: k3str4
        kestra:
          server:
            basicAuth:
              username: "admin@kestra.io" # it must be a valid email address
              password: Admin1234
          repository:
            type: postgres
          storage:
            type: local
            local:
              basePath: "/app/storage"
          queue:
            type: postgres
          tasks:
            tmpDir:
              path: /tmp/kestra-wd/tmp
          url: http://localhost:8080/
    ports:
      - "8080:8080"
      - "8081:8081"
    depends_on:
      kestra_postgres:
        condition: service_started
```

Additionally, we'll use this Dockerized version of Python with `pandas` preinstalled:
```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir pandas
```
and build it by `docker build python-with-pandas:latest .`

## Dataset
As already mentioned, the dataset we're going to playing with concerns the road traffic in the Attica region. Here's the fields of the dataset:

| **Description** | **Field** | **Type** |
|---|---|---|
| Tracking Device Code | deviceid | text |
| Counted Cars | countedcars | numeric |
| Time and Date | appprocesstime | datetime |
| Road Name | road_name | text |
| Road Info | road_info | text |
| Average Car Speed | average_speed | numeric |

We can download the data by accessing this link:
```text 
https://data.gov.gr/api/v1/query/road_traffic_attica?date_from=<data_start>&date_to=<data_end>
```
where `<data_start>` and `<data_end>` are dates in `YYYY-MM-DD` format. The maximum allowed difference between `<data_start>` and `<data_end>` is 1 day.
Additionally, the start date of the dataset is 2020-11-05.

## Inputs

Let's begin writing our Kestra Flow. The idea is to input a date and have the ETL load the corresponding data to the database. Hence, we'll define our inputs to be of type `DATA` and considering that the start date of the dataset is 2020-11-05, we will add the property `after: "2021-11-05"`:

```yaml
id: my_first_etl
namespace: company.team

inputs:
  - id: date
    type: DATE
    after: "2021-11-05"
```

## Variables
In Kestra, variables are dynamic placeholders that allow us to inject values into your flows at runtime using the Pebble templating engine (e.g., `{{ inputs.my_variable }}`), rather than hardcoding static data.

We use them to make our workflows reusable and flexible, allowing a single flow to handle different inputs, adapt to various environments (like Dev vs. Prod), and dynamically pass data outputs from one task to another.

Let's define some useful variables that we'll use across our flow:

```yaml
variables:
  table: "road_traffic_attica"
  url: "https://data.gov.gr/api/v1/query/{{ vars.table }}?date_from={{ inputs.date }}&date_to={{ inputs.date }}"
  file_name: "{{ vars.table }}_{{ inputs.date }}.json"
```

____________ why them ? ____________________

## Tasks
### Label
As our first task, we'll use the `Labels` type to attach a label to the execution of our flow, based on the data the user specified:

``` yaml
tasks:
  - id: set_label
    type: io.kestra.plugin.core.execution.Labels
    labels:
      file_date: "{{ inputs.date }}"
```

We could do something similar with the `Log` type, but attaching a label to each execution makes finding the execution we are interested in easier.

### Data Extraction
Time for the "E" part of the ETL framework. Let's extract our data! To do that, we'll use Kestra's handy `Download` type and the variable `url` we defined earlier:

```yaml
- id: extract_data
  type: io.kestra.plugin.core.http.Download
  uri: "{{ render(vars.url) }}"
```

Later, we'll want to tο access the URL of the downloaded file in Kestra's internal storage. To do that we'll use `{{ outputs.extract_data.uri }}` as `uri` is one of the outputs of the `Download` type.

### Data Transformation
The file we downloaded with the aforementioned task will be in `json` format. We want it in `csv` format to be able to later load it into the database. Additionally, the field names of the dataset isn't uniform. Hence, we aim to make the following changes:
| **Description** | **Old Name** | **New Name** |
|---|---|---|
| Tracking Device Code | deviceid | device_id |
| Counted Cars | countedcars | counted_cars |
| Time and Date | appprocesstime | processing_time |
| Road Name | road_name | road_name |
| Road Info | road_info | road_info |
| Average Car Speed | average_speed | average_speed |

Furthermore, some database normalization is in order. Specifically the decomposition of the data into separate relations. Since the tracking device used to measure the data is stationary, this means that two rows with the same tracking device id will always have the same road name and road info. Hence, we can split the table into two:
```
[device_id, counted_cars, processing_time, road_name, road_info, average_speed] -> [device_id, counted_cars, processing_time, average_speed] + [device_id, road_name, road_info]
```
with `device_id` being the foreign key that links the two tables together.

This allows us to save valuable storage space.

Let's transform the data using Python!

```yaml
- id: transform_with_python
  type: io.kestra.plugin.scripts.python.Script
  containerImage: python-with-pandas:latest
  inputFiles:
    data.json: "{{ outputs.extract_data.uri }}"
  outputFiles:
    - "{{ vars.traffic_file_name }}"
    - "{{ vars.road_file_name }}"
  script: |
    import pandas as pd
    
    # Read the JSON file
    df = pd.read_json("data.json")
    
    # Rename the columns
    df = df.rename(columns={
      'deviceid': 'device_id',
      'countedcars': 'counted_cars',
      'appprocesstime': 'time',
      'road_name': 'road_name',
      'road_info': 'road_info',
      'average_speed': 'average_speed'
    })

    # Split the dataframe into two tables
    df_traffic = df.drop(columns=['road_name', 'road_info'])
    df_road = df.drop(columns=['counted_cars', 'time', 'average_speed'])

    # Remove duplicate rows resulting from different processing times
    # on the road info table
    df_road = df_road.drop_duplicates()

    # Save to CSV
    df_traffic.to_csv("{{ vars.traffic_file_name }}", index=False)
    df_road.to_csv("{{ vars.road_file_name }}", index=False)
```

Let's see some of the properties for this task:
- `containerImage`: The task runner container image. We used the `python-with-pandas` docker image we created earlier.
- `inputFiles`: The files from Kestra’s internal storage we want to send to the local filesystem. The syntax we used is `<file_name_for_the_local_system>: <kestra_storage_uri>`, i.e., we want to map the file located in `outputs.extract_data.uri` to `data.json` for the Python Docker image.
- `outputFiles`: The files from the local filesystem to send to Kestra’s internal storage. During the execution of a script multiple files could be outputted. This property accepts a list of the names of those outputs that we want to access in subsequent tasks. To access them later we use ``{{ outputs.transform_with_python.outputFiles[render(vars.traffic_file_name)] }}``

### Data Loading
Time for the final part of the ETL pipeline. Loading the data! Let's begin by initializing our traffic and info tables. We'll create two empty tables with just the relevant column names.

```yaml
tasks:
...

  - id: traffic_table_maker
    type: io.kestra.plugin.jdbc.postgresql.Query
    sql: |
      CREATE TABLE IF NOT EXISTS {{ vars.traffic_table }} (
        unique_row_id text,
        batch_id text,
        ingest_time timestamp,
        device_id	text,
        counted_cars	numeric,
        processing_time	timestamp,
        average_speed	numeric
      );

  - id: road_table_maker
    type: io.kestra.plugin.jdbc.postgresql.Query
    sql: |
      CREATE TABLE IF NOT EXISTS {{ vars.road_table }} (
        unique_row_id text,
        batch_id text,
        ingest_time timestamp,
        device_id	text,
        road_name	text,
        road_info	text
      );

pluginDefaults:
  - type: io.kestra.plugin.jdbc.postgresql
    values:
      url: jdbc:postgresql://pgdatabase:5432/traffic
      username: root
      password: root
```

Lots of info to unpack here. Let's begin with the type `io.kestra.plugin.jdbc.postgresql.Query`. This allows us to connect with a postegreSQL database and make a query. Which database you aks? More of that in a minute. So, we have two tasks that make a query. The `traffic_table_maker` task creates the table with the traffic information, hence only including the `device_id`, `counted_cars`, `processing_time`, and `average_speed` columns. The `road_table_maker` task creates the table with the road information, hence only including the `device_id`, `road_name`, and `road_info` columns. We also include a `unique_row_id` and `batch_id` column in both tables.

Now, on the unansweared question from earlier. How does `io.kestra.plugin.jdbc.postgresql.Query` know to which database to connect? If we look at its documentation we'll see that it has two required properties: `sql` and `url`. We already provided `sql` with our query, but what about `url`? The `url` wants us to give it the JDBC (Java Database Connectivity) URL that specifies the location of a database and the necessary parameters for connecting to it. Additionally, since our database has username and a password, we also have to use the properties `username` and `password` each time we make a `io.kestra.plugin.jdbc.postgresql`. That's boring and would result in a huge Flow with repeated statements. Here comes `pluginDefaults`! It allows us to overload some fields with default values so we don't have to specify them again and again.

To populate the fields `url`, `username` and `password`, we have to look at the `docker-compose.yml` file we constructed earlier and specifically the service responsible for the traffic database, that is `pgdatabase`. The JDBC string takes the following form:
```text
jdbc:<dialect>://<host>:<port>/<database>
```
meaning that for our case it should be `jdbc:postgresql://pgdatabase:5432/traffic`. Additionally, the `username` and `password` are both `root`.

Now, if we connect to the pgAdmin instance (as we saw [here](../docker/compose.md)), we'll see that two new tables were created!

#### Staging Table
Now we should be ready to add our data to the newly constructed tables. However, what would happen to the table if we added a bad batch, that is we loaded our table with data that were incomplete or corrupted (for example missing keys or required fields, bad CSV quoting, invalid JSON, etc.)? Then, our table would be contaminated with the bad batch and would need cleaning. A way to get rid of this problem is to use temporary table, called **staging table**, to load the data first into it, and then, if the data were loaded successfully, merge it to our clean data.

Hence, let's create a staging table for each of our tables:

```yaml
- id: staging_traffic_table_maker
  type: io.kestra.plugin.jdbc.postgresql.Query
  sql: |
    CREATE TABLE IF NOT EXISTS {{ vars.traffic_staging_table }} (
      unique_row_id text,
      batch_id text,
      ingest_time timestamp,
      device_id	text,
      counted_cars	numeric,
      processing_time	timestamp,
      average_speed	numeric
    );

- id: staging_road_table_maker
  type: io.kestra.plugin.jdbc.postgresql.Query
  sql: |
    CREATE TABLE IF NOT EXISTS {{ vars.road_staging_table }} (
      unique_row_id text,
      batch_id text,
      ingest_time timestamp,
      device_id	text,
      road_name	text,
      road_info	text
    );
```

#### Loading Data into Staging Tables
Now that we have a checkpoint in the face of staging tables, let's populate them with data:

```yaml
  - id: copy_in_to_traffic_staging_table
    type: io.kestra.plugin.jdbc.postgresql.CopyIn
    format: CSV
    from: "{{ outputs.transform_with_python.outputFiles[render(vars.traffic_file_name)] }}"
    table: "{{ vars.traffic_staging_table }}"
    header: true
    columns: [device_id, counted_cars, processing_time, average_speed]

  - id: copy_in_to_road_staging_table
    type: io.kestra.plugin.jdbc.postgresql.CopyIn
    format: CSV
    from: "{{ outputs.transform_with_python.outputFiles[render(vars.road_file_name)] }}"
    table: "{{ vars.road_staging_table }}"
    header: true
    columns: [device_id, road_name, road_info]
```

We used the `io.kestra.plugin.jdbc.postgresql.CopyIn` type which can be used to copy CSV, Text, or Binary data into a PostgreSQL table.
It has the mandatory property `from` which expects the URI of the source file. In our case the dataframe with the data is sitting at `outputs.transform_with_python.outputFiles[render(vars.traffic_file_name)]` for the traffic table and at `outputs.transform_with_python.outputFiles[render(vars.road_file_name)]` for the road table. The type's second required property is the `url` which is already being taken cared of by the `pluginDefaults`, just like the `password` and `username` properties. 

The `header` property specifies whether the file contains a header line with the names of each column in the file. Finally, `columns` is an optional list of columns to be copied. If no column list is specified, all columns of the table will be copied.

#### Processing the Staging Tables
##### `unique_row_id`
Remember that `unique_row_id` we added to the tables earlier? If we look over at pgAdmin we'll notice that it's still empty. Now it's the perfect time to populate it before we merge the staging tables with the main tables.

We'll use the `io.kestra.plugin.jdbc.postgresql.Queries` type once more:

{% raw %}
```yaml
- id: add_unique_id_to_traffic
  type: io.kestra.plugin.jdbc.postgresql.Queries
  sql: |
    UPDATE {{ vars.traffic_staging_table }}
    SET 
      unique_row_id = md5(
        COALESCE(CAST(device_id AS text), '') ||
        COALESCE(CAST(processing_time AS text), '') 
      );

- id: add_unique_id_to_road
  type: io.kestra.plugin.jdbc.postgresql.Queries
  sql: |
    UPDATE {{ vars.road_staging_table }}
    SET 
      unique_row_id = md5(
        COALESCE(CAST(device_id AS text), '') ||
        COALESCE(CAST(road_name AS text), '') ||
        COALESCE(CAST(road_info AS text), '') 
      );
```
{% endraw %}

These two `UPDATE` SQL commands set a deterministic hashed identifier for every row in our staging tables and then hashing the result with `md5` so we get a compact `unique_row_id `useful for dedupe (i.e., eliminating data deduplication) and  (i.e., scripts that can be executed multiple times without changing the result beyond the initial application) merges.

Let's take a closer look to the SQL command:

- `UPDATE {{ vars.<staging_table> }}`: targets the staging table referenced by our variable.
- `SET unique_row_id = `: Writes a value into the unique_row_id column for every row.
- `md5( )`: Computes the MD5 hash of the concatenated string, producing a fixed-length digest used as the row identifier.
- `COALESCE(CAST(<column_name> AS text), '')`: Converts the field of `<column_name>` to text and replaces `NULL` with an empty string so the concatenation never yields `NULL`.
- `||`: This is the SQL string concatenation operator that joins two text values into one.

Regarding the road table we utilized all of its columns to produce the `unique_row_id`. On the other hand, we only utilized the `device_id` and the `processing_time` column to produce the `unique_row_id` since we can't expect to have a row which has the same `device_id` and `processing_time`, but different `average_speed` or `counted_cars`. 

##### `batch_id` and `ingest_time`
But what about the `batch_id` and `ingest_time` column? Adding a `batch_id` and/or `ingest_time` is a best practice in data engineering to track lineage, ensuring we know exactly which Kestra execution created which rows. And what better way to track `batch_id` than by using Kestra's built-in `execution.id` variable, and track `ingest_time` than by using Kestra's built-in `trigger.date` and `execution.startDate` variable.

```yaml
- id: add_batch_id_to_traffic
  type: io.kestra.plugin.jdbc.postgresql.Queries
  sql: |
    UPDATE {{ vars.traffic_staging_table }}
    SET 
      batch_id = '{{ execution.id }}',
      ingest_time = '{{ trigger.date ?? execution.startDate }}';

- id: add_batch_id_to_road
  type: io.kestra.plugin.jdbc.postgresql.Queries
  sql: |
    UPDATE {{ vars.road_staging_table }}
    SET 
      batch_id = '{{ execution.id }}',
      ingest_time = '{{ trigger.date ?? execution.startDate }}';
```

#### Merging the Staging and Main Tables
It's finally time to merge the staging tables with their respective main tables. We'll use the `io.kestra.plugin.jdbc.postgresql.Queries` type once again:
 
```yaml
- id: merge_traffic_tables
  type: io.kestra.plugin.jdbc.postgresql.Queries
  sql: |
    MERGE INTO {{ vars.traffic_table }} AS M
    USING {{ vars.traffic_staging_table }} AS S
    ON M.unique_row_id = S.unique_row_id
    WHEN NOT MATCHED THEN
    INSERT (
      unique_row_id, batch_id, ingest_time, device_id, counted_cars,
      processing_time, average_speed
    )
    VALUES (
      S.unique_row_id, S.batch_id, S.ingest_time, S.device_id, S.counted_cars,
      S.processing_time, S.average_speed
    );

- id: merge_road_tables
  type: io.kestra.plugin.jdbc.postgresql.Queries
  sql: |
    MERGE INTO {{ vars.road_table }} AS M
    USING {{ vars.road_staging_table }} AS S
    ON M.unique_row_id = S.unique_row_id
    WHEN NOT MATCHED THEN
    INSERT (
      unique_row_id, batch_id, ingest_time, device_id, road_name,
      road_info
    )
    VALUES (
      S.unique_row_id, S.batch_id, S.ingest_time, S.device_id, S.road_name,
      S.road_info
    );
```

These two SQL commands perform a deduplication insert, meaning that they compare the staging table against the corresponding main table and if they find a new row (based on the unique ID) that doesn't exists on the main table yet, then add it. If you find a row that already exists in the main table, do nothing.

Let's get a closer look at the commands:

- `MERGE INTO`: Identifies the main table (aliased as `M`)
- `USING`: Idenftifies the staging table (aliased as `S`)
- `ON`: This is the "join" condition. It tells the database how to match rows between the two tables. It looks at the `unique_row_id` in the new batch (`S`) and tries to find a matching ID in the main table (`M`).
- `WHEN NOT MATCHED`: This logic triggers only if the database looks for the `unique_row_id` in the main table and cannot find it. 
- `THEN INSERT ...`: For the IDs that don't exist yet, the database treats them as brand new records and copies the respecitive columns from `S` into `M`.

#### Cleaning
After merging it's time to do some cleaning. After the staging data does it's job it should be cleaned, otherwise we'd be left with two identical tables. We'll clean the staging tables by using `TRUNCATE` which removes all rows but keeps th tables structure and indices intact.

Furthermore, it's best practice to `TRUNCATE` at the start of the workflow, rather than the end of it. If for example our flow fails (or succeeds with weird data), the data remains in the staging table until the next run triggers. This gives us a window of time to log in and inspect the data to see what went wrong.

So, let's truncate the staging tables before we load them with data:

```yaml
- id: staging_traffic_table_maker
  # ... our creation logic ...

- id: staging_road_table_maker
  # ... our creation logic ...

- id: clear_traffic_staging
  type: io.kestra.plugin.jdbc.postgresql.Query
  sql: TRUNCATE TABLE {{ vars.traffic_staging_table }};

- id: clear_road_staging
  type: io.kestra.plugin.jdbc.postgresql.Query
  sql: TRUNCATE TABLE {{ vars.road_staging_table }};

- id: clear_staging
  type: io.kestra.plugin.jdbc.postgresql.Query
  sql: TRUNCATE TABLE {{ vars.road_staging_table }};

- id: copy_in_to_traffic_staging_table
  # ... our loading logic ...

- id: copy_in_to_road_staging_table
  # ... our loading logic ...
```

## Final ETL Pipeline
We conclude this article with the final Kestra flow:

```yaml
id: my_first_etl_article
namespace: company.team

inputs:
  - id: date
    type: DATE
    after: 2021-11-05

variables:
  table: road_traffic_attica
  url: "https://data.gov.gr/api/v1/query/{{ vars.table }}?date_from={{ inputs.date }}&date_to={{ inputs.date }}"
  traffic_table: traffic_table
  road_table: road_table
  traffic_staging_table: traffic_staging_table
  road_staging_table: road_staging_table
  traffic_file_name: traffic.csv
  road_file_name: road.csv

tasks:
  - id: set_label
    type: io.kestra.plugin.core.execution.Labels
    labels:
      file_date: "{{ inputs.date }}"

  - id: extract_data
    type: io.kestra.plugin.core.http.Download
    uri: "{{ render(vars.url) }}"

  - id: transform_with_python
    type: io.kestra.plugin.scripts.python.Script
    containerImage: python-with-pandas:latest
    inputFiles:
      data.json: "{{ outputs.extract_data.uri }}"
    outputFiles:
      - "{{ vars.traffic_file_name }}"
      - "{{ vars.road_file_name }}"
    script: |
      import pandas as pd
      
      # Read the JSON file
      df = pd.read_json("data.json")
      
      # Rename the columns
      df = df.rename(columns={
        'deviceid': 'device_id',
        'countedcars': 'counted_cars',
        'appprocesstime': 'time',
        'road_name': 'road_name',
        'road_info': 'road_info',
        'average_speed': 'average_speed'
      })

      # Split the dataframe into two tables
      df_traffic = df.drop(columns=['road_name', 'road_info'])
      df_road = df.drop(columns=['counted_cars', 'time', 'average_speed'])

      # Remove duplicate rows resulting from different processing times
      # on the road info table
      df_road = df_road.drop_duplicates()

      # Save to CSV
      df_traffic.to_csv("{{ vars.traffic_file_name }}", index=False)
      df_road.to_csv("{{ vars.road_file_name }}", index=False)

  - id: traffic_table_maker
    type: io.kestra.plugin.jdbc.postgresql.Query
    sql: |
      CREATE TABLE IF NOT EXISTS {{ vars.traffic_table }} (
        unique_row_id text,
        batch_id text,
        ingest_time timestamp,
        device_id	text,
        counted_cars	numeric,
        processing_time	timestamp,
        average_speed	numeric
      );

  - id: road_table_maker
    type: io.kestra.plugin.jdbc.postgresql.Query
    sql: |
      CREATE TABLE IF NOT EXISTS {{ vars.road_table }} (
        unique_row_id text,
        batch_id text,
        ingest_time timestamp,
        device_id	text,
        road_name	text,
        road_info	text
      );

  - id: staging_traffic_table_maker
    type: io.kestra.plugin.jdbc.postgresql.Query
    sql: |
      CREATE TABLE IF NOT EXISTS {{ vars.traffic_staging_table }} (
        unique_row_id text,
        batch_id text,
        ingest_time timestamp,
        device_id	text,
        counted_cars	numeric,
        processing_time	timestamp,
        average_speed	numeric
      );

  - id: staging_road_table_maker
    type: io.kestra.plugin.jdbc.postgresql.Query
    sql: |
      CREATE TABLE IF NOT EXISTS {{ vars.road_staging_table }} (
        unique_row_id text,
        batch_id text,
        ingest_time timestamp,
        device_id	text,
        road_name	text,
        road_info	text
      );

  - id: clear_traffic_staging
    type: io.kestra.plugin.jdbc.postgresql.Queries
    sql: TRUNCATE TABLE {{ vars.traffic_staging_table }};

  - id: clear_road_staging
    type: io.kestra.plugin.jdbc.postgresql.Queries
    sql: TRUNCATE TABLE {{ vars.road_staging_table }};

  - id: copy_in_to_traffic_staging_table
    type: io.kestra.plugin.jdbc.postgresql.CopyIn
    format: CSV
    from: "{{ outputs.transform_with_python.outputFiles[render(vars.traffic_file_name)] }}"
    #from: outputs["extract"]["outputFiles"]['{{ render(vars.file_name) }}']
    table: "{{ vars.traffic_staging_table }}"
    header: true
    columns: [device_id, counted_cars, processing_time, average_speed]

  - id: copy_in_to_road_staging_table
    type: io.kestra.plugin.jdbc.postgresql.CopyIn
    format: CSV
    from: "{{ outputs.transform_with_python.outputFiles[render(vars.road_file_name)] }}"
    table: "{{ vars.road_staging_table }}"
    header: true
    columns: [device_id, road_name, road_info]

  - id: add_unique_id_to_traffic
    type: io.kestra.plugin.jdbc.postgresql.Queries
    sql: |
      UPDATE {{ vars.traffic_staging_table }}
      SET 
        unique_row_id = md5(
          COALESCE(CAST(device_id AS text), '') ||
          COALESCE(CAST(processing_time AS text), '') 
        );

  - id: add_unique_id_to_road
    type: io.kestra.plugin.jdbc.postgresql.Queries
    sql: |
      UPDATE {{ vars.road_staging_table }}
      SET 
        unique_row_id = md5(
          COALESCE(CAST(device_id AS text), '') ||
          COALESCE(CAST(road_name AS text), '') ||
          COALESCE(CAST(road_info AS text), '') 
        );

  - id: add_batch_id_to_traffic
    type: io.kestra.plugin.jdbc.postgresql.Queries
    sql: |
      UPDATE {{ vars.traffic_staging_table }}
      SET 
        batch_id = '{{ execution.id }}',
        ingest_time = '{{ trigger.date ?? execution.startDate }}';

  - id: add_batch_id_to_road
    type: io.kestra.plugin.jdbc.postgresql.Queries
    sql: |
      UPDATE {{ vars.road_staging_table }}
      SET 
        batch_id = '{{ execution.id }}',
        ingest_time = '{{ trigger.date ?? execution.startDate }}';

  - id: merge_traffic_tables
    type: io.kestra.plugin.jdbc.postgresql.Queries
    sql: |
      MERGE INTO {{ vars.traffic_table }} AS M
      USING {{ vars.traffic_staging_table }} AS S
      ON M.unique_row_id = S.unique_row_id
      WHEN NOT MATCHED THEN
      INSERT (
        unique_row_id, batch_id, ingest_time, device_id, counted_cars,
        processing_time, average_speed
      )
      VALUES (
        S.unique_row_id, S.batch_id, S.ingest_time, S.device_id, S.counted_cars,
        S.processing_time, S.average_speed
      );

  - id: merge_road_tables
    type: io.kestra.plugin.jdbc.postgresql.Queries
    sql: |
      MERGE INTO {{ vars.road_table }} AS M
      USING {{ vars.road_staging_table }} AS S
      ON M.unique_row_id = S.unique_row_id
      WHEN NOT MATCHED THEN
      INSERT (
        unique_row_id, batch_id, ingest_time, device_id, road_name,
        road_info
      )
      VALUES (
        S.unique_row_id, S.batch_id, S.ingest_time, S.device_id, S.road_name,
        S.road_info
      );



pluginDefaults:
  - type: io.kestra.plugin.jdbc.postgresql
    values:
      url: jdbc:postgresql://pgdatabase:5432/traffic
      username: root
      password: root
```

























