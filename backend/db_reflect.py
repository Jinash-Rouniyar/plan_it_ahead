from sqlalchemy.ext.automap import automap_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import current_app

Base = automap_base()
_engine = None
_Session = None


def init_reflector(app):
    """Initialize automap reflector using the app SQLALCHEMY_DATABASE_URI.
    Stores Base, engine and Session factory in app.extensions['db_reflector'].
    """
    global _engine, _Session, Base
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if not db_uri:
        raise RuntimeError('SQLALCHEMY_DATABASE_URI not configured')
    _engine = create_engine(db_uri)
    # reflect DB tables
    Base.prepare(_engine, reflect=True)
    _Session = sessionmaker(bind=_engine)
    app.extensions = getattr(app, 'extensions', {})
    app.extensions['db_reflector'] = {'engine': _engine, 'Base': Base, 'Session': _Session}
    return app.extensions['db_reflector']


def get_reflector():
    if not current_app:
        raise RuntimeError('No active Flask app')
    ref = current_app.extensions.get('db_reflector')
    if not ref:
        raise RuntimeError('db_reflector not initialized; call init_reflector(app) first')
    return ref


def get_class(name):
    """Return the mapped class for the given table name (attribute on Base.classes).
    Example: get_class('itinerary')
    """
    ref = get_reflector()
    Base = ref['Base']
    try:
        return getattr(Base.classes, name)
    except AttributeError:
        raise RuntimeError(f"Reflected class for table '{name}' not found")


def get_session():
    ref = get_reflector()
    Session = ref['Session']
    return Session()
