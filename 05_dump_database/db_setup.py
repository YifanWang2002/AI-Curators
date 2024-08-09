import json
import pymysql
from pymongo import MongoClient


# MySQL Setup
def setup_mysql(mysql_config, mysql_schema):
    # Connect to MySQL server without specifying the database to create it if not exists
    initial_conn = pymysql.connect(
        host=mysql_config['host'],
        user=mysql_config['user'],
        password=mysql_config['password']
    )
    initial_cursor = initial_conn.cursor()
    initial_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {mysql_config['database']}")
    initial_conn.commit()
    initial_cursor.close()
    initial_conn.close()

    # Connect to the newly created or existing database
    connection = pymysql.connect(
        host=mysql_config['host'],
        user=mysql_config['user'],
        password=mysql_config['password'],
        database=mysql_config['database']
    )
    cursor = connection.cursor()
    
    # Create tables as per the schema
    for table in mysql_schema['schema']:
        fields = ", ".join([f"{field['name']} {field['type']}" for field in table['fields']])
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table['table_name']} ({fields});"
        cursor.execute(create_table_query)
        print(f"Table '{table['table_name']}' setup complete.")
    
    connection.commit()
    cursor.close()
    connection.close()


# MongoDB Setup
def setup_mongo(mongo_config, mongo_schema):
    for db in mongo_config['mongo']:
        client = MongoClient(host=db['host'], port=db['port'])
        database = client[db['database']]
        
        for collection in db.get('collections', []):
            coll_name = collection['name']
            coll = database[coll_name]

            # Ensure collection exists, apply schema validation if specified
            db_schema = mongo_schema.get(db['alias'], {}).get(coll_name, {})
            if db_schema:
                validation = {"$jsonSchema": db_schema}
                try:
                    database.create_collection(
                        coll_name,
                        validator=validation,
                        validationAction="error"
                    )
                    print(f"Collection '{coll_name}' created with schema validation in {db['alias']}.")
                except Exception as e:
                    print(f"Collection '{coll_name}' already exists. Updating schema.")
                    database.command({
                        'collMod': coll_name,
                        'validator': validation,
                        'validationAction': "error"
                    })
                    print(f"Schema for collection '{coll_name}' updated in {db['alias']}.")

            # Create indexes if specified
            for index in collection.get('indexes', []):
                coll.create_index([(index, 1)])  # Assuming ascending index for simplicity
                print(f"Index on '{index}' created in collection '{coll_name}'.")

            print(f"Collection '{coll_name}' setup in {db['alias']} with indexes: {collection.get('indexes', [])}")

        print(f"Setup for {db['alias']} complete.")

def verify_database_creations(mysql_config, mysql_schema, mongo_config, mongo_schema):
    # Verify MySQL database and tables
    try:
        mysql_conn = pymysql.connect(host=mysql_config['host'],
                                     user=mysql_config['user'],
                                     password=mysql_config['password'],
                                     database=mysql_config['database'])
        cursor = mysql_conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"MySQL - Database '{mysql_config['database']}' has tables: {tables}")
        expected_tables = {table['table_name'] for table in mysql_schema['schema']}
        print("MySQL - Missing tables:", expected_tables.difference(tables))
    except Exception as e:
        print(f"MySQL Error: {e}")
    finally:
        if 'mysql_conn' in locals():
            mysql_conn.close()

    # Verify MongoDB databases and collections
    mongo_client = MongoClient(host=mongo_config['mongo'][0]['host'], port=mongo_config['mongo'][0]['port'])
    for db in mongo_config['mongo']:
        database = mongo_client[db['database']]
        collections = database.list_collection_names()
        print(f"MongoDB - Database '{db['database']}' has collections: {collections}")
        expected_collections = {coll['name'] for coll in db.get('collections', [])}
        print("MongoDB - Missing collections:", expected_collections.difference(collections))




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

    setup_mysql(mysql_config, mysql_schema)

    setup_mongo(mongo_config, mongo_schema)

    verify_database_creations(mysql_config, mysql_schema, mongo_config, mongo_schema)



