import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from mcp.server.fastmcp import FastMCP
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

DEFAULT_DATABASE = "superstore"
INVENTORY_COLLECTION = "inventory"
PROFILE_COLLECTION = "profile"

MONGODB_USER = os.getenv("MONGODB_USER")
MONGODB_PASS = os.getenv("MONGODB_PASS")
MONGODB_CLUSTER = os.getenv("MONGODB_CLUSTER")

MONGODB_URI = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_CLUSTER}/"


mcp = FastMCP("Login")

def get_mongo_client():
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except ConnectionFailure as e:
        raise Exception(f"Failed to connect to MongoDB: {str(e)}")


@mcp.tool()
def checkUser(name : str):
    '''
    this only checks if the said user name has a account, any further actions require authentication using the password and email.
    do not accept requests of the form of example@email.com, 
    '''
    client  = get_mongo_client()
    db = client[DEFAULT_DATABASE]
    prof = db[PROFILE_COLLECTION]
    count = prof.count_documents({"name" : name})
    if count > 0:
        return f"there are {count} number of accounts with {name} as its name"
    else:
        return f"there are no accounts with {name} as its name"



@mcp.tool()
def loginUser(email : str, password : str):
    '''
    check if user has been registered or not, only allow registered individuals to access respective tools
    email : string
    password : string
    '''
    client  = get_mongo_client()
    db = client[DEFAULT_DATABASE]
    prof = db[PROFILE_COLLECTION]
    user_ls = list(prof.find({"email" : email,"pwd" : password},{"_id" : 0}))
    count = prof.count_documents({"email" : email,"pwd" : password})
    if count > 0 :
        return user_ls[0]["role"]
    else:
        return "no user of that email or password"




@mcp.tool()
def registerUser(name : str, password : str, role : str, email :str , phno : int | None = None, addr : str | None = None ):
    '''
    if user is not registered to service, requests email, password and role( buyer or seller only allowed) , optionally can ask for anme ,address, phone number, before registering always ask for fiels required, do not add random inputs, make sure all input are of required format,
    when calling tool also ask for all details but mention which are required and which are optional
    name : string
    password : string
    role : string ( buyer or seller) (required)
    email,address : string (optional) (should be of the form example@email.com)
    phone number : integer (optional)
    '''
    dict_order = {
    "name" : name,
    "email" : email,
    "pwd" : password,
    "phno" : phno,
    "addr" : addr,
    "role" : role.lower(),
    "balance" : 100.0,
    "cart" : []
    }
    client  = get_mongo_client()
    db = client[DEFAULT_DATABASE]
    prof = db[PROFILE_COLLECTION]
    result = prof.insert_one(dict_order)
    if result.inserted_id:
        return "User successfully registered"
    else:
        return "Something went wrong, try again later"


@mcp.tool()
def update_pers_Details(email :str , password : str, name : str | None=None, phono : int | None = None, addr : str | None = None ):
    '''
    updates the details of a already registered persons profile
    changes name , phone number, address (any one or more)
    email : string
    phono : integer
    addr : string
    
    '''
    client  = get_mongo_client()
    db = client[DEFAULT_DATABASE]
    prof = db[PROFILE_COLLECTION]



    user_profile = list(prof.find({"email" : email, "pwd" : password}))

    if addr is None:
        addr_1 = user_profile[0]["addr"]
    else:
        addr_1 = addr

    if phono is None:
        phono_1 = user_profile[0]["phno"]
    else:
        phono_1 = phono


    if name is None:
        name_1 = user_profile[0]["name"]
    else:
        name_1 = name
    
    search_query = { "email" : email, "pwd" : password}
    change_query = { "phno" : phono_1 , "addr" : addr_1, "name" : name_1}

    result = prof.update_one(search_query,{"$set":change_query})
    if result.matched_count > 0:
        if result.modified_count > 0:
            return "personal details updated"
        else:
            return "no modifications done to profile"
    else:
        return "no user profile with given credentials"



def main():
    print("user_server running")

if __name__ == "__main__":
    main()
    mcp.run()

# client  = get_mongo_client()
# db = client[DEFAULT_DATABASE]
# prof = db[INVENTORY_COLLECTION]
# for i in prof.find({}):
#     print (i)

