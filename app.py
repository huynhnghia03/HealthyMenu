
from mailbox import Message
import math
import random

from bson import ObjectId
from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import pandas as pd
from sklearn.preprocessing import  StandardScaler # type: ignore
from sklearn.neighbors import NearestNeighbors # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_restful import Api
from datetime import datetime
load_dotenv()
app = Flask(__name__)
api = Api(app)
# Apply Flask CORS
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
# app.config['UPLOAD_FOLDER'] = "static"

# Cấu hình Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')  # Email của bạn
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')  # Mật khẩu ứng dụng email
mail = Mail(app)

app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
mongo = PyMongo(app)
client = MongoClient(os.environ.get("MONGO_URI"))
db = client['HealthyMenu']
app.secret_key = os.environ.get("FLASK_SECRET")
app.config['JWT_SECRET_KEY'] = os.environ.get("JWT_SECRET_KEY")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)


# Select the relevant features
features = ['Calo', 'Carbohydrate', 'Protein', 'fat', 'fiber', 'Sodium', 'VitaminC', 'Purine', 'sugar', 'Cholesterol', 'iron']
diseases = pd.read_csv('diseases.csv')

app.config['UPLOAD_FOLDER'] = "static"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# # Tạo thư mục nếu chưa tồn tại
# if not os.path.exists(UPLOAD_FOLDER):
#     os.makedirs(UPLOAD_FOLDER)
# để xem luôn cái app cho xong

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
 
@app.route("/test_connection", methods=["GET"])
def test_connection():
    try:
        # Try to retrieve the list of collections as a basic test
        user = db.users
        result =user.find_one({"email":os.environ.get("EMAIL_ADMIN")})
        if(result):
            return jsonify(status="success", collections="admin exited"), 200
        else:
            user.insert_one({"email": os.environ.get("EMAIL_ADMIN"), "password": generate_password_hash(os.environ.get("PASSWORD")),'role':"admin","username":"admin","createdAt": datetime.utcnow(),"new":True,"avatar":""})
            return jsonify(status="success", collections="account admin added"), 200
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500
@app.route("/login", methods=["POST"])
def login():
        email = request.json.get('email')
        pwd = request.json.get('password')
        user = db.users
        result = user.find_one({"email": email})
        if result and  check_password_hash(result["password"], pwd):
            print("ok")
            access_token = create_access_token(identity=result["email"])
            if(result['new']):
                return jsonify({
                    "data": {
                        
                        "email":result["email"],
                        "role":result["role"],
                        "username":result["username"],
                         "new":result["new"],
                         "avatar":result['avatar']
                        },
                    "success":1,
                    "err":None,
                    "message": "Login Success",
                    "acesstoken":"Bearer "+access_token})
            else:
                return jsonify({
                    "data": {
                        "email":result["email"],
                        "role":result["role"],
                        "username":result["username"],
                         "weight":result["weight"],
                         "gender":result["gender"],
                          "height":result["height"],
                           "statusHealth":result["statusHealth"],
                            "new":result["new"],
                             "avatar":result['avatar']
                        },
                    "success":1,
                    "err":None,
                    "message": "Login Success",
                    "acesstoken":"Bearer "+access_token})
        else:
            return jsonify({ "success":0,
                "err":None,
                "message": "Email or password incorrect",})

@app.route("/register", methods=["POST"])
def register():
        email = request.json.get("email")
        password = generate_password_hash(request.json.get('password'))
        date = datetime.now()
        user = db.users
        result = user.find_one({"email": email})
        if result:
            return jsonify({ "success":0,
                "err":None,
                "message": "Account exited",})
        else:
            user_name = email.split('@')[0]
            user.insert_one({"email":email,"username": user_name,'role':"user","password": password,"createdAt": datetime.utcnow(),"new":True,"avatar":""})
            return jsonify({"success":1,
                "err":None,
                "message": "Account was created successfully",})
