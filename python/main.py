import os
import logging
import pathlib
import json
import requests
import hashlib
import sqlite3

from fastapi import FastAPI, Form, HTTPException,File, UploadFile
from fastapi.responses import FileResponse ,JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
# ロギングの設定
logger = logging.getLogger("uvicorn")
# logger level INFO->DEBUG
logger.level = logging.DEBUG

images = pathlib.Path(__file__).parent.resolve() / "images"
items_file = pathlib.Path(__file__).parent.resolve() / "items.json"
sqlite3_file = pathlib.Path(__file__).parents[1].resolve()/"db"/"mercari.sqlite3"

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

    # save_items_in_file(name,category,hashed_image) #items.jsonにitemを保存
    save_items_to_sqlite3(name,category,hashed_image) #mercari.sqlite3にitemを保存
    save_image(image,hashed_image) 

    return {"message": f"item received: {name}"}

# アイテム情報をJSONファイルに保存
def save_items_in_file(name,category,image_name):
    new_item = {"name": name, "category": category, "image_name": image_name}
    if items_file.exists():
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

# アイテム情報をmercari.sqlite3に保存
def save_items_to_sqlite3(name, category, image_name):
    con = sqlite3.connect(sqlite3_file)
    cur = con.cursor()

    cur.execute("SELECT id FROM categories_table WHERE name = ?", (category,))
    category_check = cur.fetchone()
    if not category_check:
        logger.debug(f"The item's category doesn't exist in the categories_table yet. ")
        try:
            cur.execute("INSERT INTO categories_table(name) VALUES (?)", (category,) )
            con.commit()
            category_check = cur.lastrowid

        except sqlite3.Error as e:
            con.rollback()
            logger.error(f"エラーが発生したためロールバック: {e}")
    else:
        category_id = category_check[0]

    cur.execute("SELECT id FROM items_table WHERE name = ?", (name,))
    exist_check = cur.fetchone()
    if not exist_check:
        logger.debug(f"The item doesn't exist yet. ")
        try:
            cur.execute("INSERT INTO items_table(name, category_id, image_name) VALUES (?, ?, ?)", (name, category_id, image_name) )
            con.commit()

        except sqlite3.Error as e:
            con.rollback()
            logger.error(f"エラーが発生したためロールバック: {e}")
    con.close()

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

# category_id :int から対応する category :string を返す
def get_category_name(category_id):
    con = sqlite3.connect(sqlite3_file)
    cur = con.cursor()
    cur.execute("SELECT name FROM categories_table WHERE id = ?", (category_id,))
    category = cur.fetchone()
    cur.close()
    con.close()
    return category[0]

# アイテムのリストを返すエンドポイント
@app.get("/items")
# アイテムのリストを取得
def get_items():
    #items = get_items_from_json()    # items.json
    items = get_items_from_sqlite3()    # mercari.sqlite3
    return items

# items.jsonからアイテムのリストを取得
def get_items_from_json():
    with open(items_file) as f:
        items = json.load(f)
    return items

# mercari.sqlite3からアイテムのリストを取得
def get_items_from_sqlite3():
    con = sqlite3.connect(sqlite3_file)
    cur = con.cursor()
    cur.execute('SELECT * FROM items_table')
    items = cur.fetchall()
    items_list = {"items":[]}
    for i in range(len(items)):
        category_id = items[i][2]
        category = get_category_name(category_id)
        item = {"name":items[i][1], "category":category, "image_name":items[i][3]}
        items_list["items"].append(item)
    cur.close()
    con.close()
    return items_list


# 特定のアイテムの詳細を取得するエンドポイント
@app.get("/items/{item_id}")
# 特定のアイテムの詳細を取得する関数
def get_particular_item(item_id: int):
    #item = get_particular_item_from_json(item_id)     # items.json
    item = get_particular_item_from_sqlite3(item_id)     # mercari.sqlite3
    return item

# items.jsonに登録されたアイテムの詳細を取得
def get_particular_item_from_json(item_id: int):
    with open(items_file) as f:
        items = json.load(f)
    if item_id > len(items["items"]):
        return {"message": "item not found"}
    return items["items"][item_id-1]

# mercari.sqlite3に登録されたアイテムの詳細を取得
def get_particular_item_from_sqlite3(item_id: int):
    con = sqlite3.connect(sqlite3_file)
    cur = con.cursor()
    cur.execute('SELECT * FROM items_table')
    items = cur.fetchall()

    if item_id > len(items):
        return {"message": "item not found"}

    category_id = items[item_id-1][2]
    cur.execute("SELECT name FROM categories_table WHERE id = ?", (category_id,))
    category = cur.fetchone()
    item = {"name":items[item_id-1][1], "category":category[0], "image_name":items[item_id-1][3]}

    return item

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

# アイテムを検索するエンドポイント
@app.get("/search")
def search_items(keyword: str):
    logger.debug(f"Search items name : {keyword}")
    con = sqlite3.connect(sqlite3_file)
    cur = con.cursor()
    items = cur.execute("SELECT * FROM items_table WHERE name LIKE ?", (f"%{keyword}%",))
    items_list_with_specified_keyword={"items":[]}
    if not items:
        return logger.debug(f"The name's items not found: {keyword}")
    items = cur.fetchall()
    for i in range(len(items)):
        category_id = items[i][2]
        category = get_category_name(category_id)
        item_with_specified_keyword = {"name":items[i][1], "category":category, "image_name":items[i][3]}
        items_list_with_specified_keyword["items"].append(item_with_specified_keyword)

    cur.close()
    con.close()
    return items_list_with_specified_keyword