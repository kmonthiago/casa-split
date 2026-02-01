#!/usr/bin/env bash
set -e

# Render fornece PORT; streamlit precisa ouvir em 0.0.0.0
streamlit run app.py --server.port "$PORT" --server.address 0.0.0.0

