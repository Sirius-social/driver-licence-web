import uuid
from typing import Optional

from django.http import HttpRequest, HttpResponse

import sirius_sdk
from sirius_sdk.agent.wallet.abstract import RetrieveRecordOptions


class BrowserSession:

    KEY = 'connection_key'
    WALLET_TYPE = 'connection_keys'

    def __init__(self, request: HttpRequest, cookie_path: str = '/'):
        self.__request = request
        self.__connection_key = None
        self.__cookie_path = cookie_path

    async def get_connection_key(self) -> Optional[str]:
        if self.__connection_key:
            return self.__connection_key
        value_from_cookie = self.__request.COOKIES.get(self.KEY)
        if value_from_cookie:
            opts = RetrieveRecordOptions()
            record = await sirius_sdk.NonSecrets.get_wallet_record(self.WALLET_TYPE, value_from_cookie, opts)
            if record:
                self.__connection_key = value_from_cookie
                return value_from_cookie
            else:
                return None
        else:
            return None

    async def create_connection_key(self) -> str:
        self.__connection_key = await sirius_sdk.Crypto.create_key()
        await sirius_sdk.NonSecrets.add_wallet_record(
            self.WALLET_TYPE, self.__connection_key, self.__connection_key
        )
        return self.__connection_key

    async def get_qr_code_url(self) -> str:
        if not self.__connection_key:
            raise RuntimeError('Connection key is Empty!!!')
        endpoints = await sirius_sdk.endpoints()
        simple_endpoint = [e for e in endpoints if e.routing_keys == []][0]
        invitation = sirius_sdk.aries_rfc.Invitation(
            label="Police",
            recipient_keys=[self.__connection_key],
            endpoint=simple_endpoint.address
        )
        qr_content = invitation.invitation_url
        qr_url = await sirius_sdk.generate_qr_code(qr_content)
        return qr_url

    async def set_connection_key(self, response: HttpResponse):
        if self.__connection_key is None:
            await self.create_connection_key()
        response.set_cookie(self.KEY, self.__connection_key, path=self.__cookie_path)