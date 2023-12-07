import base64
from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions
from websocketserver.heavenland.exceptions import JWTDecodeError
from websocketserver.heavenland.client import validate_heavenland_token, game_login


class HeavenlandJwtAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.META.get('REQUEST_METHOD') == 'OPTIONS':
            return None, None
        authorization = request.META.get('HTTP_AUTHORIZATION')
        if not authorization:
            raise exceptions.AuthenticationFailed('Bearer Token is not provided')
        try:
            access_token = authorization[7:]
            validated_token = validate_heavenland_token(access_token)
        except JWTDecodeError:
            raise exceptions.AuthenticationFailed('JWT is not valid')
        try:
            username = validated_token['sub']
        except IndexError:
            raise exceptions.AuthenticationFailed('JWT is not valid')
        return {
                   "refresh_token": None,
                   "access_token": access_token,
                   "user_id": username
               }, None


class HeavenlandUserAndPass(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.META.get('REQUEST_METHOD') == 'OPTIONS':
            return None, None
        authorization = request.META.get('HTTP_AUTHORIZATION')
        if not authorization:
            raise exceptions.AuthenticationFailed('Authorization is not provided')
        try:
            base64_auth = authorization[6:]
            bytes_data = base64.b64decode(base64_auth)
            credentials = bytes_data.decode()
            username, password = credentials.split(':')
            user_data = game_login(username, password)
        except Exception:
            raise exceptions.AuthenticationFailed('Authorization is not valid')
        return user_data, None


class HeavenlandBearerOrBasic(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.META.get('REQUEST_METHOD') == 'OPTIONS':
            return None, None
        authorization = request.META.get('HTTP_AUTHORIZATION')
        if not authorization:
            raise exceptions.AuthenticationFailed('Bearer Token or Basic Auth has to be provided')
        if authorization.startswith('Bearer'):
            try:
                access_token = authorization[7:]
                if access_token == settings.UE4_SECRET:
                    user_id = request.GET.get('user_id')
                    if not user_id:
                        raise exceptions.AuthenticationFailed('user_id is required url parameter')
                    return {
                       "refresh_token": None,
                       "access_token": None,
                       "user_id": user_id
                    }, None
                validated_token = validate_heavenland_token(access_token)
            except JWTDecodeError:
                raise exceptions.AuthenticationFailed('JWT is not valid')
            try:
                username = validated_token['sub']
            except IndexError:
                raise exceptions.AuthenticationFailed('JWT is not valid')
            return {
                "refresh_token": None,
                "access_token": access_token,
                "user_id": username
            }, None
        elif authorization.startswith('Basic'):
            try:
                base64_auth = authorization[6:]
                bytes_data = base64.b64decode(base64_auth)
                credentials = bytes_data.decode()
                username, password = credentials.split(':')
                user_data = game_login(username, password)
            except Exception:
                raise exceptions.AuthenticationFailed('Authorization is not valid')
            return user_data, None
        else:
            raise exceptions.AuthenticationFailed('Bearer Token or Basic Auth has to be provided')


class ApiKeyAuth(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.META.get('REQUEST_METHOD') == 'OPTIONS':
            return None, None
        bearer = request.META.get('HTTP_AUTHORIZATION')
        if not bearer:
            raise exceptions.AuthenticationFailed('Authorization is not provided')
        try:
            token = bearer[7:]
            if token != settings.UE4_SECRET:
                raise Exception
        except Exception:
            raise exceptions.AuthenticationFailed('Token is not valid')
        user_id = request.args.get('user_id')
        return {
            "refresh_token": None,
            "access_token": None,
            "user_id": user_id
        }, None
