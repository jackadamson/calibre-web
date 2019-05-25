import json
import sys
from functools import wraps

from flask import (Response, make_response, abort)
from flask import request
from flask_login import (login_required)
from werkzeug.security import check_password_hash

from cps.models import ub
from cps.models.ub import config


def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def check_auth(username, password):
    if sys.version_info.major == 3:
        username = username.encode('windows-1252')
    user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == username.decode('utf-8').lower()).first()
    return bool(user and check_password_hash(user.password, password))


def requires_basic_auth_if_no_ano(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if config.config_anonbrowse != 1:
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
        return f(*args, **kwargs)

    return decorated


def login_required_if_no_ano(f):
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if config.config_anonbrowse == 1:
            return f(*args, **kwargs)
        return login_required(f)(*args, **kwargs)

    return decorated_view


def remote_login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if config.config_remote_login:
            return f(*args, **kwargs)
        if request.is_xhr:
            data = {'status': 'error', 'message': 'Forbidden'}
            response = make_response(json.dumps(data, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return response, 403
        abort(403)

    return inner
