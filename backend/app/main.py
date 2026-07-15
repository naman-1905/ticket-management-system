from fastapi import FastAPI
from sqlalchemy import text

from app.db.database import engine


app = FastAPI(
    title="Ticket Management System Backend",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Ticket Management System Backend is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.get("/health/db")
def database_health_check():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_user")
        )

        database, user = result.one()

    return {
        "status": "healthy",
        "database": database,
        "user": user,
    }