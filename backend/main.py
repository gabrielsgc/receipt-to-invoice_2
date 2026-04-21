from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import receipts, invoices, mercadona

app = FastAPI(title="Receipt to Invoice API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(receipts.router, prefix="/api/receipts", tags=["receipts"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(mercadona.router, prefix="/api/mercadona", tags=["mercadona"])


@app.get("/")
def root():
    return {"message": "Receipt to Invoice API running"}
