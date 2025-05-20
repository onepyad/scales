# Scales Project

This repository contains Python scripts and service files for running the weight and laser measurement system.

## Installation

Create a virtual environment (optional) and install dependencies from `requirements.txt`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

Two main scripts are provided:

- `usr/sbin/wsh/api.py` &mdash; starts the Flask API server on port 5000.
- `usr/sbin/wsh/weith.py` &mdash; reads weight and laser measurements.

Example to run the API:

```bash
python3 usr/sbin/wsh/api.py
```

The `etc/systemd/system` folder contains example service files for running these scripts as systemd services.
