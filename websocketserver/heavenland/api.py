import requests
import json
import urllib.parse
import jwt
import logging
from typing import Tuple
from django.conf import settings
from .exceptions import UnauthorizedError, HeavenlandAPIError

logger = logging.getLogger(__name__)


class HeavenLandAPI:

    root_url = settings.HEAVENLAND_API_URL
    default_headers = {'content-type': 'application/json'}
    custom_headers = {}
    path = ''
    request_url_params = {}
    request_data = {}
    api_response = None
    response_data = {}
    status_code = 0

    def request_common(self, resp: requests.Response):
        self.api_response = resp
        self.get_response_dict(resp)
        self.custom_headers = {}
        self.request_data = {}
        self.request_url_params = {}
        self.status_code = resp.status_code

    def request_get(self) -> requests.Response:
        request_headers = {**self.default_headers, **self.custom_headers}
        resp = requests.get(f"{self.root_url}{self.path}{self.get_request_url_params()}", headers=request_headers)
        self.request_common(resp)
        return resp

    def request_post(self) -> requests.Response:
        request_headers = {**self.default_headers, **self.custom_headers}
        resp = requests.post(f"{self.root_url}{self.path}{self.get_request_url_params()}",
                             data=self.request_data,
                             headers=request_headers)
        self.request_common(resp)
        return resp

    def request_delete(self) -> requests.Response:
        request_headers = {**self.default_headers, **self.custom_headers}
        resp = requests.delete(f"{self.root_url}{self.path}{self.get_request_url_params()}",
                               data=self.request_data,
                               headers=request_headers)
        self.request_common(resp)
        return resp

    def set_path(self, path: str):
        self.path = path

    def set_request_data(self, data: dict):
        self.request_data = json.dumps(data)

    def set_request_headers(self, key, value):
        self.custom_headers[key] = value

    def set_request_url_params(self, key, value):
        if value:
            self.request_url_params[str(key)] = str(value)

    def get_request_url_params(self):
        if len(self.request_url_params) > 0:
            return "?" + urllib.parse.urlencode(self.request_url_params)
        else:
            return ""

    def get_response_dict(self, response: requests.Response) -> dict:
        self.response_data = {}
        if response.status_code not in [200, 201]:
            logger.error(f"{response.status_code} - {response.text}")
            raise HeavenlandAPIError(status_code=response.status_code)
        if response.text and len(response.text) > 0:
            data = json.loads(response.text)
            self.response_data = data
            return data

    def validate_token(self, token: str) -> dict:
        valid_data = jwt.decode(
            token,
            settings.VERIFYING_KEY,
            algorithms=settings.HEAVENLAND_ALGORITHM,
            audience=settings.HEAVENLAND_AUD)
        return valid_data

    def create_account(self, username: str, password: str) -> dict:
        self.set_path('/idm/accounts')
        self.set_request_data({
            "username": username,
            "password": password
        })
        self.request_post()
        return self.response_data

    def game_login(self, username: str, password: str) -> Tuple[str, str, dict]:
        self.set_path('/idm/auth/login')
        self.set_request_data({
            "username": username,
            "password": password,
            "type": "credentials",
            "clientType": "game"
        })
        self.request_post()
        refresh_token = self.response_data.get('refreshToken', {}).get('value')
        if not refresh_token:
            raise UnauthorizedError()
        self.set_path('/idm/auth/access-token')
        self.set_request_data({
            "refreshToken": refresh_token
        })
        self.request_post()
        access_token = self.response_data.get('accessToken', {}).get('value', '')
        payload = self.validate_token(access_token)
        return refresh_token, access_token, payload

    def get_game_assets(self, limit: int = None, offset: int = None) -> dict:
        self.set_path('/inventory/game-assets')
        self.set_request_url_params(key='limit', value=limit)
        self.set_request_url_params(key='offset', value=offset)
        self.request_get()
        return self.response_data

    def add_game_asset(self, description: str, fbx: str, ue_reference: str) -> dict:
        self.set_path('/inventory/game-assets')
        self.set_request_data({
            "description": description,
            "fbx": fbx,
            "ueReference": ue_reference
        })
        self.request_post()
        return self.response_data

    def get_user_inventory(self, access_token: str, user_id: str) -> dict:
        self.set_path(f'/inventory/accounts/{user_id}/game-assets')
        self.set_request_headers(key='Authorization', value=f'Bearer {access_token}')
        self.request_get()
        return self.response_data

    def add_to_user_inventory(self, access_token: str, user_id: str, item_id: int) -> dict:
        self.set_path(f'/inventory/accounts/{user_id}/game-assets')
        self.set_request_headers(key='Authorization', value=f'Bearer {access_token}')
        self.set_request_data({
            "itemId": item_id
        })
        self.request_post()
        return self.response_data

    def remove_from_user_inventory(self, access_token: str, user_id: str, inventory_item_id: int) -> dict:
        self.set_path(f'/inventory/accounts/{user_id}/game-assets/{inventory_item_id}')
        self.set_request_headers(key='Authorization', value=f'Bearer {access_token}')
        self.request_delete()
        return self.response_data

    def get_parcels(self, access_token: str, user_id: str):
        self.set_path(f'/inventory/accounts/{user_id}/nfts/parcels?divideParcelBuckets=true')
        self.set_request_headers(key='Authorization', value=f'Bearer {access_token}')
        self.request_get()
        return self.response_data, self.status_code

    def get_paragons(self, access_token: str, user_id: str):
        self.set_path(f'/inventory/accounts/{user_id}/nfts/paragons')
        self.set_request_headers(key='Authorization', value=f'Bearer {access_token}')
        self.request_get()
        return self.response_data, self.status_code
