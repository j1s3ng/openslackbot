from fastapi import FastAPI


app = FastAPI(title="local-slack-rag-bot RAG API")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
