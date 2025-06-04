import json
from mcp.server.fastmcp import FastMCP
from bson import ObjectId
from utils.db_utils import get_mongo_client
from utils.constants import DEFAULT_DATABASE, PROFILE_COLLECTION, INVENTORY_COLLECTION
from utils.helpers import get_email_by_name

mcp = FastMCP("Buyer Service")

@mcp.tool()
def view_all_products() -> str:
    """Fetch and display all products available in the store."""
    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        products_cursor = db[INVENTORY_COLLECTION].find()

        products = []
        for product in products_cursor:
            products.append({
                "product_id": str(product["_id"]),
                "name": product["name"],
                "price": product["price"],
                "quantity": product["quantity"],
                "seller_email": product["seller_email"]
            })

        if not products:
            return "No products found in the store."

        return json.dumps(products, indent=2)

    finally:
        client.close()

@mcp.tool()
def view_cart(buyer_name: str) -> str:
    """View the contents of the buyer's cart by identifying the user with their name."""
    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        profile_coll = db[PROFILE_COLLECTION]

        profile = profile_coll.find_one({
            "name": {"$regex": f"^{buyer_name.strip()}$", "$options": "i"},
            "role": {"$regex": "^buyer$", "$options": "i"}
        })

        if not profile:
            return f"No buyer found with name: {buyer_name}"

        cart = profile.get("cart", [])
        if not cart:
            return f"{buyer_name}'s cart is empty."

        def serialize_cart_item(item):
            if isinstance(item, dict):
                return {
                    key: (str(value) if isinstance(value, ObjectId) else value)
                    for key, value in item.items()
                }
            return item

        serialized_cart = [serialize_cart_item(item) for item in cart]

        return json.dumps({
            "buyer_name": profile["name"],
            "buyer_email": profile["email"],
            "cart_count": len(serialized_cart),
            "cart": serialized_cart
        }, indent=2)
    finally:
        client.close()

@mcp.tool()
def view_product_details(product_id: str) -> str:
    """View details of a specific product"""
    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        product = db[INVENTORY_COLLECTION].find_one({"_id": ObjectId(product_id)})
        if not product:
            return "Product not found."

        details = {
            "product_id": str(product["_id"]),
            "name": product["name"],
            "price": product["price"],
            "quantity": product["quantity"],
            "seller_email": product["seller_email"]
        }
        return json.dumps(details, indent=2)
    finally:
        client.close()

@mcp.tool()
def check_balance(name: str) -> str:
    """Check balance of a buyer using name"""
    email = get_email_by_name(name)
    if not email:
        return f"No buyer found with name: {name}"

    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        user = db[PROFILE_COLLECTION].find_one({"email": email})
        return f"{name} has ₹{user.get('balance')} in their account."
    finally:
        client.close()

@mcp.tool()
def add_balance(name: str, amount: float) -> str:
    """Add amount to buyer's balance using name"""
    if amount <= 0:
        return "Amount must be greater than zero."

    email = get_email_by_name(name)
    if not email:
        return f"No buyer found with name: {name}"

    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        result = db[PROFILE_COLLECTION].update_one({"email": email}, {"$inc": {"balance": amount}})
        if result.modified_count == 0:
            return f"No buyer found with email: {email}"

        user = db[PROFILE_COLLECTION].find_one({"email": email})
        return f"Balance updated. New balance for {name}: ₹{user.get('balance')}"
    finally:
        client.close()


