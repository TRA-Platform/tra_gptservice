#!/bin/bash
python -m celery -A gptService worker --concurrency=8 -Ofair -E -B