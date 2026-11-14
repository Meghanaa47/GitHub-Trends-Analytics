
# GitHub Repository Trends Analytics System

A Python-based data analytics project that collects GitHub repository data using the GitHub REST API, processes it with Pandas, stores historical snapshots in MySQL, and visualizes repository trends using Streamlit.

## Tech Stack
- Python
- GitHub REST API
- Pandas
- MySQL
- SQLAlchemy
- Streamlit
- Plotly

## Key Features
- Extracts popular repositories across six programming languages.
- Collects stars, forks, open issues, and repository details.
- Cleans and transforms data using Pandas.
- Stores data and historical snapshots in MySQL.
- Analyzes repository popularity and language trends.
- Displays interactive charts and statistics.

## Project Architecture

GitHub API → Python → Pandas → MySQL → Streamlit Dashboard

## How to Run

1. Install dependencies:
   `pip install -r requirements.txt`

2. Configure MySQL credentials in `.env`.

3. Run the ETL pipeline:
   `python main.py`

4. Launch the dashboard:
   `streamlit run dashboard.py`

## Developer

**GitHub:** [meghanaa47](https://github.com/meghanaa47)
