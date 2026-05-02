#!/usr/bin/env python3
import sys
from django.setup import setup

# Execute via `python manage.py runscript` is possible, but here we expect
# the container's PYTHONPATH to include project; we will import Django via manage.py

if __name__ == '__main__':
    # This file is intended to be executed with the project's manage.py shell
    # Example: docker compose exec web python manage.py shell < this_file
    # But we'll make it importable: instead run via `python -c` is messy.
    print('This script is a helper. Prefer using manage.py shell or run it via the container.')
