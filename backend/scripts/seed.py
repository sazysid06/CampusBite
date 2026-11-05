import asyncio
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal, engine, Base
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole
from backend.app.models.restaurant import Restaurant, MenuItem


async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Check if seed data already exists
        check = await session.execute(select(User).where(User.email == "student@campus.edu"))
        if check.scalar_one_or_none():
            print("Database already contains seed data.")
            return

        # 2. Seed Users
        student = User(
            email="student@campus.edu",
            hashed_password=hash_password("StudentPass123!"),
            full_name="Alex Campus",
            phone_number="+919876500010",
            role=UserRole.CUSTOMER,
        )
        owner = User(
            email="dhaba_owner@campus.edu",
            hashed_password=hash_password("OwnerPass123!"),
            full_name="Rajesh Sharma",
            phone_number="+919876500020",
            role=UserRole.RESTAURANT_OWNER,
        )
        delivery = User(
            email="rider@campus.edu",
            hashed_password=hash_password("RiderPass123!"),
            full_name="Vikram Singh",
            phone_number="+919876500030",
            role=UserRole.DELIVERY_PARTNER,
        )
        session.add_all([student, owner, delivery])
        await session.flush()

        # 3. Seed Restaurant
        dhaba = Restaurant(
            owner_id=owner.id,
            name="Night Owl Canteen",
            description="Late night comfort food, rolls, and chai for campus night owls.",
            address="Near Central Library Gate 1",
            phone_number="+919876500021",
            is_open=True,
        )
        session.add(dhaba)
        await session.flush()

        # 4. Seed Menu Items
        items = [
            MenuItem(
                restaurant_id=dhaba.id,
                name="Double Egg Chicken Roll",
                description="Crispy paratha filled with spiced chicken chunks and egg.",
                price=120.0,
                category="Rolls",
                is_available=True,
            ),
            MenuItem(
                restaurant_id=dhaba.id,
                name="Paneer Tikka Roll",
                description="Smoked cottage cheese cubes tossed in spicy tandoori mayo.",
                price=110.0,
                category="Rolls",
                is_available=True,
            ),
            MenuItem(
                restaurant_id=dhaba.id,
                name="Masala Maggi Bowl",
                description="Double noodle cake cooked with sweet corn, peas, and extra tastemaker.",
                price=60.0,
                category="Snacks",
                is_available=True,
            ),
            MenuItem(
                restaurant_id=dhaba.id,
                name="Adrak Elaichi Chai (Kulhad)",
                description="Slow-brewed milk tea infused with crushed ginger and cardamom.",
                price=25.0,
                category="Beverages",
                is_available=True,
            ),
            MenuItem(
                restaurant_id=dhaba.id,
                name="Cold Coffee with Ice Cream",
                description="Thick blended espresso shake topped with vanilla ice cream.",
                price=85.0,
                category="Beverages",
                is_available=True,
            ),
        ]
        session.add_all(items)
        await session.commit()
        print("SEED COMPLETE: Users, restaurant, and menu items populated successfully.")


if __name__ == "__main__":
    asyncio.run(seed_database())