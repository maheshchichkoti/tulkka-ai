# src/middlewares/idempotency.py
from fastapi import Request, HTTPException
from typing import Optional
from src.db.mysql_pool import execute_query
import json
import uuid

IDEMPOTENCY_HEADER = "Idempotency-Key"

def check_idempotency(user_id: str, route: str, key: Optional[str]) -> Optional[dict]:
    if not key:
        return None
    # try find existing
    row = execute_query("SELECT id, response_json FROM idempotency_keys WHERE user_id = %s AND key_value = %s AND route = %s", (user_id, key, route), fetchone=True)
    if row:
        try:
            return json.loads(row['response_json']) if row.get('response_json') else None
        except Exception:
            return None
    return None

def save_idempotent_response(user_id: str, route: str, key: str, response_obj: dict):
    idv = str(uuid.uuid4())
    execute_query("INSERT INTO idempotency_keys (id, user_id, key_value, route, response_json) VALUES (%s,%s,%s,%s,%s)",
                  (idv, user_id, key, route, json.dumps(response_obj)))
