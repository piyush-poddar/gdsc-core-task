import os
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from models import File, User, db
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_socketio import SocketIO, send
from flask_cors import CORS

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['JWT_SECRET_KEY'] = 'jwt_secret_key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=60)

db.init_app(app)
jwt = JWTManager(app)

CORS(app, resources={r"/*": {"origins": "*"}})

socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")


# this one deprecated
# @app.before_first_request
# def create_tables():
#     app.before_first_request_funcs[None].remove(create_tables)
#     db.create_all()

# Initialize DB
with app.app_context():
    db.create_all()

# 1. CRUD APIs for File Storage

@app.route('/files', methods=['POST'])
@jwt_required()
def upload_file():
    user_id = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    new_file = File(filename=filename, user_id=user_id)
    db.session.add(new_file)
    db.session.commit()

    return jsonify(new_file.file_metadata()), 201

@app.route('/files/<int:file_id>', methods=['GET'])
@jwt_required()
def get_file(file_id):
    file_record = File.query.get_or_404(file_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], file_record.filename)

@app.route('/files/<int:file_id>', methods=['PUT'])
@jwt_required()
def update_file(file_id):
    user_id = get_jwt_identity()
    file_record = File.query.get_or_404(file_id)
    if file_record.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    
    # Remove old file
    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.filename)
    if os.path.exists(old_file_path):
        os.remove(old_file_path)
    
    # Save new file
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    file_record.filename = filename
    db.session.commit()
    
    return jsonify(file_record.file_metadata()), 200

@app.route('/files/<int:file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    user_id = get_jwt_identity()
    file_record = File.query.get_or_404(file_id)
    if file_record.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.session.delete(file_record)
    db.session.commit()

    return jsonify({"message": "File deleted successfully"}), 200

# 2. Authentication APIs using JWT

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    if 'username' not in data or 'password' not in data:
        return jsonify({"error": "Missing username or password"}), 400

    username = data['username']
    password = data['password']

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "User already exists"}), 400
    
    new_user = User(username=username)
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
    
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200

@app.route('/auth/logout', methods=['GET'])
@jwt_required()
def logout():
    return jsonify({"message": "Logged out"}), 200

# 3. Real-time Communication (SocketIO)

@socketio.on('message')
def handle_message(msg):
    print(f"Message: {msg}")
    send(msg, broadcast=True)

if __name__ == '__main__':
    #socketio.run(app, debug=True)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