@app.route('/createFood', methods=['POST'])
@jwt_required()
def create_food():
    email = get_jwt_identity()
    if(email):
        try:
            # Lấy dữ liệu từ form-data
            title = request.form.get('name')
            type0fgroup = request.form.get('type0fgroup')  # Assuming this is an ID
            typeoffood = request.form.get('typeoffood')  # Assuming this is an ID
            description = request.form.get('description')
            ingredient = request.form.get('ingredient')
            methob = request.form.get('methob')
            image_file = request.files.get('image')
            nutrition = {}
            if description:
                try:
                    for item in description.split(','):
                        key, value = item.split(':')
                        nutrition[key.strip().lower()] = float(value.strip())
                except ValueError:
                    return jsonify({"error": "Dữ liệu mô tả dinh dưỡng không hợp lệ!"}), 400
            # Kiểm tra các trường bắt buộc
            if not title or not type0fgroup or not typeoffood :
                return jsonify({"error": "Thiếu thông tin bắt buộc!"}), 400

            # Kiểm tra định dạng file ảnh
            if not allowed_file(image_file.filename):
                return jsonify({"error": "Định dạng ảnh không được hỗ trợ!"}), 400

            # Lưu ảnh với tên an toàn
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'],"uploads/dishes", filename)
            image_file.save(image_path)
            realFilePath = 'static/uploads/dishes/'+filename
            # Tạo món ăn mới
            # new_food = {
            #     "title": title,
            #     "type0fgroup": type0fgroup,  # Lưu ID của nhóm loại
            #     "typeoffood": typeoffood,  # Lưu ID của loại món ăn
            #     "description": description,
            #     "ingredient": ingredient,
            #     "methob": methob,
            #     "image_path": realFilePath,
            #     "createdAt": datetime.utcnow()
            # }
            new_food = {
                "title": title,
                "type0fgroup": type0fgroup,
                "typeoffood": typeoffood,
                "Calo": nutrition.get('Calo'),
                "Carbohydrate": nutrition.get('Carbohydrate'),
                "Protein": nutrition.get('Protein'),
                "fat": nutrition.get('fat'),
                "fiber": nutrition.get('fiber'),
                "Sodium": nutrition.get('Sodium'),
                "VitaminC": nutrition.get('VitaminC'),
                "Purine": nutrition.get('Purine'),
                "sugar": nutrition.get('sugar'),
                "Cholesterol": nutrition.get('Cholesterol'),
                "iron": nutrition.get('iron'),
                "ingredient": ingredient,
                "methob": methob,
                "description": description,
                "image_path": realFilePath,
                "createdAt": datetime.utcnow()
            }
            # Thêm món ăn vào MongoDB
            result = db.Recipes.insert_one(new_food)
            new_food["_id"] = str(result.inserted_id)
            backup_to_csv()
            return jsonify({
                "message": "Tạo món ăn thành công!",
                "food": new_food
            }), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
            return jsonify({
            "message":"Unauthoried"
            
            })
