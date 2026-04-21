from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import receipts, invoices

app = FastAPI(title="Receipt to Invoice API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(receipts.router, prefix="/api/receipts", tags=["receipts"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])


@app.get("/")
def root():
    return {"message": "Receipt to Invoice API running"}
