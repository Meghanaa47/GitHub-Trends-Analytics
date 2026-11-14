
import os
from pathlib import Path
from datetime import datetime

import requests
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text


# 1. LOAD DATABASE CONFIGURATION

load_dotenv(
    Path(__file__).resolve().parent / ".env",
    override=True
)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

if not DB_USER or not DB_PASSWORD:
    raise ValueError("MySQL username or password missing in .env file")

print("Database username:", DB_USER)
print("Database password loaded:", bool(DB_PASSWORD))


# 2. EXTRACT DATA FROM GITHUB REST API

api_url = "https://api.github.com/search/repositories"

languages = ["Java", "Python", "JavaScript", "SQL", "C++", "Go"]

repositories = []

for language in languages:

    params = {
        "q": f"language:{language}",
        "sort": "stars",
        "order": "desc",
        "per_page": 10
    }

    response = requests.get(
        api_url,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        print(
            f"API request failed for {language}: "
            f"{response.status_code}"
        )
        continue

    data = response.json()

    for repo in data["items"]:

        repositories.append({
            "repository": repo["full_name"],
            "language": repo["language"],
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "open_issues": repo["open_issues_count"],
            "created_at": repo["created_at"],
            "updated_at": repo["updated_at"],
            "url": repo["html_url"]
        })

    print(
        f"Fetched {len(data['items'])} repositories "
        f"for {language}"
    )


# 3. TRANSFORM AND CLEAN DATA

df = pd.DataFrame(repositories)

if df.empty:
    raise ValueError("No repository data was collected from GitHub.")

print("\nTotal repositories collected:", len(df))

df["created_at"] = pd.to_datetime(
    df["created_at"], utc=True
).dt.tz_localize(None)

df["updated_at"] = pd.to_datetime(
    df["updated_at"], utc=True
).dt.tz_localize(None)

df = df.astype(object).where(pd.notna(df), None)


# 4. CONNECT TO MYSQL


# 4. CONNECT TO TIDB CLOUD

DB_NAME = os.getenv("DB_NAME", "github_analytics")
DB_CA_PATH = os.getenv("DB_CA_PATH")

if not DB_CA_PATH:
    raise ValueError("TiDB CA certificate path missing in .env")

ca_path = Path(DB_CA_PATH)

if not ca_path.is_absolute():
    ca_path = Path(__file__).resolve().parent / ca_path

db_url = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

engine = create_engine(
    db_url,
    connect_args={
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
        "ssl_ca": str(ca_path)
    },
    pool_recycle=300,
    pool_pre_ping=True
)



# 5. PREPARE COMMON SNAPSHOT TIMESTAMP

snapshot_time = datetime.now()

records = df.to_dict(orient="records")

for record in records:
    record["collected_at"] = snapshot_time


# 6. LOAD DATA INTO MYSQL

insert_query = text("""
    INSERT INTO repository_snapshots (
        repository,
        language,
        stars,
        forks,
        open_issues,
        created_at,
        updated_at,
        repository_url,
        collected_at
    )
    VALUES (
        :repository,
        :language,
        :stars,
        :forks,
        :open_issues,
        :created_at,
        :updated_at,
        :url,
        :collected_at
    )
""")

try:

    with engine.begin() as connection:

        connection.execute(
            insert_query,
            records
        )

    print("\nData successfully loaded into MySQL!")
    print("Records inserted:", len(records))
    print("Snapshot timestamp:", snapshot_time)

finally:
    engine.dispose()
