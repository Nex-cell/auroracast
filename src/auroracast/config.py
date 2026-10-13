"""Configuration loading: YAML files in config/ for settings, environment variables for secrets."""

import os
from pathlib import Path

import yaml
from psycopg.conninfo import make_conninfo

CONFIG_DIR = Path(os.environ.get("AURORACAST_CONFIG_DIR", Path(__file__).resolve().parents[2] / "config"))


def load_config(name: str = "sources.yaml") -> dict:
    with open(CONFIG_DIR / name) as f:
        return yaml.safe_load(f)


def db_conninfo() -> str:
    """Build the Postgres connection string from the POSTGRES_* variables (see env.sample)."""
    return make_conninfo(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
