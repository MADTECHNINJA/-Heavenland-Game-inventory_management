from math import ceil
from uuid import uuid4
from logging import getLogger
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from websocketserver.auth.auth import HeavenlandBearerOrBasic, HeavenlandUserAndPass, HeavenlandJwtAuthentication
from websocketserver.heavenland.client import game_login, get_inventory, remove_from_inventory, add_to_inventory, \
    list_assets, list_parcels, list_paragons
from websocketserver.heavenland.exceptions import UnauthorizedError, HeavenlandAPIError, JWTDecodeError
from .redis import redis_instance
from .models import InventoryItem, Parcel
from django.conf import settings

logger = getLogger(__file__)

headers = {"Access-Control-Allow-Origin": "*"}
cors_headers = {"Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True,
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "Access-Control-Allow-Methods": "*"}


class ApiBaseView(APIView):
    allowed_methods = {'GET'}
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK, headers=headers)

class ApiVersionView(APIView):
    allowed_methods = {'GET'}
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK,headers=headers,data={"api":"v1.0.1","env":f"{settings.HEAVENLAND_API_ENVIRONMENT}","desc":"Inventory Management Python"})


class CharacterEditorView(APIView):
    allowed_methods = {'POST'}
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        char_url = request.data.get('charUrl')
        if not username or not password:
            return Response({"error": "missing username or password in the request body"}, status.HTTP_400_BAD_REQUEST,
                            headers=headers)
        if not char_url:
            return Response({"error": "missing charUrl in the request body"}, status.HTTP_400_BAD_REQUEST,
                            headers=headers)
        try:
            data = game_login(username, password)
        except UnauthorizedError:
            return Response({"error": "invalid credentials"}, status.HTTP_401_UNAUTHORIZED, headers=headers)
        user_id = data['user_id']
        redis_instance.set(f"{user_id}_char", char_url)
        return Response(status=status.HTTP_201_CREATED, headers=headers)


class GameLoginView(APIView):
    allowed_methods = {'POST'}
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({"error": "missing username or password in the request body"}, status.HTTP_400_BAD_REQUEST,
                            headers=headers)
        payload = game_login(username, password)
        token = uuid4().hex
        redis_instance.hmset(name=token, mapping=payload)
        return Response({"token": token}, status.HTTP_200_OK, headers=headers)


class GameAssetsView(APIView):
    allowed_methods = {'GET'}
    permission_classes = [AllowAny]

    def get(self, request):
        limit = request.query_params.get('item_id')
        offset = request.query_params.get('item_id')
        res = list_assets(limit, offset)
        return Response(res, headers=headers)


class InventoryView(APIView):
    allowed_methods = {'POST', 'GET', 'DELETE'}
    authentication_classes = [HeavenlandUserAndPass]

    def get(self, request):
        user_id = request.user['user_id']
        items = InventoryItem.objects.filter(username=user_id)
        resp = []
        for item in items:
            resp.append({
                "itemId": item.item_id,
                "description": item.description,
                "fbx": item.fbx,
                "ueReference": item.ue_reference
            })
        return Response(resp, headers=headers)

    def post(self, request):
        try:
            item_id = int(request.query_params.get('item_id'))
        except ValueError:
            return Response({"error": "item_id has to be an integer"}, status.HTTP_400_BAD_REQUEST, headers=headers)
        if not item_id:
            return Response({"error": "item_id has to be provided"}, status.HTTP_400_BAD_REQUEST, headers=headers)
        assets_list = list_assets(None, None).get('items')
        for asset in assets_list:
            if asset['id'] == item_id:
                selected_asset = asset
                break
        else:
            return Response({"error": "selected item not found in game assets"}, status.HTTP_404_NOT_FOUND,
                            headers=headers)
        item = InventoryItem.objects.create(
            username=request.user['user_id'],
            item_id=item_id,
            description=selected_asset['description'],
            fbx=selected_asset['fbx'],
            ue_reference=selected_asset['ueReference']
        )
        item.save()
        add_to_inventory(request.user.get('access_token'), request.user.get('user_id'), item_id)
        return Response(status.HTTP_201_CREATED, headers=headers)

    def delete(self, request):
        item_id = request.query_params.get('item_id')
        if not item_id:
            return Response({"error": "item_id has to be provided"}, status.HTTP_400_BAD_REQUEST, headers=headers)
        count, _ = InventoryItem.objects.filter(username=request.user['user_id'], item_id=item_id).delete()
        remove_from_inventory(request.user.get('access_token'), request.user.get('user_id'), item_id)
        if count > 0:
            return Response(status=status.HTTP_200_OK, headers=headers)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND, headers=headers)


