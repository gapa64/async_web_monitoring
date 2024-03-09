# Async Web Monitoring
## The lightweight Web Monitoring Solution to monitor web-sites reachability

Table of contents
- [Project Description](#project-description)
- [Project deployment](#project-deployment)
- [Project testing](#project-testing)


## Project Description

The project implements simple Web monitoring by fetching web pages.  
The solution is based on asyncio framework, aiohttp web client and aiopg PostgreSQL client.  
Solution is posible to run in a docker container or as the standalone script

## Project deployment

1. Clone repository from github
```bash
git clone https://github.com/gapa64/async_web_monitoring
```
2. Create .env file with the appropriate template in the project directory
```bash
cd pythonswe-01.03.2024-gapa64
```
.env file template
```bash
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5433
RESULT_TABLE=async_results
ERROR_TABLE=async_errors
```
3. Specify monitored urls in urls.py
```python
URLS_DB = [
    ('https://python.org', 5, r'Python\s+is\s+a\s+programming'),
    ('https://google.com', 5, r'blablabla'),
]
```
4. Navigate to infra directory and Start the project
```bash
cd infra
docker-compose up -d 
```
## Project testing
For the pytest purpose, another compose file is delivered with local db definition.  
To run pytests navigate to 
```bash
cd infra_pytests
docker-compose up
```
For the Pytest purposes I recomend to use the following .env template
```bash
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
RESULT_TABLE=async_results
ERROR_TABLE=async_errors
```
## Known bugs
1. The docker image uses psycopg-binary only and can not install psycopg2 lib from the requirements.  
However for the venv on mac-os it works fine with main psycopg2 package. 
If dependency failure you may try to add psycopg2 to requirements.
```bash
psycopg2==2.9.9
```