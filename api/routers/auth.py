"""POST /auth/signup and POST /auth/login"""
import os
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter(prefix="/auth", tags=["auth"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://langfuse:langfuse@localhost:5432/medrag")


def _get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def _ensure_table():
    """Create users table if it doesn't exist (idempotent)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('patient', 'doctor')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
    finally:
        conn.close()


# Ensure table exists on module import
try:
    _ensure_table()
except Exception:
    pass  # DB may not be ready yet at import time; table created on first request


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=4, max_length=200)
    role: Literal["patient", "doctor"]


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=4, max_length=200)


class AuthResponse(BaseModel):
    username: str
    role: str


@router.post("/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    _ensure_table()
    hashed = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING username, role",
                (req.username, hashed, req.role),
            )
            user = cur.fetchone()
        conn.commit()
        return AuthResponse(username=user["username"], role=user["role"])
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    _ensure_table()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT username, password_hash, role FROM users WHERE username = %s", (req.username,))
            user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if not bcrypt.checkpw(req.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        return AuthResponse(username=user["username"], role=user["role"])
    finally:
        conn.close()
