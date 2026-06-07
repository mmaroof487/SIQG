from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.post("/test")
async def test_endpoint():
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
