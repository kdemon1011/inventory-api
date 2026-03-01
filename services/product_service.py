from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.product import Product
from schemas.product import ProductCreate, ProductUpdate


async def create_product(db: AsyncSession, data: ProductCreate):
    product = Product(
        name=data.name,
        sku=data.sku,
        description=data.description,
        price=data.price,
        stock_quantity=data.stock_quantity,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def get_product(db: AsyncSession, product_id: int):
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def search_products(db: AsyncSession, name: str):
    query = select(Product).where(Product.name.ilike(f"%{name}%"))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_products(db: AsyncSession, active_only: bool = True):
    query = select(Product)
    if active_only:
        query = query.where(Product.is_active == True)
    query = query.order_by(Product.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_product(db: AsyncSession, product_id: int, data: ProductUpdate):
    product = await get_product(db, product_id)
    if not product:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.flush()
    await db.refresh(product)
    return product
