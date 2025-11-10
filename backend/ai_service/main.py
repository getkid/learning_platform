from fastapi import FastAPI

app = FastAPI(title="AI Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AI Service"}