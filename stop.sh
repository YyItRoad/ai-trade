#!/bin/bash
echo "Stopping and removing all containers and networks..."
# Use the same compose files as the start scripts to ensure everything is torn down
docker compose -f docker-compose.yml -f docker-compose.db.yml down --remove-orphans
echo "All services have been stopped."