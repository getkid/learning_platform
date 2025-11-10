from fastapi import FastAPI

app = FastAPI(title="Code Executor Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Code Executor Service"}