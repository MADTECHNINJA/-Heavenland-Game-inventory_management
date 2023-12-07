from channels.layers import get_channel_layer
from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from django.conf import settings


def broadcast_message(user_id: str, data: dict):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "HL", {
            "type": "broadcast",
            "json": {
                "user_id": user_id,
                "data": data
            },
        }
    )


class HLConsumer(JsonWebsocketConsumer):

    authenticated = False

    def authenticate(self, token):
        if settings.UE4_SECRET != token:
            self.send_json({"error": "token is not valid"})
            return
        self.authenticated = True
        async_to_sync(self.channel_layer.group_add)("HL", self.channel_name)
        self.send_json({"info": "connected"})

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)("HL", self.channel_name)

    def receive_json(self, content, **kwargs):
        if not self.authenticated:
            if content.get('action') == 'login' and content.get('token'):
                token = content.get('token')
                self.authenticate(token)
            else:
                self.send_json({'error': "you need to authenticate first"})
        elif content.get('action') == 'broadcast':
            self.send_group_message(self.channel_name, content.get('data', {}), **kwargs)

    def send_group_message(self, user_id, content, **kwargs):
        async_to_sync(self.channel_layer.group_send)(
            "HL",
            {
                "type": "broadcast",
                "json": {
                    "user_id": user_id,
                    "data": content
                },
            },
        )

    def broadcast(self, data):
        self.send_json(data['json'])
