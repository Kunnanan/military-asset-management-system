"""Apply the starter schema to the MySQL database configured in .env."""
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv()
schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
statements = [statement.strip() for statement in schema.split(";") if statement.strip()]
connection = mysql.connector.connect(
    host=os.environ["MYSQL_HOST"], port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DATABASE"], ssl_disabled=False,
)
try:
    cursor = connection.cursor()
    for statement in statements:
        cursor.execute(statement)
    connection.commit()
    print(f"Applied {len(statements)} schema statements.")
finally:
    connection.close()