class NftView(APIView):
    allowed_methods = {'GET'}
    authentication_classes = [HeavenlandBearerOrBasic]

    def get(self, request):
        page = request.GET.get('page', None)
        per_page = request.GET.get('per_page', 5)
        total_pages = None
        logger.warning(f"got NFTs request with params page={page}, per_page={request.GET.get('per_page', None)}")

        # validation
        if page:
            try:
                page = int(page)
            except ValueError:
                resp = {"error": "page must be a valid integer"}
                return Response(resp, status=status.HTTP_400_BAD_REQUEST, headers=cors_headers)
            if page < 1:
                resp = {"error": "page must be a positive integer"}
                return Response(resp, status=status.HTTP_400_BAD_REQUEST, headers=cors_headers)
        if per_page:
            try:
                per_page = int(per_page)
            except ValueError:
                resp = {"error": "per_page must be a valid integer"}
                return Response(resp, status=status.HTTP_400_BAD_REQUEST, headers=cors_headers)
            if not 1 <= int(per_page) <= 100:
                resp = {"error": "per_page must be a positive integer between 1 and 100"}
                return Response(resp, status=status.HTTP_400_BAD_REQUEST, headers=cors_headers)
        try:
            data, status_code = list_paragons(access_token=request.user['access_token'], user_id=request.user['user_id'])
        except HeavenlandAPIError as HlApiErr:
            err_msg = {"error": f"Heavenland API Error, responded with status code {HlApiErr.status_code}"}
            return Response(err_msg, status=status.HTTP_424_FAILED_DEPENDENCY, headers=headers)
        except Exception:
            err_msg = {"error": f"General error on the server, contact the administrator"}
            return Response(err_msg, status=status.HTTP_500_INTERNAL_SERVER_ERROR, headers=headers)
        nfts = []
        if status_code > 400:
            resp = {
                "heavenlandAPIError": data
            }
            return Response(resp, status=status_code, headers=cors_headers)
        all_items = data.get('items', [])

        # prepare pagination
        if page:
            i1 = (page - 1) * per_page
            i2 = i1 + per_page
            items = all_items[i1:i2]
            total_pages = ceil(len(all_items) / per_page)
        else:
            per_page = None
            items = all_items
        for item in items:
            assets = item.get('assets', [])
            name = item.get('name', 'default')
            image = None
            for asset in assets:
                if "full_sized_image" in asset.get('labels', []):
                    image = asset.get('uri')
            if image:
                nfts.append({
                    "type": name,
                    "url": image
                })
        resp = {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "nft": nfts,
        }
        return Response(resp, headers=headers)


class ParcelsView(APIView):
    allowed_methods = {'GET', 'OPTIONS'}
    authentication_classes = [HeavenlandJwtAuthentication]

    def get(self, request, *args, **kwargs):
        try:
            data, status_code = list_parcels(access_token=request.user['access_token'], user_id=request.user['user_id'])
        except HeavenlandAPIError as HlApiErr:
            err_msg = {"error": f"Heavenland API Error, responded with status code {HlApiErr.status_code}"}
            return Response(err_msg, status=status.HTTP_424_FAILED_DEPENDENCY, headers=headers)
        except Exception:
            err_msg = {"error": f"General error on the server, contact the administrator"}
            return Response(err_msg, status=status.HTTP_500_INTERNAL_SERVER_ERROR, headers=headers)
        parcels = []
        if status_code > 400:
            resp = {
                "heavenlandAPIError": data
            }
            return Response(resp, status=status_code, headers=cors_headers)
        items = data.get('items', [])
        for item in items:
            offChain = item.get('metadata', {}).get('offChain', {})
            attributes = offChain.get('attributes', [])
            fullname = offChain.get('name', '')
            files = offChain.get('properties', {}).get('files', [])
            parcel_data = {
                "id": item.get('id'),
                "name": fullname[:fullname.find('[')].strip(),
                "building_id": None,
            }
            for attribute in attributes:
                if attribute.get('trait_type') == "Coordinate X [m]":
                    parcel_data['x'] = attribute.get('value')
                if attribute.get('trait_type') == "Coordinate Y [m]":
                    parcel_data['y'] = attribute.get('value')
            for file in files:
                if file.get('uri', '').startswith('https://shdw-drive'):
                    parcel_data['thumbnail'] = file.get('uri')
            parcel = Parcel.objects.filter(id=parcel_data['id']).first()
            if not parcel:
                Parcel.objects.create(
                    id=parcel_data['id'],
                    name=parcel_data['name'],
                    location_x=parcel_data.get('x'),
                    location_y=parcel_data.get('y'),
                    username=request.user['user_id'],
                    thumbnail=parcel_data.get('thumbnail'),
                )
            else:
                parcel_data['building_id'] = parcel.building_id
                if parcel.thumbnail is None and parcel_data.get('thumbnail') is not None:
                    parcel.thumbnail = parcel_data.get('thumbnail')
                    parcel.save()

            parcels.append(parcel_data)

        return Response(parcels, status=status.HTTP_200_OK, headers=cors_headers)

    def options(self, request, *args, **kwargs):
        if self.metadata_class is None:
            return self.http_method_not_allowed(request, *args, **kwargs)
        data = self.metadata_class().determine_metadata(request, self)
        return Response(data, status=status.HTTP_200_OK, headers=cors_headers)

