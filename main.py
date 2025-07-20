from typing import Union
from fastapi import FastAPI, status
import pymongo
from typing import List
from pydantic import BaseModel
from bson import ObjectId


app = FastAPI()
myclient = pymongo.MongoClient("mongodb+srv://adityakale11011:ZogGvYpP4WLRpHPo@cluster0.pyy6xew.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

mydb = myclient["database"]
products = mydb['products']
orders = mydb['orders']


# Define a Pydantic model for the product
class SizeItem(BaseModel):
    size: str
    quantity: int

class Product(BaseModel):
    name: str
    price: float
    sizes: List[SizeItem]



# Define a Pydantic model for the orders
class itemList(BaseModel):
    productId: str
    qty: int

class Order(BaseModel):
    userId: str
    items: List[itemList]


# Define a routes for the API 
# POST METHODS
@app.post("/products",status_code=status.HTTP_201_CREATED)
def create_products(product: Product):
    try:
        data = product.dict()
        product = products.insert_one(data)
        return {"id":str(product.inserted_id)}
    except:
        return {"message": "Error creating product"}



@app.post("/orders",status_code=status.HTTP_201_CREATED)
def create_orders(order: Order):
    try:
        data = order.dict()
        order = orders.insert_one(data)
        return {"id":str(order.inserted_id)}
    except:
        return {"message": "Error creating product"}
    

# GET METHODS 

def serialize_product(product):
    return {
        "id": str(product["_id"]),
        "name": product["name"],
        "price": product["price"]
    }

@app.get("/products", status_code=status.HTTP_200_OK)
def get_products(name: str = "", size: str = "", limit: int = 10, offset: int = 0):
    try:
        query = {}

        if name:
            query["name"] = {"$regex": name, "$options": "i"}  # Partial match, case-insensitive

        if size:
            query["sizes.size"] = {"$regex": size, "$options": "i"}  # Partial match on nested size field

        cursor = products.find(query).skip(offset).limit(limit)

        productList = [serialize_product(doc) for doc in cursor]

        pagination = {
            "next": offset + limit,
            "limit": len(productList),
            "previous": max(offset - limit, 0)
        }

        return {
            "data": productList,
            "page": pagination
        }

    except Exception as e:
        return {"message": f"Error getting product: {str(e)}"}


def get_product_details(product_id):
    product = products.find_one({"_id": ObjectId(product_id)})
    if product:
        return {
            "name": product["name"],
            "id": str(product["_id"])
        }
    return {
        "name": "Unknown Product",
        "id": product_id
    }

def serialize_order(order):
    return {
        "id": str(order["_id"]),
        "items": [
            {
                "productDetails": get_product_details(item["product_id"]),
                "qty": item["qty"]
            }
            for item in order.get("items", [])
        ],
        "total": order.get("total", 0.0)
    }

@app.get("/orders/{user_id}", status_code=status.HTTP_200_OK)
def get_orders(user_id: str, limit: int = 10, offset: int = 0):
    query = {"userId": user_id}
    cursor = orders.find(query).skip(offset).limit(limit)
    
    order_list = []
    for doc in cursor:
        enriched_items = []
        for item in doc["items"]:
            product = products.find_one({"_id": ObjectId(item["productId"])})
            if product:
                enriched_items.append({
                    "productDetails": {
                        "name": product["name"],
                        "id": str(product["_id"])
                    },
                    "qty": item["qty"]
                })
        order_list.append({
            "id": str(doc["_id"]),
            "items": enriched_items,
            "total": doc.get("total", 0.0)
        })

    return {
        "data": order_list,
        "page": {
            "next": offset + limit,
            "limit": len(order_list),
            "previous": max(0, offset - limit)
        }
    }
