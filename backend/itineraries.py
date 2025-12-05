from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db_reflect import get_class, get_session
from datetime import datetime

bp = Blueprint('itineraries', __name__, url_prefix='/api/itineraries')


def _parse_datetime(s):
    if not s:
        return None
    try:
        # accept ISO format
        return datetime.fromisoformat(s)
    except Exception:
        return None


@bp.route('', methods=['POST'])
@jwt_required()
def create_itinerary():
    identity = get_jwt_identity() or {}
    user_id = identity.get('user_id') if isinstance(identity, dict) else None
    if not user_id:
        return jsonify({'msg': 'invalid token'}), 401

    data = request.get_json() or {}
    activity_start_time = _parse_datetime(data.get('activity_start_time'))
    total_cost = data.get('total_cost')

    Itinerary = get_class('itinerary')
    session = get_session()
    try:
        it = Itinerary(user_id=user_id, activity_start_time=activity_start_time, total_cost=total_cost)
        session.add(it)
        session.commit()
        return jsonify({
            'itinerary_id': it.itinerary_id,
            'user_id': it.user_id,
            'activity_start_time': str(it.activity_start_time) if it.activity_start_time else None,
            'total_cost': float(it.total_cost) if it.total_cost is not None else None
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({'msg': str(e)}), 400
    finally:
        session.close()


@bp.route('', methods=['GET'])
@jwt_required()
def list_itineraries():
    identity = get_jwt_identity() or {}
    user_id = identity.get('user_id') if isinstance(identity, dict) else None
    if not user_id:
        return jsonify({'msg': 'invalid token'}), 401

    Itinerary = get_class('itinerary')
    session = get_session()
    try:
        rows = session.query(Itinerary).filter_by(user_id=user_id).all()
        out = []
        for it in rows:
            out.append({
                'itinerary_id': it.itinerary_id,
                'user_id': it.user_id,
                'activity_start_time': str(it.activity_start_time) if it.activity_start_time else None,
                'total_cost': float(it.total_cost) if it.total_cost is not None else None
            })
        return jsonify(out), 200
    finally:
        session.close()


@bp.route('/<int:itinerary_id>', methods=['GET'])
@jwt_required()
def get_itinerary(itinerary_id):
    identity = get_jwt_identity() or {}
    user_id = identity.get('user_id') if isinstance(identity, dict) else None
    if not user_id:
        return jsonify({'msg': 'invalid token'}), 401

    Itinerary = get_class('itinerary')
    session = get_session()
    try:
        it = session.query(Itinerary).filter_by(itinerary_id=itinerary_id, user_id=user_id).first()
        if not it:
            return jsonify({'msg': 'not found or unauthorized'}), 404
        return jsonify({
            'itinerary_id': it.itinerary_id,
            'user_id': it.user_id,
            'activity_start_time': str(it.activity_start_time) if it.activity_start_time else None,
            'total_cost': float(it.total_cost) if it.total_cost is not None else None
        }), 200
    finally:
        session.close()


@bp.route('/<int:itinerary_id>', methods=['PUT'])
@jwt_required()
def update_itinerary(itinerary_id):
    identity = get_jwt_identity() or {}
    user_id = identity.get('user_id') if isinstance(identity, dict) else None
    if not user_id:
        return jsonify({'msg': 'invalid token'}), 401

    data = request.get_json() or {}
    activity_start_time = _parse_datetime(data.get('activity_start_time'))
    total_cost = data.get('total_cost')

    Itinerary = get_class('itinerary')
    session = get_session()
    try:
        it = session.query(Itinerary).filter_by(itinerary_id=itinerary_id, user_id=user_id).first()
        if not it:
            return jsonify({'msg': 'not found or unauthorized'}), 404
        if activity_start_time is not None:
            it.activity_start_time = activity_start_time
        if total_cost is not None:
            it.total_cost = total_cost
        session.commit()
        return jsonify({'msg': 'updated'}), 200
    except Exception as e:
        session.rollback()
        return jsonify({'msg': str(e)}), 400
    finally:
        session.close()


@bp.route('/<int:itinerary_id>', methods=['DELETE'])
@jwt_required()
def delete_itinerary(itinerary_id):
    identity = get_jwt_identity() or {}
    user_id = identity.get('user_id') if isinstance(identity, dict) else None
    if not user_id:
        return jsonify({'msg': 'invalid token'}), 401

    Itinerary = get_class('itinerary')
    session = get_session()
    try:
        it = session.query(Itinerary).filter_by(itinerary_id=itinerary_id, user_id=user_id).first()
        if not it:
            return jsonify({'msg': 'not found or unauthorized'}), 404
        session.delete(it)
        session.commit()
        return jsonify({'msg': 'deleted'}), 200
    except Exception as e:
        session.rollback()
        return jsonify({'msg': str(e)}), 400
    finally:
        session.close()


@bp.route('/<int:itinerary_id>/budget', methods=['POST'])
@jwt_required()
def calculate_budget(itinerary_id):
    """Simple budget stub: returns total_cost from itinerary row if present.
    More advanced calculation can sum bookings, flights, accommodations, attractions costs.
    """
    identity = get_jwt_identity() or {}
    user_id = identity.get('user_id') if isinstance(identity, dict) else None
    if not user_id:
        return jsonify({'msg': 'invalid token'}), 401

    Itinerary = get_class('itinerary')
    session = get_session()
    try:
        it = session.query(Itinerary).filter_by(itinerary_id=itinerary_id, user_id=user_id).first()
        if not it:
            return jsonify({'msg': 'not found or unauthorized'}), 404
        return jsonify({'itinerary_id': it.itinerary_id, 'estimated_budget': float(it.total_cost) if it.total_cost is not None else 0.0}), 200
    finally:
        session.close()
