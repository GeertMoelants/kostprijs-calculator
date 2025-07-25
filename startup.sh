#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Upgrade de database naar de laatste versie
echo "Running database upgrades..."
flask db upgrade

# Vul de database met initiële data (de seeder is slim genoeg om dit niet opnieuw te doen)
echo "Seeding database if necessary..."
flask seed-db

# Start de Gunicorn webserver
echo "Starting Gunicorn..."
exec gunicorn app:app
