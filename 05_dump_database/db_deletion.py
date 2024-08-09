import json
import pymysql
from pymongo import MongoClient

def delete_all_databases(mysql_config, mongo_config):
    # Delete MySQL database
    try:
        mysql_conn = pymysql.connect(host=mysql_config['host'],
                                     user=mysql_config['user'],
                                     password=mysql_config['password'])
        cursor = mysql_conn.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS {mysql_config['database']};")
        print(f"MySQL - Database '{mysql_config['database']}' deleted.")
    except Exception as e:
        print(f"MySQL Error: {e}")
    finally:
        if 'mysql_conn' in locals():
            mysql_conn.close()

    # Delete MongoDB databases
    mongo_client = MongoClient(host=mongo_config['mongo'][0]['host'], port=mongo_config['mongo'][0]['port'])
    for db in mongo_config['mongo']:
        mongo_client.drop_database(db['database'])
        print(f"MongoDB - Database '{db['database']}' deleted.")

if __name__ == '__main__':
    # Load configurations
    with open('db_config/mysql_config.json', 'r') as f:
        mysql_config = json.load(f)

    with open('db_config/mongo_config.json', 'r') as f:
        mongo_config = json.load(f)

    with open('db_config/mysql_schema.json', 'r') as f:
        mysql_schema = json.load(f)

    with open('db_config/mongo_schema.json', 'r') as f:
        mongo_schema = json.load(f)

    delete_all_databases(mysql_config, mongo_config)
