"""
Synthetic e-commerce data generator using Faker.

Generates realistic datasets: customers, products, orders, transactions.
Outputs to CSV for Medallion pipeline demo.
"""

import csv
import random
from pathlib import Path

try:
    from faker import Faker

    fake = Faker()
except ImportError:
    raise ImportError("pip install faker to use the data generator")

OUTPUT_DIR = Path("data/sample")


def generate_customers(n: int = 1000) -> list[dict]:
    segments = ["consumer", "business", "enterprise", "vip"]
    return [
        {
            "id": i,
            "name": fake.name(),
            "email": fake.email(),
            "city": fake.city(),
            "state": fake.state(),
            "segment": random.choice(segments),
            "created_at": fake.date_between(start_date="-2y", end_date="today").isoformat(),
        }
        for i in range(1, n + 1)
    ]


def generate_products(n: int = 100) -> list[dict]:
    categories = ["electronics", "clothing", "food", "books", "home", "sports"]
    return [
        {
            "id": i,
            "name": fake.catch_phrase(),
            "category": random.choice(categories),
            "price": round(random.uniform(5, 500), 2),
            "brand": fake.company(),
            "stock": random.randint(0, 500),
        }
        for i in range(1, n + 1)
    ]


def generate_orders(customers: list[dict], products: list[dict], n: int = 5000) -> list[dict]:
    statuses = ["completed", "pending", "cancelled", "refunded"]
    channels = ["web", "mobile", "pos", "api"]
    orders = []
    for i in range(1, n + 1):
        customer = random.choice(customers)
        product = random.choice(products)
        qty = random.randint(1, 5)
        orders.append(
            {
                "id": i,
                "customer_id": customer["id"],
                "product_id": product["id"],
                "qty": qty,
                "total": round(product["price"] * qty, 2),
                "status": random.choices(statuses, weights=[70, 15, 10, 5])[0],
                "channel": random.choice(channels),
                "created_at": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            }
        )
    return orders


def generate_transactions(orders: list[dict], n: int = 4000) -> list[dict]:
    methods = ["credit_card", "debit_card", "pix", "boleto", "wallet"]
    statuses = ["authorized", "captured", "settled", "declined", "refunded"]
    transactions = []
    for i in range(1, n + 1):
        order = random.choice(orders)
        transactions.append(
            {
                "id": i,
                "order_id": order["id"],
                "amount": order["total"],
                "method": random.choices(methods, weights=[40, 20, 20, 10, 10])[0],
                "status": random.choices(statuses, weights=[10, 30, 40, 15, 5])[0],
                "created_at": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            }
        )
    return transactions


def write_csv(filename: str, data: list[dict]):
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=data[0].keys())
        w.writeheader()
        w.writerows(data)
    print(f"  {path} — {len(data)} rows")


def generate_all():
    print("Generating synthetic e-commerce data...")
    customers = generate_customers(500)
    products = generate_products(50)
    orders = generate_orders(customers, products, 2000)
    transactions = generate_transactions(orders, 1500)

    write_csv("customers.csv", customers)
    write_csv("products.csv", products)
    write_csv("orders.csv", orders)
    write_csv("transactions.csv", transactions)
    print(f"\n✅ Generated to {OUTPUT_DIR}/")
    return {
        "customers": len(customers),
        "products": len(products),
        "orders": len(orders),
        "transactions": len(transactions),
    }


if __name__ == "__main__":
    generate_all()
