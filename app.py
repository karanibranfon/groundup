import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest, NotFound
import jwt
from functools import wraps
import hashlib
import pydicom
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
app.config['MONGO_DB_NAME'] = os.getenv('MONGO_DB_NAME')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH'))
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

# CORS configuration
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# MongoDB connection
client = MongoClient(app.config['MONGO_URI'])
db = client[app.config['MONGO_DB_NAME']]

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Logging configuration
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Audit logging for HIPAA compliance
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler(os.getenv('AUDIT_LOG_FILE'))
audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)

# Authentication middleware
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode and verify token
            jwt_secret = os.getenv('JWT_SECRET_KEY')
            if not jwt_secret:
                return jsonify({'error': 'Server configuration error'}), 500
                
            payload = jwt.decode(
                token, 
                jwt_secret, 
                algorithms=['HS256']
            )
            current_user_id = payload['sub']
            
            # Get user from database
            user = db.users.find_one({'auth0_id': current_user_id})
            if not user:
                return jsonify({'error': 'User not found'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user_id, *args, **kwargs)
    return decorated

def log_audit_event(action, user_id, resource_type=None, resource_id=None, details=None):
    """Log audit events for HIPAA compliance"""
    audit_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'user_id': user_id,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'details': details
    }
    audit_logger.info(json.dumps(audit_data))

