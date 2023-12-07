from typing import Union
from websocketserver.heavenland.api import HeavenLandAPI
from websocketserver.heavenland.exceptions import JWTDecodeError, HeavenlandAPIError


def game_login(username: str, password: str) -> dict:
    refresh_token, access_token, payload = HeavenLandAPI().game_login(username, password)
    user_id = payload.get('sub')
    return {
        "refresh_token": refresh_token,
        "access_token": access_token,
        "user_id": user_id
    }


def validate_heavenland_token(access_token: str) -> dict:
    try:
        valid_data = HeavenLandAPI().validate_token(access_token)
    except Exception:
        raise JWTDecodeError
    return valid_data


def get_inventory(access_token: str, user_id: str) -> dict:
    try:
        response = HeavenLandAPI().get_user_inventory(access_token, user_id)
    except Exception:
        raise JWTDecodeError
    return response


def add_to_inventory(access_token: str, user_id: str, item_id: int) -> dict:
    try:
        response = HeavenLandAPI().add_to_user_inventory(access_token, user_id, item_id)
    except Exception:
        raise JWTDecodeError
    return response


def remove_from_inventory(access_token: str, user_id: str, item_id: int) -> dict:
    try:
        response = HeavenLandAPI().remove_from_user_inventory(access_token, user_id, item_id)
    except Exception:
        raise JWTDecodeError
    return response


def list_assets(limit: Union[int, None], offset: Union[int, None]) -> dict:
    try:
        print(limit, offset)
        response = HeavenLandAPI().get_game_assets(limit, offset)
    except Exception:
        raise JWTDecodeError
    return response


def list_parcels(access_token: str, user_id: str):
    try:
        response, status_code = HeavenLandAPI().get_parcels(access_token, user_id)
    except HeavenlandAPIError as HlApiErr:
        raise HlApiErr
    except Exception:
        raise JWTDecodeError
    return response, status_code


def list_paragons(access_token: str, user_id: str):
    try:
        response, status_code = HeavenLandAPI().get_paragons(access_token, user_id)
    except HeavenlandAPIError as HlApiErr:
        raise HlApiErr
    except Exception:
        raise JWTDecodeError
    return response, status_code