@app.route('/loveFood', methods=['POST'])
@jwt_required()
def love_food():
    email = get_jwt_identity()
    if(email):
        try:
            data = request.form
            food_id = data.get("food_id")
            print(email)
            if not food_id:
                return jsonify({"error": "food_id is required"}), 400
            
            # Kiểm tra người dùng tồn tại không
            user = db.users.find_one({"email": email})
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Kiểm tra món ăn đã tồn tại trong bảng Favourites chưa
            existing_favourite = db.Favourites.find_one({"user_email": email, "food_id": food_id})
            if existing_favourite:
                return jsonify({"message": "This food is already in favorites"}), 200
            
            # Thêm món ăn yêu thích vào bảng Favourites
            new_favourite = {
                "user_email": email,
                "food_id": food_id,
                "created_at": datetime.utcnow()  # Thời gian thêm vào danh sách yêu thích
            }
            db.Favourites.insert_one(new_favourite)
            
            return jsonify({
                "message": "Food added to favorites successfully!",
                "food_id": food_id
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
            return jsonify({
            "message":"Unauthoried"
            
            })
@app.route('/favorites', methods=['GET'])
@jwt_required()
def get_favorites():
    email = get_jwt_identity()
    if email:
        try:
            # Lấy danh sách món ăn yêu thích từ bảng Favourites
            favorites = db.Favourites.find({"user_email": email})
            favorite_list = []

            for fav in favorites:
                # Lấy chi tiết món ăn từ bảng Recipes
                recipe = db.Recipes.find_one({"_id": ObjectId(fav["food_id"])})
                print(recipe)
                print(fav["food_id"])
                # Thêm thông tin chi tiết món ăn vào danh sách
                favorite_list.append({
                    "_id": fav["food_id"],
                    "created_at": fav["created_at"],
                    "title": recipe["title"],
                    "description": recipe.get("description", ""),
                    "image_path": recipe.get("image_path", ""),
                    "type0fgroup": recipe.get("type0fgroup", ""),
                    "typeoffood": recipe.get("typeoffood", ""),
                    "ingredient": recipe.get("ingredient", ""),
                    "methob": recipe.get("methob", "")
                  
                })
            
            return jsonify({
                "message": "Favorites retrieved successfully!",
                "favorites": favorite_list
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"message": "Unauthorized"}), 401
@app.route('/checkLoveDish/<food_id>', methods=['GET'])
@jwt_required()
def check_love(food_id):
    email = get_jwt_identity()
    if email:
        try:
            # Lấy danh sách món ăn yêu thích từ bảng Favourites
            isLove = db.Favourites.find_one({"user_email": email,"food_id":food_id})
            print(isLove)
            if(isLove):
                return jsonify({
                    "message": "Dish was added in favourite love list!",
                    "love": True
                }), 200
            return jsonify({
                    "message": "Dish doesnt add in favourite love list!",
                    "love": False
                }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"message": "Unauthorized"}), 401

@app.route('/remove_favorite/<food_id>', methods=['DELETE'])
@jwt_required()
def remove_favorite(food_id):
    email = get_jwt_identity()
    if email:
        try:
            if not food_id:
                return jsonify({"error": "food_id is required"}), 400
            
            # Xóa món ăn khỏi bảng Favourites
            result = db.Favourites.delete_one({"user_email": email, "food_id": food_id})
            if result.deleted_count == 0:
                return jsonify({"message": "Food not found in favorites"}), 404
            
            return jsonify({
                "message": "Food removed from favorites successfully!",
                "food_id": food_id
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"message": "Unauthorized"}), 401

@app.route('/editFood/<food_id>', methods=['PUT'])
@jwt_required()
def edit_food(food_id):
    email = get_jwt_identity()
    if(email):
        try:
            # Lấy dữ liệu từ form-data
            title = request.form.get('name')
            type0fgroup = request.form.get('type0fgroup')  # Assuming this is an ID
            typeoffood = request.form.get('typeoffood')  # Assuming this is an ID
            description = request.form.get('description')
            ingredient = request.form.get('ingredient')
            methob = request.form.get('methob')
            image_file = request.files.get('image')

            # Tạo đối tượng cập nhật
            update_data = {}

            if title:
                update_data["title"] = title
            if type0fgroup:
                update_data["type0fgroup"] = type0fgroup
            if typeoffood:
                update_data["typeoffood"] = typeoffood
            if description:
                update_data["description"] = description
            if ingredient:
                update_data["ingredient"] = ingredient
            if methob:
                update_data["methob"] = methob
            update_data["updatedAt"] =datetime.utcnow()
            
            if description != "null":
                print(description!=None)
                nutrition = {}
                try:
                    for item in description.split(','):
                       
                        key, value = item.split(':')
                        print(value)
                        if key in features:
                            nutrition[key] = float(value.strip())
                except ValueError:
                    return jsonify({"error": "Dữ liệu mô tả dinh dưỡng không hợp lệ!"}), 400

                update_data.update(nutrition)
            # Nếu có ảnh mới, xử lý lưu ảnh
            if image_file:
                if not allowed_file(image_file.filename):
                    return jsonify({"error": "Định dạng ảnh không được hỗ trợ!"}), 400

                # Lưu ảnh với tên an toàn
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'],"uploads/dishes", filename)
                image_file.save(image_path)
                realFilePath = 'static/uploads/dishes/'+filename
                update_data["image_path"] = realFilePath

            # Kiểm tra nếu có dữ liệu cần cập nhật
            if not update_data:
                return jsonify({"error": "Không có thông tin để cập nhật!"}), 400

            # Cập nhật món ăn trong MongoDB
            result = db.Recipes.update_one({"_id": ObjectId(food_id)}, {"$set": update_data})

            if result.matched_count == 0:
                return jsonify({"error": "Không tìm thấy món ăn để cập nhật!"}), 404

            backup_to_csv()
            return jsonify({"message": "Cập nhật món ăn thành công!"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
            return jsonify({
            "message":"Unauthoried"
            
            })

@app.route('/getFood/<food_id>', methods=['GET'])
@jwt_required()
def get_food(food_id):
    email = get_jwt_identity()
    if(email):
        try:
            # Tìm món ăn trong MongoDB theo food_id
            food_item = db.Recipes.find_one({"_id": ObjectId(food_id)})

            if not food_item:
                return jsonify({"error": "Không tìm thấy món ăn!"}), 404

            # Chuyển đổi dữ liệu từ MongoDB thành dictionary và loại bỏ trường '_id'
            food_data = {
                "food_id": str(food_item["_id"]),
                "title": food_item.get("title"),
                "type0fgroup": food_item.get("type0fgroup"),
                "typeoffood": food_item.get("typeoffood"),
                "description": food_item.get("description"),
                "ingredient": food_item.get("ingredient"),
                "methob": food_item.get("methob"),
                "image_path": food_item.get("image_path")
            }

            return jsonify({"data":food_data}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
            return jsonify({
            "message":"Unauthoried"
            
            })

@app.route('/deleteFood/<food_id>', methods=['DELETE'])
@jwt_required()
def delete_food(food_id):
    email = get_jwt_identity()
    if(email):
        try:
            # Xóa món ăn từ MongoDB dựa trên ID
            result = db.Recipes.delete_one({"_id": ObjectId(food_id)})

            if result.deleted_count == 0:
                return jsonify({"error": "Không tìm thấy món ăn để xóa!"}), 404

            backup_to_csv()
            return jsonify({"message": "Xóa món ăn thành công!"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
            return jsonify({
            "message":"Unauthoried"
            
            })

@app.route('/dishes', methods=['GET'])
@jwt_required()
def get_dishes():
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 12))
        search = request.args.get('searchDish', '')
        # Calculate skip and fetch records
        skip = (page - 1) * limit
       # Nếu 'searchDish' có giá trị, thực hiện tìm kiếm, nếu không thì bỏ qua tìm kiếm
        if search:
            dishes = db.Recipes.find({"title": {"$regex": search, "$options": "i"}}).sort("createdAt", -1).skip((page - 1) * limit).limit(limit)
        else:
            dishes = db.Recipes.find().sort("createdAt", -1).skip((page - 1) * limit).limit(limit)
        
        # Get total records
        total_dishes = db.Recipes.count_documents({})
        total_pages = math.ceil(total_dishes / limit)
        
        # Prepare response
        dish_list = [
            {
                "food_id": str(dish["_id"]),
                "title": dish["title"],
                "description": dish.get("description", ""),
                "image_path": dish.get("image_path", ""),
                "type0fgroup": dish.get("type0fgroup", ""),
                "typeoffood": dish.get("typeoffood", ""),
                "ingredient": dish.get("ingredient", ""),
                "methob": dish.get("methob", "")
            } for dish in dishes
        ]
        
        return jsonify({
            "total": total_dishes,
            "page": page,
            "limit": limit,
            "totalPages": total_pages,
            "dishes": dish_list
        })
    except Exception as e:
        return jsonify({"message": "Internal Server Error", "error": str(e),"auth":False}), 500


@app.route('/recommand_dishes', methods=['GET'])
@jwt_required()
def recommand_dishes():
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        # Retrieve the user data from the database based on email
        user = db.users.find_one({"email": email})
        # search = request.args.get('searchDish', '')
        par = request.args.get('typeOfGroup', '')
        print(par)
        # Get the user's health conditions
        user_health_conditions = user.get("statusHealth", [])
        print(user)
        if not user_health_conditions:
            return jsonify({"message": "No health conditions found for the user."}), 400
        
        # Filter the diseases dataframe based on the user's health conditions
        filtered_data = diseases[diseases['status'].isin(user_health_conditions)]
        # print(filtered_data)
        if filtered_data.empty:
            return jsonify({"message": "No data found for the given health conditions."}), 404
        
        # Extract the nutritional values from the first matching row
        row = filtered_data.iloc[0]
        print(row)
        nutrition_data = {
            "calories": row['Calo'],
            "carbs": row['Carbohydrate'],
            "protein": row['Protein'],
            "fat": row['Fat'],
            "fiber": row['Fiber'],
            "Sodium": row['Sodium'],
            "VitaminC": row['VitaminC'],
            "Purine": row['Purine'],
            "sugar": row['Sugar'],
            "Cholesterol": row['Cholesterol'],
            "iron": row['Iron'],
        }
        
        # Call the function to recommend dishes
        recommended_dishes = recommend_dishes_by_health(**nutrition_data, typeOfGroup=par)
        
        # Extract list of IDs from the recommended dishes
        recommended_ids = [ObjectId(dish['_id']) for dish in recommended_dishes.to_dict(orient='records')]
        # print("Recommended IDs:", recommended_ids)  # Debug
        
        # Find the documents in the database that match these IDs
        dishes_cursor = db.Recipes.find({"_id": {"$in": recommended_ids}})
        dishes = list(dishes_cursor)  # Convert cursor to list

        # Convert ObjectId to string for JSON serialization
        for dish in dishes:
            dish['_id'] = str(dish['_id'])
        
        # Return the dishes to the user
        return jsonify({"data": dishes})
        
    except Exception as e:
        return jsonify({"success": 0, "message": "Server error", "error": str(e)}), 500

@app.route('/user_detail/<user_id>', methods=['GET'])
@jwt_required()
def get_user_detail(user_id):
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        # Kiểm tra tính hợp lệ của user_id
        if not ObjectId.is_valid(user_id):
            return jsonify({"message": "Invalid user ID"}), 400

        # Lấy thông tin user từ MongoDB
        user = db.users.find_one({"_id": ObjectId(user_id)})

        if not user:
            return jsonify({"message": "User not found"}), 404

        # Chuẩn bị dữ liệu trả về
        user_detail = {
            "user_id": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "phoneNumber": user.get("phoneNumber"),
            "role": user.get("role"),
            "statusHealth": user.get("statusHealth"),
            "image": user.get("image"),
            "address": user.get("address"),
            "Country": user.get("Country"),
            "createdAt": user.get("createdAt"),
            "updatedAt": user.get("updatedAt")
        }

        return jsonify({"message": "User details retrieved successfully", "data": user_detail}), 200

    except Exception as e:
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500



@app.route("/update-user-info", methods=["PUT"])
@jwt_required()
def update_user_info():
    email = get_jwt_identity()
    if not email:
        return jsonify({'success': False, "error": "Email is required"}), 400

    # Lấy dữ liệu từ request
    current_pwd = request.form.get('oldpass')
    new_pwd = request.form.get('newpass')
    new_username = request.form.get('username')
    avatar_file = request.files.get('image')
    print(current_pwd,new_pwd,avatar_file)
    user_collection = db.users
    user_data = user_collection.find_one({"email": email})

    if not user_data:
        return jsonify({'success': False, 'error': "User not found"}), 404

    # Xử lý cập nhật mật khẩu
    if current_pwd and new_pwd:
        if check_password_hash(user_data['password'], current_pwd):
            # Hash mật khẩu mới và cập nhật
            new_hashed_pwd = generate_password_hash(new_pwd)
            user_collection.update_one(
                {"email": email},
                {"$set": {"password": new_hashed_pwd}}
            )
        else:
            return jsonify({'success': False, "error": "Current password is incorrect"}), 400

    # Xử lý cập nhật tên người dùng
    if new_username:
        user_collection.update_one(
            {"email": email},
            {"$set": {"username": new_username}}
        )

    # Xử lý cập nhật avatar
    real_path = user_data.get('avatar', '')
    if avatar_file:
        filename = secure_filename(avatar_file.filename)
        if filename:
            avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], "uploads/users", filename)
            avatar_file.save(avatar_path)
            real_path = 'static/uploads/users/' + filename
            user_collection.update_one(
                {"email": email},
                {"$set": {"avatar": real_path}}
            )

    # Lấy dữ liệu mới nhất sau khi cập nhật
    updated_user = user_collection.find_one({"email": email})
    data = {
        "email": updated_user['email'],
        "role": updated_user["role"],
        "username": updated_user['username'],
        "avatar": updated_user['avatar'],
        "date": updated_user.get('date', str(datetime.now())),
        "access_token": "Bearer " + create_access_token(identity=updated_user['email'])
    }
    return jsonify({"data": data}), 200

@app.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '')

        # Tính toán skip
        skip = (page - 1) * limit

        # Query tìm kiếm với search và phân trang
        query = {"$or": [
            {"username": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phoneNumber": {"$regex": search, "$options": "i"}}
        ]} if search else {}

        users = db.users.find(query).skip(skip).limit(limit).sort("createdAt", -1)

        # Lấy tổng số người dùng
        total_users = db.users.count_documents(query)
        total_pages = math.ceil(total_users / limit)

        # Chuẩn bị dữ liệu trả về
        user_list = [
            {
                "user_id": str(user["_id"]),
                "username": user.get("username"),
                "email": user.get("email"),
                "phoneNumber": user.get("phoneNumber"),
                "role": user.get("role"),
                "statusHealth": user.get("statusHealth"),
                "image": user.get("image"),
                "address": user.get("address"),
                "Country": user.get("Country"),
                "createdAt": user.get("createdAt"),
                "updatedAt": user.get("updatedAt"),
            } for user in users
        ]

        return jsonify({
            "message": "Users retrieved successfully",
            "total": total_users,
            "page": page,
            "limit": limit,
            "totalPages": total_pages,
            "users": user_list
        }), 200

    except Exception as e:
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500

@app.route('/infor_user', methods=['PUT'])
@jwt_required()
def infor_user():
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401
    data = request.json

    # Kiểm tra user_id hợp lệ
    try:
        user =  db.users.find_one({"email":email})
        if not user:
            return jsonify({"success": 0, "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"success": 0, "message": "Invalid user ID", "error": str(e)}), 400

    # Dữ liệu cần cập nhật
    update_data = {
        "gender": data.get("gender", user.get("gender")),
        "statusHealth": data.get("statusHealth", user.get("statusHealth")),
        "height": data.get("height", user.get("height")),
        "weight": data.get("weight", user.get("weight")),
        "updatedAt": datetime.utcnow(),
        "new":False
    }
    print(data)
    print(update_data)
    try:
        # Cập nhật thông tin người dùng
        res= db.users.update_one({"email": email}, {"$set": update_data})
        dataRes={
             "email":user["email"],
                        "role":user["role"],
                        "username":user["username"],
                        "gender": data.get("gender", user.get("gender")),
        "statusHealth": data.get("statusHealth", user.get("statusHealth")),
        "height": data.get("height", user.get("height")),
        "weight": data.get("weight", user.get("weight")),
        "updatedAt": datetime.utcnow(),
        "new":False,
                             "avatar":user['avatar']
                        
        }
        dataRes.update(update_data)
        print(res)
        return jsonify({"data":dataRes,"success": 1, "message": "User updated successfully"})
    except Exception as e:
        return jsonify({"success": 0, "message": "Server error", "error": str(e)}), 500

@app.route('/edit_user/<user_id>', methods=['PUT'])
def edit_user(user_id):
    data = request.json

    # Kiểm tra user_id hợp lệ
    try:
        user =  db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"success": 0, "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"success": 0, "message": "Invalid user ID", "error": str(e)}), 400

    # Dữ liệu cần cập nhật
    update_data = {
        "username": data.get("username", user.get("username")),
        "statusHealth": data.get("statusHealth", user.get("statusHealth")),
        "phoneNumber": data.get("phoneNumber", user.get("phoneNumber")),
        "role": data.get("role", user.get("role")),
        "image": data.get("image", user.get("image")),
        "address": data.get("address", user.get("address")),
        "Country": data.get("Country", user.get("Country")),
        "email": data.get("email", user.get("email")),
        "updatedAt": datetime.utcnow()
    }

    try:
        # Cập nhật thông tin người dùng
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        return jsonify({"success": 1, "message": "User updated successfully"})
    except Exception as e:
        return jsonify({"success": 0, "message": "Server error", "error": str(e)}), 500
@app.route('/delete_user/<user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        # Xác nhận user_id là ObjectId hợp lệ
        if not ObjectId.is_valid(user_id):
            return jsonify({"message": "Invalid user ID"}), 400

        # Thực hiện xóa user
        result = db.users.delete_one({"_id": ObjectId(user_id)})

        if result.deleted_count == 0:
            return jsonify({"message": "User not found"}), 404

        return jsonify({"message": "User deleted successfully"}), 200

    except Exception as e:
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500


@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = db.users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'Email not found'}), 404

    # Tạo mã xác minh 4 chữ số
    verification_code = random.randint(1000, 9999)

    # Lưu mã vào database
    db.users.update_one(
        {'email': email},
        {
            '$set': {
                'code': verification_code,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(minutes=2)
            }
        },
        upsert=True
    )

    # Gửi email
    try:
        msg = Message('Reset Password Code', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f'Your verification code is: {verification_code}. This code will expire in 2 minutes.'
        mail.send(msg)
        return jsonify({'message': 'Verification code sent successfully!'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500

@app.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    email = data.get('email')
    code = data.get('code')

    if not email or not code:
        return jsonify({'error': 'Email and code are required'}), 400

    # Kiểm tra mã trong database
    record = db.users.find_one({'email': email})
    if not record or record['code'] != int(code):
        return jsonify({'error': 'Invalid code'}), 400

    # Kiểm tra thời gian hết hạn
    if datetime.utcnow() > record['expires_at']:
        return jsonify({'error': 'Code expired'}), 400

    return jsonify({'message': 'Code verified successfully!'}), 200

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    new_password = generate_password_hash(data.get('newpass'))

    if not email or not new_password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Cập nhật mật khẩu mới
    db.users.update_one({'email': email}, {'$set': {'password': new_password}})
    return jsonify({'message': 'Password reset successfully!'}), 200

@app.route('/comments/<recipe_id>', methods=['GET'])
@jwt_required()
def get_comments(recipe_id):
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401
    comments = list(db.Comments.find({"recipeId": recipe_id}))
    for comment in comments:
        comment["_id"] = str(comment["_id"])
    return jsonify({"status": 200, "comments": comments}), 200

# 2. API Thêm bình luận mới
@app.route('/comments', methods=['POST'])
@jwt_required()
def add_comment():
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401
    data = request.get_json()
    recipe_id = data.get("recipeId")
    content = data.get("content")
    user = data.get("user", "Anonymous")
    emailUser = data.get("emailUser", "")
    if not recipe_id or not content:
        return jsonify({"status": 400, "message": "Recipe ID and content are required"}), 400

    comment = {
        "recipeId": recipe_id,
        "content": content,
        "user": user,
        "emailUser":emailUser,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    result = db.Comments.insert_one(comment)
    comment["_id"] = str(result.inserted_id)
    return jsonify({"status": 200, "comment": comment}), 200

# 3. API Chỉnh sửa bình luận
@app.route('/comments/<comment_id>', methods=['PUT'])
@jwt_required()
def edit_comment(comment_id):
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401
    data = request.json
    content = data.get("content")

    if not content:
        return jsonify({"status": 400, "message": "Content is required"}), 400

    updated = db.Comments.update_one(
        {"_id": ObjectId(comment_id)},
        {"$set": {"content": content, "updatedAt": datetime.utcnow()}}
    )

    if updated.modified_count == 1:
        return jsonify({"status": 200, "message": "Comment updated successfully"}), 200
    return jsonify({"status": 400, "message": "Failed to update comment"}), 400

# 4. API Xóa bình luận
@app.route('/comments/<comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    email = get_jwt_identity()
    if not email:
        return jsonify({"message": "Unauthorized"}), 401
    deleted = db.Comments.delete_one({"_id": ObjectId(comment_id)})
    if deleted.deleted_count == 1:
        return jsonify({"status": 200, "message": "Comment deleted successfully"}), 200
    return jsonify({"status": 400, "message": "Failed to delete comment"}), 400




def recommend_dishes_by_health(calories, carbs, protein, fat, fiber, Sodium, VitaminC, Purine, sugar, Cholesterol, iron, typeOfGroup):
    data = pd.read_csv('Recipes.csv')
   
    # Convert categorical column 'Tình trạng sức khoẻ' to numerical
    # label_encoder = LabelEncoder()
    # data['status'] = label_encoder.fit_transform(data['status'])
    filtered_data = data[data['type0fgroup'] == typeOfGroup]
    # Standardize the data
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(filtered_data[features])

    # Initialize the KNN model
    knn_model = NearestNeighbors(n_neighbors=30, algorithm="brute", metric="cosine")
    knn_model.fit(data_scaled)  # Fit the model on the entire dataset
    
    # filtered_data = data[data['status'] == health_condition]
    input_features_df = pd.DataFrame([[calories, carbs, protein, fat, fiber, Sodium, VitaminC, Purine, sugar, Cholesterol, iron]], columns=features)
    input_features_scaled = scaler.transform(input_features_df)
    distances, indices = knn_model.kneighbors(input_features_scaled)

    # Retrieve the recommended dishes
    recommended_dishes = filtered_data.iloc[indices[0]]

    # Select relevant columns for the output
    result = recommended_dishes[["_id"]]

    return result
def backup_to_csv():
    # Lấy tất cả dữ liệu từ collection
    
    data = db.Recipes.find()
    
    # Chuyển dữ liệu từ MongoDB sang DataFrame của pandas
    df = pd.DataFrame(list(data))
    
    # Đặt tên file với thời gian hiện tại
    filename = "Recipes.csv"
    
    # Lưu DataFrame vào file CSV
    df.to_csv(filename, index=False)
    print(f"Backup saved as {filename}")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=os.environ.get(
        "FLASK_PORT"), debug=True)

