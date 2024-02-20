import os
import logging
import pathlib
import json
import requests
import hashlib
from fastapi import FastAPI, Form, HTTPException,File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logger = logging.getLogger("uvicorn")
# logger level INFO->DEBUG
logger.level = logging.DEBUG
images = pathlib.Path(__file__).parent.resolve() / "images"
items_file = pathlib.Path(__file__).parent.resolve() / "items.json"
origins = [os.environ.get("FRONT_URL", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello, world!"}


@app.post("/items")
def add_item(name: str = Form(...),category: str = Form(...),image: UploadFile = File(...)):
    logger.info(f"Receive item: {name}")
    logger.info(f"Receive item: {category}")
    logger.info(f"Receive item: {image}")

    image_name = image.filename
    hashed_image = get_hash(image_name)

    save_items_in_file(name,category,hashed_image) 
    save_image(image,hashed_image) 

    return {"message": f"item received: {name}"}

def save_items_in_file(name,category,image_name):
    new_item = {"name": name, "category": category, "image_name": image_name}
    if os.path.exists(items_file):
        with open(items_file,'r') as f:
            now_data = json.load(f)
        if new_item in now_data["items"]:
            return 
        else:
            now_data["items"].append(new_item)
        with open(items_file, 'w') as f:
            json.dump(now_data, f, indent=2)
    else:
        first_item = {"items": [new_item]}
        with open(items_file, 'w') as f:
            json.dump(first_item, f, indent=2)

def save_image(image,jpg_hashed_image_name):
    imagefile = image.file.read()
    image = images / jpg_hashed_image_name
    with open(image, 'wb') as f:
        f.write(imagefile)
    return

def get_hash(image):
    hash = hashlib.sha256(image.encode()).hexdigest()
    return hash+".jpg"

@app.get("/items")
def get_items():
    with open(items_file) as f:
        items = json.load(f)
    return items

@app.get("/items/{item_id}")
def get_items_item(item_id: int):
    with open(items_file) as f:
        items = json.load(f)
    if item_id < 0 or item_id > len(items["items"]):
        return {"message": "item not found"}
    return items["items"][item_id-1]

@app.get("/image/{image_name}")
async def get_image(image_name):
    # Create image path
    image = images / image_name

    if not image_name.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)

