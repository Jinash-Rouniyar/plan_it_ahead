from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from datetime import timedelta

# Use SQLAlchemy Core table reflection to avoid automap relationship/backref issues
from sqlalchemy import Table, MetaData, select
from db_reflect import get_reflector

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def init_jwt(app):
    jwt = JWTManager(app)
    return jwt


@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    preferences = data.get('preferences')

    if not name or not email or not password:
        return jsonify({'msg': 'name, email and password required'}), 400

    # Use reflected users table via Core (avoids automap relationship conflicts)
    try:
        ref = get_reflector()
    except RuntimeError:
        return jsonify({'msg': 'database reflection not initialized'}), 500

    engine = ref['engine']
    metadata = MetaData()
    users = Table('users', metadata, autoload_with=engine)

    with engine.begin() as conn:
        existing = conn.execute(select(users).where(users.c.email == email)).first()
        if existing:
            return jsonify({'msg': 'user already exists'}), 400

        # bcrypt limits input to 72 bytes; guard against longer inputs
        # use Werkzeug PBKDF2 hashing (secure and avoids bcrypt backend issues)
        password_hash = generate_password_hash(password or '')
        insert_values = {}
        if 'name' in users.c:
            insert_values['name'] = name
        if 'email' in users.c:
            insert_values['email'] = email
        # some schemas name the column 'password' instead of 'password_hash'
        if 'password' in users.c:
            insert_values['password'] = password_hash
        elif 'password_hash' in users.c:
            insert_values['password_hash'] = password_hash
        if preferences and 'preferences' in users.c:
            insert_values['preferences'] = preferences

        result = conn.execute(users.insert().values(**insert_values))
        # get primary key value (driver dependent)
        pk_val = None
        try:
            pk_val = result.inserted_primary_key[0]
        except Exception:
            # fallback: select by unique email
            row = conn.execute(select(users).where(users.c.email == email)).first()
            if row:
                pk_val = row._mapping[list(row._mapping.keys())[0]]

        # fetch created row
        created = None
        if pk_val is not None:
            pk_col = list(users.primary_key)[0]
            created = conn.execute(select(users).where(pk_col == pk_val)).first()
        else:
            created = conn.execute(select(users).where(users.c.email == email)).first()

        if not created:
            return jsonify({'msg': 'failed to create user'}), 500

        user_dict = dict(created._mapping)
        access_token = create_access_token({'user_id': user_dict.get(list(users.primary_key)[0].name)}, expires_delta=timedelta(days=7))
        return jsonify({'user': user_dict, 'access_token': access_token}), 201


@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'msg': 'email and password required'}), 400

    try:
        ref = get_reflector()
    except RuntimeError:
        return jsonify({'msg': 'database reflection not initialized'}), 500

    engine = ref['engine']
    metadata = MetaData()
    users = Table('users', metadata, autoload_with=engine)

    with engine.begin() as conn:
        row = conn.execute(select(users).where(users.c.email == email)).first()
        if not row:
            return jsonify({'msg': 'invalid credentials'}), 401

        rowmap = row._mapping
        # support either 'password' or 'password_hash' column names
        stored_hash = rowmap.get('password') or rowmap.get('password_hash')
        if not stored_hash:
            return jsonify({'msg': 'invalid credentials'}), 401
        # verify using Werkzeug check_password_hash
        verified = check_password_hash(stored_hash, password or '')

        if not verified:
            return jsonify({'msg': 'invalid credentials'}), 401

        user_dict = dict(rowmap)
        pk_name = list(users.primary_key)[0].name
        access_token = create_access_token({'user_id': user_dict.get(pk_name)})
        return jsonify({'user': user_dict, 'access_token': access_token}), 200


@bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    identity = get_jwt_identity() or {}
    user_id = identity.get('user_id') if isinstance(identity, dict) else None
    if not user_id:
        return jsonify({'msg': 'invalid token'}), 401
    try:
        ref = get_reflector()
    except RuntimeError:
        return jsonify({'msg': 'database reflection not initialized'}), 500

    engine = ref['engine']
    metadata = MetaData()
    users = Table('users', metadata, autoload_with=engine)

    pk_col = list(users.primary_key)[0]
    with engine.begin() as conn:
        row = conn.execute(select(users).where(pk_col == user_id)).first()
        if not row:
            return jsonify({'msg': 'user not found'}), 404
        return jsonify({'user': dict(row._mapping)}), 200
