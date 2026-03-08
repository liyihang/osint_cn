#!/bin/bash

# Initialize PostgreSQL database
psql -U postgres -c "CREATE DATABASE my_database;"

# Initialize MongoDB database
mongo --eval "db.getSiblingDB('my_database').createCollection('my_collection');"

# Initialize Elasticsearch index
curl -X PUT "localhost:9200/my_index" -H 'Content-Type: application/json' -d '{ "settings": { "number_of_shards": 1 } }'