@mcp.tool()
def add_to_cart(name: str, product_id: str = None, quantity: int = None, items: list = None) -> str:
    """
    Add single or multiple products to the buyer's cart.
    Either pass 'product_id' and 'quantity', or 'items' as a list of {"product_id", "quantity"}.
    """

    email = get_email_by_name(name)
    if not email:
        return f"No buyer found with name: {name}"

    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        inventory = db[INVENTORY_COLLECTION]
        profile = db[PROFILE_COLLECTION]

        cart_items = []

        if items: 
            for item in items:
                pid = item.get("product_id")
                qty = item.get("quantity", 0)
                if not pid or qty <= 0:
                    continue
                product = inventory.find_one({"_id": ObjectId(pid)})
                if not product:
                    continue
                cart_items.append({
                    "product_id": str(product["_id"]),
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": qty,
                    "seller_email": product["seller_email"]
                })

            if not cart_items:
                return "No valid items to add to cart."

            profile.update_one(
                {"email": email},
                {"$push": {"cart": {"$each": cart_items}}}
            )
            return f"Added {len(cart_items)} item(s) to {name}'s cart."

        elif product_id and quantity and quantity > 0:  # Handle single addition
            product = inventory.find_one({"_id": ObjectId(product_id)})
            if not product:
                return "Product not found."

            cart_item = {
                "product_id": str(product["_id"]),
                "name": product["name"],
                "price": product["price"],
                "quantity": quantity,
                "seller_email": product["seller_email"]
            }

            profile.update_one(
                {"email": email},
                {"$push": {"cart": cart_item}}
            )
            return f"Added {quantity} of '{product['name']}' to {name}'s cart."

        else:
            return "Invalid input. Provide either a product_id with quantity, or a list of items."

    finally:
        client.close()

@mcp.tool()
def delete_from_cart(name: str, product_id: str) -> str:
    """Remove an item from the buyer's cart using their name and product_id."""
    email = get_email_by_name(name)
    if not email:
        return f"No buyer found with name: {name}"

    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        buyer = db[PROFILE_COLLECTION].find_one({"email": email})
        if buyer:
            print("Current cart:", buyer.get("cart"))

        result = db[PROFILE_COLLECTION].update_one(
            {"email": email},
            {"$pull": {"cart": {"product_id": product_id}}}
        )
        if result.modified_count == 0:
            return "Item not found in cart."
        return f"Item {product_id} removed from {name}'s cart."
    finally:
        client.close()

@mcp.tool()
def place_order(name: str) -> str:
    email = get_email_by_name(name)
    if not email:
        return f"No buyer found with name: {name}"

    client = get_mongo_client()
    try:
        db = client[DEFAULT_DATABASE]
        profile_coll = db[PROFILE_COLLECTION]
        inventory_coll = db[INVENTORY_COLLECTION]
        order_coll = db["order"]
        payment_coll = db["payment"]

        buyer = profile_coll.find_one({"email": email})
        if not buyer:
            return "Buyer profile not found."

        cart = buyer.get("cart", [])
        if not cart:
            return f"{name}'s cart is empty. Nothing to order."

        balance = buyer.get("balance", 0.0)

        total_cost = 0.0
        for item in cart:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 0)

            product = inventory_coll.find_one({"_id": ObjectId(product_id)})
            if not product:
                return f"Product {product_id} not found in inventory."

            available_qty = product.get("quantity", 0)
            if quantity > available_qty:
                return f"Insufficient stock for '{product['name']}'. Available: {available_qty}, requested: {quantity}."

            total_cost += item.get("price", 0) * quantity

        if total_cost > balance:
            return f"Insufficient balance. Total cost is ₹{total_cost}, but you have ₹{balance}."

        profile_coll.update_one({"email": email}, {"$inc": {"balance": -total_cost}})

        for item in cart:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 0)
            inventory_coll.update_one(
                {"_id": ObjectId(product_id)},
                {"$inc": {"quantity": -quantity}}
            )

        for item in cart:
            order_doc = {
                "buyer_email": email,
                "prod_name": item.get("name"),
                "quantity": item.get("quantity"),
                "total_price": item.get("price") * item.get("quantity")
            }
            order_coll.insert_one(order_doc)

        payments_map = {}
        for item in cart:
            seller = item.get("seller_email")
            amount = item.get("price") * item.get("quantity")
            payments_map[seller] = payments_map.get(seller, 0) + amount

        for seller_email, amount in payments_map.items():
            payment_doc = {
                "buyer_email": email,
                "seller_email": seller_email,
                "amount": amount
            }
            payment_coll.insert_one(payment_doc)

        profile_coll.update_one({"email": email}, {"$set": {"cart": []}})

        return f"Order placed successfully! Total amount deducted: ₹{total_cost}."

    finally:
        client.close()

if __name__ == "__main__":
    mcp.run()