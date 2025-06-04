import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from mcp.server.fastmcp import FastMCP
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

mcp = FastMCP("Seller Service")

MONGODB_USER = os.getenv("MONGODB_USER")
MONGODB_PASS = os.getenv("MONGODB_PASS")
MONGODB_CLUSTER = os.getenv("MONGODB_CLUSTER")

MONGODB_URI = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_CLUSTER}/"

DEFAULT_DATABASE = "superstore"
INVENTORY_COLLECTION = "inventory"
PROFILE_COLLECTION = "profile"

def get_mongo_client():
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except ConnectionFailure as e:
        raise Exception(f"Failed to connect to MongoDB: {str(e)}")

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if isinstance(doc, dict):
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                doc[key] = str(value)
            elif isinstance(value, dict):
                doc[key] = serialize_doc(value)
            elif isinstance(value, list):
                doc[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
    return doc

@mcp.tool()
def add_product(seller_email, product_name, price, quantity):
    """
    Add a product to the inventory.
    Args:
        seller_email: Seller's email (to identify seller)
        product_name: Name of the product
        price: Price of the product
        quantity: Quantity of the product
    """
    try:
        client = get_mongo_client()
        db = client[DEFAULT_DATABASE]
        collection = db[INVENTORY_COLLECTION]

        product = {
            "name": product_name.strip(),
            "price": float(price),
            "quantity": int(quantity),
            "seller_email": seller_email.strip().lower(),
        }

        result = collection.insert_one(product)
        product["_id"] = str(result.inserted_id)

        return json.dumps({"message": "Product added successfully", "product": product}, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        client.close()

@mcp.tool()
def add_multiple_products(seller_email: str, products_json: list[dict]) -> str:
    """
    Add multiple products to the inventory in one go.
    """
    client = None
    try:
        products_data = products_json 

        if not isinstance(products_data, list):
            return json.dumps({"error": "Expected a list of products."})

        client = get_mongo_client()
        db = client[DEFAULT_DATABASE]
        collection = db[INVENTORY_COLLECTION]

        products = []
        for p in products_data:
            product = {
                "name": p["name"].strip(),
                "price": float(p["price"]),
                "quantity": int(p["quantity"]),
                "seller_email": seller_email.strip().lower()
            }
            products.append(product)

        result = collection.insert_many(products)

        for i, product in enumerate(products):
            product["_id"] = str(result.inserted_ids[i])

        return json.dumps({
            "message": f"{len(products)} products added successfully",
            "products": products
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if client:
            client.close()

@mcp.tool()
def update_product(product_id, field, new_value):
    """
    Update product details.
    Args:
        product_id: ID of the product to update
        field: Field to update (name, price, quantity)
        new_value: New value for the field
    """
    try:
        client = get_mongo_client()
        db = client[DEFAULT_DATABASE]
        collection = db[INVENTORY_COLLECTION]

        update_field = field.strip().lower()
        if update_field not in ["name", "price", "quantity"]:
            return json.dumps({"error": "Invalid field. Choose from 'name', 'price', or 'quantity'."})

        if update_field == "price":
            new_value = float(new_value)
        elif update_field == "quantity":
            new_value = int(new_value)
        else:
            new_value = new_value.strip()

        result = collection.update_one({"_id": ObjectId(product_id)}, {"$set": {update_field: new_value}})
        if result.modified_count == 0:
            return json.dumps({"message": "No changes made. Check product_id."})
        return json.dumps({"message": f"Product updated: {update_field} set to {new_value}"})

    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        client.close()

@mcp.tool()
def delete_product(product_id):
    """
    Delete a product from the inventory.
    Args:
        product_id: ID of the product to delete
    """
    try:
        client = get_mongo_client()
        db = client[DEFAULT_DATABASE]
        collection = db[INVENTORY_COLLECTION]

        result = collection.delete_one({"_id": ObjectId(product_id)})
        if result.deleted_count == 0:
            return json.dumps({"message": "No product found with given ID."})
        return json.dumps({"message": "Product deleted successfully."})

    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        client.close()

@mcp.tool()
def view_seller_products(seller_name):
    """
    View all products added by a seller.
    Args:
        seller_name: Seller's name (case-insensitive)
    """
    try:
        client = get_mongo_client()
        db = client[DEFAULT_DATABASE]
        profile_collection = db[PROFILE_COLLECTION]
        inventory_collection = db[INVENTORY_COLLECTION]

        seller_profile = profile_collection.find_one({
            "name": {"$regex": f"^{seller_name.strip()}$", "$options": "i"},
            "role": {"$regex": "^seller$", "$options": "i"}
        })

        if not seller_profile:
            return json.dumps({"error": f"No seller found with name '{seller_name}'."})

        seller_email = seller_profile.get("email")
        if not seller_email:
            return json.dumps({"error": "Seller email not found in profile."})

        cursor = inventory_collection.find({"seller_email": seller_email.lower()})
        products = [serialize_doc(doc) for doc in cursor]

        return json.dumps({
            "seller_name": seller_name,
            "seller_email": seller_email,
            "product_count": len(products),
            "products": products
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        client.close()

if __name__ == "__main__":
    mcp.run()