def validate_file_type(filename):
    """Validate uploaded file types for medical images"""
    allowed_extensions = {'dcm', 'jpg', 'jpeg', 'png', 'tiff', 'tif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def create_response(data=None, message=None, status_code=200):
    """Standardize API responses"""
    response = {}
    if data is not None:
        response['data'] = data
    if message is not None:
        response['message'] = message
    
    return jsonify(response), status_code

# Static routes (keeping existing functionality)
@app.route('/')
def landing_page():
    return send_from_directory ('.', 'index.html')

@app.route("/send_feedback")
def send_feedback():
    return render_template ("feedback.html")
    
@app.route("/help")    
def help():
    return send_from_directory ("help", "help.html")

@app.route("/pricing")
def pricing():
    return send_from_directory ("pricing", "pricing.html")
    
@app.route("/login")
def login():
    return render_template ("login.html")
    
@app.route("/whats_included")
def whats_included():
    return send_from_directory ("about", "whats_included.html")
    
@app.route("/about/testimonials")
def testimonials():
    return render_template ("testimonials.html")

# API Routes

# Authentication endpoints
@app.route('/api/auth/store-user', methods=['POST'])
@token_required
def store_user(current_user_id):
    try:
        user_data = request.get_json()
        
        # Validate required fields
        if not user_data.get('email'):
            return create_response(message='Email is required', status_code=400)
        
        # Check if user already exists
        existing_user = db.users.find_one({'email': user_data['email']})
        if existing_user:
            return create_response(message='User already exists', status_code=409)
        
        # Create new user
        new_user = {
            'auth0_id': current_user_id,
            'email': user_data['email'],
            'name': user_data.get('name', ''),
            'role': user_data.get('role', 'user'),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = db.users.insert_one(new_user)
        new_user['_id'] = str(result.inserted_id)
        
        log_audit_event('USER_CREATED', current_user_id, 'user', new_user['_id'])
        return create_response(data=new_user, message='User stored successfully', status_code=201)
        
    except Exception as e:
        logger.error(f"Error storing user: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/auth/profile', methods=['GET'])
@token_required
def get_user_profile(current_user_id):
    try:
        user = db.users.find_one({'auth0_id': current_user_id})
        if not user:
            return create_response(message='User not found', status_code=404)
        
        user['_id'] = str(user['_id'])
        del user['auth0_id']  # Don't expose internal ID
        
        return create_response(data=user)
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/auth/role', methods=['PUT'])
@token_required
def update_user_role(current_user_id):
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        if not new_role:
            return create_response(message='Role is required', status_code=400)
        
        result = db.users.update_one(
            {'auth0_id': current_user_id},
            {
                '$set': {
                    'role': new_role,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            return create_response(message='User not found', status_code=404)
        
        log_audit_event('ROLE_UPDATED', current_user_id, 'user', details={'new_role': new_role})
        return create_response(message='Role updated successfully')
        
    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

# Patient Management endpoints
@app.route('/api/patients', methods=['GET'])
@token_required
def get_patients(current_user_id):
    try:
        # Get query parameters for pagination and filtering
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '').strip()
        
        # Build query
        query = {}
        if search:
            query['$or'] = [
                {'name': {'$regex': search, '$options': 'i'}},
                {'patientId': {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}}
            ]
        
        # Get total count
        total_count = db.patients.count_documents(query)
        
        # Get patients with pagination
        patients = list(db.patients.find(query)
                        .skip((page - 1) * limit)
                        .limit(limit)
                        .sort('created_at', -1))
        
        # Convert ObjectId to string
        for patient in patients:
            patient['_id'] = str(patient['_id'])
            if 'created_at' in patient:
                patient['created_at'] = patient['created_at'].isoformat()
            if 'updated_at' in patient:
                patient['updated_at'] = patient['updated_at'].isoformat()
            if 'dateOfBirth' in patient and patient['dateOfBirth']:
                patient['dateOfBirth'] = patient['dateOfBirth'].isoformat()
        
        response_data = {
            'patients': patients,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }
        
        return create_response(data=response_data)
        
    except Exception as e:
        logger.error(f"Error getting patients: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/patients/<string:patient_id>', methods=['GET'])
@token_required
def get_patient(current_user_id, patient_id):
    try:
        patient = db.patients.find_one({'_id': patient_id})
        if not patient:
            return create_response(message='Patient not found', status_code=404)
        
        patient['_id'] = str(patient['_id'])
        if 'created_at' in patient:
            patient['created_at'] = patient['created_at'].isoformat()
        if 'updated_at' in patient:
            patient['updated_at'] = patient['updated_at'].isoformat()
        if 'dateOfBirth' in patient and patient['dateOfBirth']:
            patient['dateOfBirth'] = patient['dateOfBirth'].isoformat()
        
        # Get image count
        image_count = db.images.count_documents({'patientId': patient_id})
        patient['imageCount'] = image_count
        
        # Get last study date
        last_study = db.studies.find_one({'patientId': patient_id}, sort=[('createdAt', -1)])
        if last_study:
            patient['lastStudyDate'] = last_study['createdAt'].isoformat()
        
        return create_response(data=patient)
        
    except Exception as e:
        logger.error(f"Error getting patient: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/patients', methods=['POST'])
@token_required
def create_patient(current_user_id):
    try:
        patient_data = request.get_json()
        
        # Validate required fields
        if not patient_data.get('name'):
            return create_response(message='Patient name is required', status_code=400)
        
        if not patient_data.get('patientId'):
            return create_response(message='Patient ID is required', status_code=400)
        
        # Check if patient ID already exists
        existing_patient = db.patients.find_one({'patientId': patient_data['patientId']})
        if existing_patient:
            return create_response(message='Patient ID already exists', status_code=409)
        
        # Create new patient
        new_patient = {
            'name': patient_data['name'],
            'patientId': patient_data['patientId'],
            'dateOfBirth': None,
            'gender': None,
            'email': patient_data.get('email', ''),
            'phone': patient_data.get('phone', ''),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': current_user_id
        }
        
        # Handle optional fields
        if patient_data.get('dateOfBirth'):
            try:
                new_patient['dateOfBirth'] = datetime.fromisoformat(patient_data['dateOfBirth'])
            except ValueError:
                return create_response(message='Invalid date of birth format', status_code=400)
        
        if patient_data.get('gender') in ['M', 'F', 'O']:
            new_patient['gender'] = patient_data['gender']
        
        result = db.patients.insert_one(new_patient)
        new_patient['_id'] = str(result.inserted_id)
        new_patient['created_at'] = new_patient['created_at'].isoformat()
        new_patient['updated_at'] = new_patient['updated_at'].isoformat()
        if new_patient['dateOfBirth']:
            new_patient['dateOfBirth'] = new_patient['dateOfBirth'].isoformat()
        
        log_audit_event('PATIENT_CREATED', current_user_id, 'patient', new_patient['_id'], 
                       details={'patient_name': new_patient['name'], 'patient_id': new_patient['patientId']})
        return create_response(data=new_patient, message='Patient created successfully', status_code=201)
        
    except Exception as e:
        logger.error(f"Error creating patient: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/patients/<string:patient_id>', methods=['PUT'])
@token_required
def update_patient(current_user_id, patient_id):
    try:
        patient_data = request.get_json()
        
        # Check if patient exists
        existing_patient = db.patients.find_one({'_id': patient_id})
        if not existing_patient:
            return create_response(message='Patient not found', status_code=404)
        
        # Prepare update data
        update_data = {'updated_at': datetime.utcnow()}
        
        # Update allowed fields
        if 'name' in patient_data:
            update_data['name'] = patient_data['name']
        if 'email' in patient_data:
            update_data['email'] = patient_data['email']
        if 'phone' in patient_data:
            update_data['phone'] = patient_data['phone']
        if 'dateOfBirth' in patient_data:
            try:
                update_data['dateOfBirth'] = datetime.fromisoformat(patient_data['dateOfBirth'])
            except ValueError:
                return create_response(message='Invalid date of birth format', status_code=400)
        if 'gender' in patient_data and patient_data['gender'] in ['M', 'F', 'O']:
            update_data['gender'] = patient_data['gender']
        
        # Check for patient ID conflict if updating
        if 'patientId' in patient_data and patient_data['patientId'] != existing_patient['patientId']:
            # Check if new patient ID already exists
            id_conflict = db.patients.find_one({'patientId': patient_data['patientId']})
            if id_conflict:
                return create_response(message='Patient ID already exists', status_code=409)
            update_data['patientId'] = patient_data['patientId']
        
        result = db.patients.update_one(
            {'_id': patient_id},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return create_response(message='Patient not found', status_code=404)
        
        log_audit_event('PATIENT_UPDATED', current_user_id, 'patient', patient_id, 
                       details={'updated_fields': list(update_data.keys())})
        return create_response(message='Patient updated successfully')
        
    except Exception as e:
        logger.error(f"Error updating patient: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/patients/<string:patient_id>', methods=['DELETE'])
@token_required
def delete_patient(current_user_id, patient_id):
    try:
        # Check if patient exists
        patient = db.patients.find_one({'_id': patient_id})
        if not patient:
            return create_response(message='Patient not found', status_code=404)
        
        # Check if patient has studies
        study_count = db.studies.count_documents({'patientId': patient_id})
        if study_count > 0:
            return create_response(message='Cannot delete patient with existing studies', status_code=400)
        
        # Delete patient
        result = db.patients.delete_one({'_id': patient_id})
        
        if result.deleted_count == 0:
            return create_response(message='Patient not found', status_code=404)
        
        log_audit_event('PATIENT_DELETED', current_user_id, 'patient', patient_id,
                       details={'patient_name': patient['name'], 'patient_id': patient['patientId']})
        return create_response(message='Patient deleted successfully')
        
    except Exception as e:
        logger.error(f"Error deleting patient: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/patients/search', methods=['GET'])
@token_required
def search_patients(current_user_id):
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return create_response(message='Search query is required', status_code=400)
        
        # Build search query
        search_query = {
            '$or': [
                {'name': {'$regex': query, '$options': 'i'}},
                {'patientId': {'$regex': query, '$options': 'i'}},
                {'email': {'$regex': query, '$options': 'i'}},
                {'phone': {'$regex': query, '$options': 'i'}}
            ]
        }
        
        # Execute search
        patients = list(db.patients.find(search_query).limit(20).sort('name', 1))
        
        # Convert ObjectId to string
        for patient in patients:
            patient['_id'] = str(patient['_id'])
            if 'created_at' in patient:
                patient['created_at'] = patient['created_at'].isoformat()
            if 'updated_at' in patient:
                patient['updated_at'] = patient['updated_at'].isoformat()
        
        return create_response(data={'patients': patients})
        
    except Exception as e:
        logger.error(f"Error searching patients: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

# Study Management endpoints
@app.route('/api/studies', methods=['GET'])
@token_required
def get_studies(current_user_id):
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        patient_id = request.args.get('patientId')
        study_type = request.args.get('studyType')
        status = request.args.get('status')
        
        # Build query
        query = {}
        if patient_id:
            query['patientId'] = patient_id
        if study_type:
            query['studyType'] = study_type
        if status:
            query['status'] = status
        
        # Get total count
        total_count = db.studies.count_documents(query)
        
        # Get studies with pagination
        studies = list(db.studies.find(query)
                      .skip((page - 1) * limit)
                      .limit(limit)
                      .sort('createdAt', -1))
        
        # Convert ObjectId to string and add patient names
        for study in studies:
            study['_id'] = str(study['_id'])
            if 'createdAt' in study:
                study['createdAt'] = study['createdAt'].isoformat()
            if 'updatedAt' in study:
                study['updatedAt'] = study['updatedAt'].isoformat()
            
            # Get patient name
            patient = db.patients.find_one({'_id': study['patientId']})
            study['patientName'] = patient['name'] if patient else 'Unknown Patient'
            
            # Get image count
            image_count = db.images.count_documents({'studyId': study['_id']})
            study['imageCount'] = image_count
        
        response_data = {
            'studies': studies,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }
        
        return create_response(data=response_data)
        
    except Exception as e:
        logger.error(f"Error getting studies: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/studies/patient/<string:patient_id>', methods=['GET'])
@token_required
def get_patient_studies(current_user_id, patient_id):
    try:
        # Check if patient exists
        patient = db.patients.find_one({'_id': patient_id})
        if not patient:
            return create_response(message='Patient not found', status_code=404)
        
        # Get patient studies
        studies = list(db.studies.find({'patientId': patient_id}).sort('createdAt', -1))
        
        # Convert ObjectId to string and add image counts
        for study in studies:
            study['_id'] = str(study['_id'])
            if 'createdAt' in study:
                study['createdAt'] = study['createdAt'].isoformat()
            if 'updatedAt' in study:
                study['updatedAt'] = study['updatedAt'].isoformat()
            
            # Get image count
            image_count = db.images.count_documents({'studyId': study['_id']})
            study['imageCount'] = image_count
        
        return create_response(data={'studies': studies})
        
    except Exception as e:
        logger.error(f"Error getting patient studies: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/studies', methods=['POST'])
@token_required
def create_study(current_user_id):
    try:
        study_data = request.get_json()
        
        # Validate required fields
        if not study_data.get('patientId'):
            return create_response(message='Patient ID is required', status_code=400)
        if not study_data.get('studyType'):
            return create_response(message='Study type is required', status_code=400)
        
        # Validate study type
        valid_types = ['X-Ray', 'CT', 'MRI', 'Ultrasound', 'PET', 'Other']
        if study_data['studyType'] not in valid_types:
            return create_response(message=f'Invalid study type. Must be one of: {", ".join(valid_types)}', status_code=400)
        
        # Check if patient exists
        patient = db.patients.find_one({'_id': study_data['patientId']})
        if not patient:
            return create_response(message='Patient not found', status_code=404)
        
        # Create new study
        new_study = {
            'patientId': study_data['patientId'],
            'patientName': patient['name'],
            'studyType': study_data['studyType'],
            'description': study_data.get('description', ''),
            'status': study_data.get('status', 'draft'),
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow(),
            'created_by': current_user_id,
            'images': [],
            'reportGenerated': False,
            'aiAnalysis': None
        }
        
        result = db.studies.insert_one(new_study)
        new_study['_id'] = str(result.inserted_id)
        new_study['createdAt'] = new_study['createdAt'].isoformat()
        new_study['updatedAt'] = new_study['updatedAt'].isoformat()
        new_study['imageCount'] = 0
        
        log_audit_event('STUDY_CREATED', current_user_id, 'study', new_study['_id'],
                       details={'patient_id': new_study['patientId'], 'study_type': new_study['studyType']})
        return create_response(data=new_study, message='Study created successfully', status_code=201)
        
    except Exception as e:
        logger.error(f"Error creating study: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/studies/<string:study_id>', methods=['PUT'])
@token_required
def update_study(current_user_id, study_id):
    try:
        study_data = request.get_json()
        
        # Check if study exists
        existing_study = db.studies.find_one({'_id': study_id})
        if not existing_study:
            return create_response(message='Study not found', status_code=404)
        
        # Prepare update data
        update_data = {'updatedAt': datetime.utcnow()}
        
        # Update allowed fields
        if 'description' in study_data:
            update_data['description'] = study_data['description']
        if 'status' in study_data:
            valid_statuses = ['draft', 'active', 'archived']
            if study_data['status'] not in valid_statuses:
                return create_response(message=f'Invalid status. Must be one of: {", ".join(valid_statuses)}', status_code=400)
            update_data['status'] = study_data['status']
        if 'studyType' in study_data:
            valid_types = ['X-Ray', 'CT', 'MRI', 'Ultrasound', 'PET', 'Other']
            if study_data['studyType'] not in valid_types:
                return create_response(message=f'Invalid study type. Must be one of: {", ".join(valid_types)}', status_code=400)
            update_data['studyType'] = study_data['studyType']
        
        result = db.studies.update_one(
            {'_id': study_id},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return create_response(message='Study not found', status_code=404)
        
        log_audit_event('STUDY_UPDATED', current_user_id, 'study', study_id,
                       details={'updated_fields': list(update_data.keys())})
        return create_response(message='Study updated successfully')
        
    except Exception as e:
        logger.error(f"Error updating study: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/studies/<string:study_id>', methods=['DELETE'])
@token_required
def delete_study(current_user_id, study_id):
    try:
        # Check if study exists
        study = db.studies.find_one({'_id': study_id})
        if not study:
            return create_response(message='Study not found', status_code=404)
        
        # Delete associated images
        db.images.delete_many({'studyId': study_id})
        
        # Delete study
        result = db.studies.delete_one({'_id': study_id})
        
        if result.deleted_count == 0:
            return create_response(message='Study not found', status_code=404)
        
        log_audit_event('STUDY_DELETED', current_user_id, 'study', study_id,
                       details={'patient_id': study['patientId'], 'study_type': study['studyType']})
        return create_response(message='Study deleted successfully')
        
    except Exception as e:
        logger.error(f"Error deleting study: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/studies/<string:study_id>/generate-report', methods=['POST'])
@token_required
def generate_ai_report(current_user_id, study_id):
    try:
        # Check if study exists
        study = db.studies.find_one({'_id': study_id})
        if not study:
            return create_response(message='Study not found', status_code=404)
        
        # Get study images
        images = list(db.images.find({'studyId': study_id}))
        if not images:
            return create_response(message='No images found for this study', status_code=400)
        
        # Mock AI analysis (in production, this would call a real AI service)
        mock_ai_analysis = {
            'summary': f'AI analysis for {study["studyType"]} study with {len(images)} images',
            'confidence': 0.92,
            'findings': [
                'No acute abnormalities detected',
                'Normal anatomical structures visualized',
                'Comparison with prior studies recommended if available'
            ],
            'recommendations': [
                'Clinical correlation recommended',
                'Follow-up imaging in 6-12 months if clinically indicated'
            ]
        }
        
        # Update study with AI analysis
        db.studies.update_one(
            {'_id': study_id},
            {
                '$set': {
                    'aiAnalysis': mock_ai_analysis,
                    'reportGenerated': True,
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        log_audit_event('AI_REPORT_GENERATED', current_user_id, 'study', study_id,
                       details={'image_count': len(images), 'study_type': study['studyType']})
        return create_response(data=mock_ai_analysis, message='AI report generated successfully')
        
    except Exception as e:
        logger.error(f"Error generating AI report: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

# Image Management endpoints
@app.route('/api/images/upload', methods=['POST'])
@token_required
def upload_image(current_user_id):
    try:
        # Check if file is present
        if 'file' not in request.files:
            return create_response(message='No file provided', status_code=400)
        
        file = request.files['file']
        if file.filename == '':
            return create_response(message='No file selected', status_code=400)
        
        # Get study ID
        study_id = request.form.get('studyId')
        if not study_id:
            return create_response(message='Study ID is required', status_code=400)
        
        # Check if study exists
        study = db.studies.find_one({'_id': study_id})
        if not study:
            return create_response(message='Study not found', status_code=404)
        
        # Validate file type
        if not validate_file_type(file.filename):
            return create_response(message='Invalid file type. Allowed: DICOM, JPG, PNG, TIFF', status_code=400)
        
        # Secure filename
        file_filename = file.filename
        if not file_filename:
            return create_response(message='No filename provided', status_code=400)
            
        filename = secure_filename(file_filename)
        if not filename:
            return create_response(message='Invalid filename', status_code=400)
        
        # Create unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save file
        file.save(file_path)
        
        # Process DICOM metadata if it's a DICOM file
        dicom_metadata = {}
        is_dicom = filename.lower().endswith('.dcm')
        
        if is_dicom:
            try:
                ds = pydicom.dcmread(file_path)
                dicom_metadata = {
                    'patientName': str(ds.get('PatientName', '')),
                    'patientID': str(ds.get('PatientID', '')),
                    'studyDate': str(ds.get('StudyDate', '')),
                    'modality': str(ds.get('Modality', '')),
                    'bodyPartExamined': str(ds.get('BodyPartExamined', '')),
                    'sliceThickness': str(ds.get('SliceThickness', '')),
                    'pixelSpacing': str(ds.get('PixelSpacing', '')),
                    'rows': int(ds.get('Rows', 0)),
                    'columns': int(ds.get('Columns', 0)),
                    'bitsAllocated': int(ds.get('BitsAllocated', 0)),
                    'windowCenter': str(ds.get('WindowCenter', '')),
                    'windowWidth': str(ds.get('WindowWidth', ''))
                }
            except Exception as e:
                logger.warning(f"Could not read DICOM metadata: {str(e)}")
                dicom_metadata = {'error': 'Could not read DICOM metadata'}
        
        # Create image record
        new_image = {
            'studyId': study_id,
            'patientId': study['patientId'],
            'filename': unique_filename,
            'originalFilename': filename,
            'fileSize': os.path.getsize(file_path),
            'contentType': file.content_type or 'application/octet-stream',
            'isDicom': is_dicom,
            'dicomMetadata': dicom_metadata,
            'createdAt': datetime.utcnow(),
            'createdBy': current_user_id,
            'status': 'active'
        }
        
        result = db.images.insert_one(new_image)
        new_image['_id'] = str(result.inserted_id)
        new_image['createdAt'] = new_image['createdAt'].isoformat()
        
        # Update study image count
        db.studies.update_one(
            {'_id': study_id},
            {
                '$push': {'images': new_image['_id']},
                '$set': {'updatedAt': datetime.utcnow()}
            }
        )
        
        log_audit_event('IMAGE_UPLOADED', current_user_id, 'image', new_image['_id'],
                       details={'study_id': study_id, 'filename': filename, 'file_size': new_image['fileSize']})
        return create_response(data=new_image, message='Image uploaded successfully', status_code=201)
        
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/images/study/<string:study_id>', methods=['GET'])
@token_required
def get_study_images(current_user_id, study_id):
    try:
        # Check if study exists
        study = db.studies.find_one({'_id': study_id})
        if not study:
            return create_response(message='Study not found', status_code=404)
        
        # Get images
        images = list(db.images.find({'studyId': study_id}).sort('createdAt', 1))
        
        # Convert ObjectId to string
        for image in images:
            image['_id'] = str(image['_id'])
            if 'createdAt' in image:
                image['createdAt'] = image['createdAt'].isoformat()
        
        return create_response(data={'images': images})
        
    except Exception as e:
        logger.error(f"Error getting study images: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/images/<string:image_id>', methods=['GET'])
@token_required
def get_image(current_user_id, image_id):
    try:
        # Get image from database
        image = db.images.find_one({'_id': image_id})
        if not image:
            return create_response(message='Image not found', status_code=404)
        
        # Get file path
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
        if not os.path.exists(file_path):
            return create_response(message='Image file not found', status_code=404)
        
        # Return file
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            image['filename'],
            as_attachment=False,
            download_name=image['originalFilename']
        )
        
    except Exception as e:
        logger.error(f"Error getting image: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/images/<string:image_id>', methods=['DELETE'])
@token_required
def delete_image(current_user_id, image_id):
    try:
        # Get image from database
        image = db.images.find_one({'_id': image_id})
        if not image:
            return create_response(message='Image not found', status_code=404)
        
        # Delete file from filesystem
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove image from study
        db.studies.update_one(
            {'_id': image['studyId']},
            {'$pull': {'images': image_id}}
        )
        
        # Delete image record
        result = db.images.delete_one({'_id': image_id})
        
        if result.deleted_count == 0:
            return create_response(message='Image not found', status_code=404)
        
        log_audit_event('IMAGE_DELETED', current_user_id, 'image', image_id,
                       details={'study_id': image['studyId'], 'filename': image['originalFilename']})
        return create_response(message='Image deleted successfully')
        
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

@app.route('/api/images/<string:image_id>/process-dicom', methods=['POST'])
@token_required
def process_dicom(current_user_id, image_id):
    try:
        # Get image from database
        image = db.images.find_one({'_id': image_id})
        if not image:
            return create_response(message='Image not found', status_code=404)
        
        if not image['isDicom']:
            return create_response(message='Image is not a DICOM file', status_code=400)
        
        # Get file path
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
        if not os.path.exists(file_path):
            return create_response(message='Image file not found', status_code=404)
        
        # Process DICOM file
        try:
            ds = pydicom.dcmread(file_path)
            
            # Extract comprehensive metadata
            processed_metadata = {
                'basicInfo': {
                    'patientName': str(ds.get('PatientName', '')),
                    'patientID': str(ds.get('PatientID', '')),
                    'studyInstanceUID': str(ds.get('StudyInstanceUID', '')),
                    'seriesInstanceUID': str(ds.get('SeriesInstanceUID', '')),
                    'sopInstanceUID': str(ds.get('SOPInstanceUID', ''))
                },
                'studyInfo': {
                    'studyDate': str(ds.get('StudyDate', '')),
                    'studyTime': str(ds.get('StudyTime', '')),
                    'accessionNumber': str(ds.get('AccessionNumber', '')),
                    'studyDescription': str(ds.get('StudyDescription', ''))
                },
                'seriesInfo': {
                    'modality': str(ds.get('Modality', '')),
                    'seriesNumber': int(ds.get('SeriesNumber', 0)),
                    'seriesDescription': str(ds.get('SeriesDescription', '')),
                    'bodyPartExamined': str(ds.get('BodyPartExamined', ''))
                },
                'imageInfo': {
                    'rows': int(ds.get('Rows', 0)),
                    'columns': int(ds.get('Columns', 0)),
                    'bitsAllocated': int(ds.get('BitsAllocated', 0)),
                    'bitsStored': int(ds.get('BitsStored', 0)),
                    'highBit': int(ds.get('HighBit', 0)),
                    'pixelRepresentation': int(ds.get('PixelRepresentation', 0)),
                    'samplesPerPixel': int(ds.get('SamplesPerPixel', 0)),
                    'photometricInterpretation': str(ds.get('PhotometricInterpretation', ''))
                },
                'technicalInfo': {
                    'sliceThickness': str(ds.get('SliceThickness', '')),
                    'pixelSpacing': str(ds.get('PixelSpacing', '')),
                    'imageOrientationPatient': str(ds.get('ImageOrientationPatient', '')),
                    'imagePositionPatient': str(ds.get('ImagePositionPatient', '')),
                    'windowCenter': str(ds.get('WindowCenter', '')),
                    'windowWidth': str(ds.get('WindowWidth', '')),
                    'rescaleSlope': str(ds.get('RescaleSlope', '1')),
                    'rescaleIntercept': str(ds.get('RescaleIntercept', '0'))
                },
                'equipmentInfo': {
                    'manufacturer': str(ds.get('Manufacturer', '')),
                    'manufacturerModelName': str(ds.get('ManufacturerModelName', '')),
                    'stationName': str(ds.get('StationName', '')),
                    'institutionName': str(ds.get('InstitutionName', ''))
                }
            }
            
            # Update image record with processed metadata
            db.images.update_one(
                {'_id': image_id},
                {
                    '$set': {
                        'dicomMetadata': processed_metadata,
                        'updatedAt': datetime.utcnow()
                    }
                }
            )
            
            log_audit_event('DICOM_PROCESSED', current_user_id, 'image', image_id)
            return create_response(data=processed_metadata, message='DICOM metadata processed successfully')
            
        except Exception as e:
            logger.error(f"Error processing DICOM file: {str(e)}")
            return create_response(message=f'Error processing DICOM file: {str(e)}', status_code=500)
        
    except Exception as e:
        logger.error(f"Error processing DICOM: {str(e)}")
        return create_response(message='Internal server error', status_code=500)

if __name__ == "__main__":
    # Create required directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    app.run(debug=True, host="0.0.0.0", port=5000)
