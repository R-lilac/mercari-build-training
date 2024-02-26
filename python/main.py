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
# ロギングの設定
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

# ルートエンドポイントの定義
@app.get("/")
def root():
    return {"message": "Hello, world!"}

# アイテムの追加をするエンドポイント
@app.post("/items")
# アイテムの追加、画像の保存
def add_item(name: str = Form(...),category: str = Form(...),image: UploadFile = File(...)):
    # アイテムの各情報をログに記録
    logger.info(f"Receive item: {name}")
    logger.info(f"Receive item: {category}")
    logger.info(f"Receive item: {image}")

    image_name = image.filename
    hashed_image = get_hash(image_name)

    save_items_in_file(name,category,hashed_image) 
    save_image(image,hashed_image) 

    return {"message": f"item received: {name}"}

# アイテム情報をJSONファイルに保存
def save_items_in_file(name,category,image_name):
    new_item = {"name": name, "category": category, "image_name": image_name}
    if items_file.exists(items_file):
        with open(items_file,'r') as f:
            current_data = json.load(f)
        if new_item in current_data["items"]:
            return 
        else:
            current_data["items"].append(new_item)
        with open(items_file, 'w') as f:
            json.dump(current_data, f, indent=2)
    else:
        first_item = {"items": [new_item]}
        with open(items_file, 'w') as f:
            json.dump(first_item, f, indent=2)

# アップロードされた画像を保存
def save_image(image,jpg_hashed_image_name):
    imagefile = image.file.read()
    image = images / jpg_hashed_image_name
    with open(image, 'wb') as f:
        f.write(imagefile)
    return

# 文字列からSHA-256ハッシュを生成
def get_hash(image):
    hash = hashlib.sha256(image.encode()).hexdigest()
    return hash+".jpg"

# アイテムのリストをJSONで返すエンドポイント
@app.get("/items")
# JSONファイルからアイテムのリストを取得
def get_items():
    with open(items_file) as f:
        items = json.load(f)
    return items

# 特定のアイテムを取得するエンドポイント
@app.get("/items/{item_id}")
# 特定のアイテムを取得する関数
def get_items_item(item_id: int):
    with open(items_file) as f:
        items = json.load(f)
    if item_id < 0 or item_id > len(items["items"]):
        return {"message": "item not found"}
    return items["items"][item_id-1]

# 画像を取得するエンドポイント
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

