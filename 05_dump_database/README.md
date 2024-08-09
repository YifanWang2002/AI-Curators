# Database Setup and Cleanup Guide

Welcome to our database management utility. This folder contains two essential scripts for setting up and deleting databases using MySQL and MongoDB configurations.

## Dependencies

Ensure you have `pymysql` and `pymongo` installed:

```bash
pip install pymysql pymongo
```


## Scripts

### 1. Database Setup (`db_setup.py`)

This script initializes and configures MySQL and MongoDB databases according to the provided schema and configuration files.

#### Usage

1. Ensure that JSON configuration files for MySQL and MongoDB (`mysql_config.json`, `mongo_config.json`) and schema files (`mysql_schema.json`, `mongo_schema.json`) are present in the `db_config` directory.
2. Run the script to set up databases:
   ```bash
   python setup_databases.py
   ```

### 2. Database Cleanup (`db_cleanup.py`)

This script deletes specified MySQL and MongoDB databases to reset or clear all data.


#### Usage

1. Confirm that the correct databases are specified in the configuration files in the `db_config` directory.
2. Execute the script to remove the databases:
   ```bash
   python cleanup_databases.py
   ```

## Configuration

### JSON Configuration Files

Ensure that the `db_config` folder contains:

- `mysql_config.json`: MySQL server credentials and database name.
- `mongo_config.json`: MongoDB server details and database names.
- `mysql_schema.json`: Definitions for MySQL tables.
- `mongo_schema.json`: Schemas and indexes for MongoDB collections.

### Important Notes

- **Backup your data** before running the cleanup script to avoid irreversible loss.
- The setup script will create databases and tables/collections if they do not already exist, and apply schemas and indexes as specified.


