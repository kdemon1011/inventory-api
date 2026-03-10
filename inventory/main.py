from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import init_db
from routers.products import router as products_router
from routers.orders import router as orders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Inventory Management API",
    version="0.3.1",
    lifespan=lifespan,
)

app.include_router(products_router)
app.include_router(orders_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from config import API_PORT

    uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, reload=True)
