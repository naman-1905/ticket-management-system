from fastapi import FastAPI


app = FastAPI(
    title="Ticket Management System API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Ticket Management System API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }