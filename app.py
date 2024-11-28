import json
import math

from bson import ObjectId
from flask import Flask, request, jsonify, Blueprint, send_from_directory, render_template

from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler # type: ignore
from sklearn.neighbors import NearestNeighbors # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_restful import Api, Resource
from flasgger import Swagger
# import schedule
# import time
from datetime import datetime
# from random import random
# Khởi tạo Flask Server Backend
load_dotenv()
app = Flask(__name__)
api = Api(app)
# Apply Flask CORS
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
# app.config['UPLOAD_FOLDER'] = "static"

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
            user.insert_one({"email": os.environ.get("EMAIL_ADMIN"), "password": generate_password_hash(os.environ.get("PASSWORD")),'role':"admin","username":"admin","createdAt": datetime.utcnow()})
            return jsonify(status="success", collections="account admin added"), 200
    except Exception as e:
        return jsonify(status="error", message=str(e)), 500
@app.route("/login", methods=["POST"])
def login():
        email = request.json.get('email')
        pwd = request.json.get('password')
        user = db.users
        result = user.find_one({"email": email})
        print(check_password_hash(result["password"], pwd))
        if result and  check_password_hash(result["password"], pwd):
            print("ok")
            access_token = create_access_token(identity=result["email"])
            return jsonify({
                "data": {"email":result["email"],"role":result["role"],"username":result["username"]},
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
            user.insert_one({"email":email,"username": user_name,'role':"user","password": password,"createdAt": datetime.utcnow()})
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
            typeoffood = request.form.get('typeofffood')  # Assuming this is an ID
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
                "calo": nutrition.get('calo', 0),
                "carbohydrate": nutrition.get('carbohydrate', 0),
                "protein": nutrition.get('protein', 0),
                "fat": nutrition.get('fat', 0),
                "fiber": nutrition.get('fiber', 0),
                "sodium": nutrition.get('sodium', 0),
                "vitaminc": nutrition.get('vitaminc', 0),
                "purine": nutrition.get('purine', 0),
                "sugar": nutrition.get('sugar', 0),
                "cholesterol": nutrition.get('cholesterol', 0),
                "iron": nutrition.get('iron', 0),
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

@app.route('/editFood/<food_id>', methods=['PUT'])
@jwt_required()
def edit_food(food_id):
    email = get_jwt_identity()
    if(email):
        try:
            # Lấy dữ liệu từ form-data
            title = request.form.get('name')
            type0fgroup = request.form.get('typeoffgroup')  # Assuming this is an ID
            typeoffood = request.form.get('typeofffood')  # Assuming this is an ID
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
            if description:
              
                nutrition = {}
                try:
                    for item in description.split(','):
                        key, value = item.split(':')
                        key_lower = key.strip().lower()
                        if key_lower in features:
                            nutrition[key_lower] = float(value.strip())
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
        # Calculate skip and fetch records
        skip = (page - 1) * limit
        dishes = db.Recipes.find().sort("createdAt", -1).skip(skip).limit(limit)
        
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
@app.route('/recommand_dishes', methods=['POST'])
def recommand_dishes():
    # Retrieve the status from the request JSON
    status = request.json.get('status')
    
    # Filter the data based on the status
    filtered_data = diseases[diseases['status'] == status]
    print(filtered_data)
    # If filtered_data is empty, return a response indicating no data found
    if filtered_data.empty:
        return jsonify({"message": "No data found for the given health condition."}), 404
    
    # Extract the nutritional values from the filtered data
    row = filtered_data.iloc[0]  # Assuming you only need the first matching record
    
    # Extract the necessary features from the row
    calories = row['Calo']
    carbs = row['Carbohydrate']
    protein = row['Protein']
    fat = row['Fat']
    fiber = row['Fiber']
    sodium = row['Sodium']
    vitamin_c = row['VitaminC']
    purine = row['Purine']
    sugar = row['Sugar']
    cholesterol = row['Cholesterol']
    iron = row['Iron']
    
    # Call the function to recommend dishes based on the extracted values
    recommended_dishes = recommend_dishes_by_health( calories, carbs, protein, fat, fiber, sodium,
        vitamin_c, purine, sugar, cholesterol, iron, status
    )
    
    # Return the recommended dishes as a JSON response
    return jsonify(recommended_dishes.to_dict(orient='records'))  # Converts DataFrame to list of dicts

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



@app.route("/change-password", methods=["put"])
@jwt_required()
def change_password():
    email = get_jwt_identity()
    if email:
        current_pwd = request.json.get('oldpas')
        new_pwd = request.json.get('newpass')
        
        # Tìm người dùng trong MongoDB
        user_collection = db.users
        user_data = user_collection.find_one({"email": email})

        if user_data and check_password_hash(user_data['password'], current_pwd):
            # Cập nhật mật khẩu mới
            new_hashed_pwd = generate_password_hash(new_pwd)
            user_collection.update_one(
                {"email": email},
                {"$set": {"password": new_hashed_pwd}}
            )
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, "error": "Current password is incorrect"})
    else:
        return jsonify({'success': False, "error": "Can't find user"})
    
@app.route("/changeUsername", methods=["Put"])
@jwt_required()
def change_username():
    email = get_jwt_identity()
    if email:
        new_username = request.form.get('username')
        user_collection = db.users
        user_data = user_collection.find_one({"email": email})
        realPath=""
        if user_data:
            # Đường dẫn mặc định để lưu ảnh đại diện
            avatar_path = user_data.get('avatar', '')

            # Nếu có ảnh đại diện mới được tải lên
            if 'image' in request.files:
                current_avatar = request.files['image']
                filename = secure_filename(current_avatar.filename)
               
                if filename:
                    # Tạo đường dẫn lưu file
                    avatar_path = os.path.join(app.config['UPLOAD_FOLDER'],"uploads/users", filename)
                    current_avatar.save(avatar_path)
                    realPath='static/uploads/users/'+filename
            # Cập nhật tên người dùng và đường dẫn avatar mới
            user_collection.update_one(
                {"email": email},
                {"$set": {"username": new_username, "avatar": realPath}}
            )

            # Lấy dữ liệu mới nhất sau khi cập nhật
            updated_user = user_collection.find_one({"email": email})
            data = {
                "email": updated_user['email'],
                "success": 1,
                "role":updated_user["role"],
                "username": updated_user['username'],
                "avatar": updated_user['avatar'],
                "date": updated_user.get('date', str(datetime.now())),
                "access_token": "Bearer " + create_access_token(identity=updated_user['email'])
            }
            return jsonify({"data":data})
        else:
            return jsonify({'success': False, 'error': "User not found"})
    else:
        return jsonify({'success': False, 'error': "Email is required"})

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
def recommend_dishes_by_health(calories, carbs, protein, fat, fiber, Sodium, VitaminC, Purine, sugar, Cholesterol, iron, health_condition=''):
    data = pd.read_csv('Recipes.csv')
   
    # Convert categorical column 'Tình trạng sức khoẻ' to numerical
    # label_encoder = LabelEncoder()
    # data['status'] = label_encoder.fit_transform(data['status'])

    # Standardize the data
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data[features])

    # Initialize the KNN model
    knn_model = NearestNeighbors(n_neighbors=10, algorithm="brute", metric="cosine")
    knn_model.fit(data_scaled)  # Fit the model on the entire dataset
    input_features_df = pd.DataFrame([[calories, carbs, protein, fat, fiber, Sodium, VitaminC, Purine, sugar, Cholesterol, iron]], columns=features)
    distances, indices = knn_model.kneighbors(input_features_df)

    # Retrieve the recommended dishes
    recommended_dishes = data.iloc[indices[0]]

    # Select relevant columns for the output
    return recommended_dishes[['title','type0fgroup','typeoffood']]

    
def backup_to_csv():
    # Lấy tất cả dữ liệu từ collection
    
    data = db.Recipes.find()
    
    # Chuyển dữ liệu từ MongoDB sang DataFrame của pandas
    df = pd.DataFrame(list(data))
    
    # Loại bỏ trường `_id` khỏi DataFrame (vì MongoDB sẽ tự động thêm trường này)
    # if '_id' in df.columns:
    #     df = df.drop(columns=['_id'])
    
    # Đặt tên file với thời gian hiện tại
    filename = "Recipes.csv"
    
    # Lưu DataFrame vào file CSV
    df.to_csv(filename, index=False)
    print(f"Backup saved as {filename}")

# Lập lịch sao lưu hàng ngày (ví dụ vào lúc 2:00 AM)
# schedule.every().day.at("02:00").do(backup_to_csv)
# schedule.every(10).minutes.do(backup_to_csv)
# def run():
#     while True:
#         schedule.run_pending()
#         time.sleep(1)
if __name__ == '__main__':
    # test_connection()
    # from threading import Thread
    # flask_thread = Thread(target=lambda: app.run(debug=True, use_reloader=False))
    # flask_thread.start()
    
    # # Chạy scheduler
    # run()
    app.run(host="0.0.0.0", port=os.environ.get(
        "FLASK_PORT"), debug=True)

