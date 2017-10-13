import requests
import json
import datetime
from django.conf import settings


def with_refresh_token(client_method):

    def wrapper(self, *args):
        self.__refresh_token__()

        return client_method(self, *args)

    return wrapper


class Auth0ManagementClient(object):
    __url = None
    __ttl = 60 * 20  # 20 minutes retention
    __connection = "Username-Password-Authentication"

    # Keeping the token shared between instances
    # by using dict and updating with update method.
    __token = {}

    def __init__(self):
        self.__url = settings.AUTH0_DOMAIN_URL + "/api/v2"

    def __refresh_token__(self):
        if not self.is_token_expired():
            return

        url = settings.AUTH0_DOMAIN_URL + "/oauth/token"
        headers = {"content-type": "application/json"}
        payload = {"grant_type": "client_credentials", "client_id": settings.AUTH0_CLIENT_ID,
                   "client_secret": settings.AUTH0_CLIENT_SECRET, "audience": settings.AUTH0_AUDIENCE}

        response = requests.post(
            url, data=json.dumps(payload), headers=headers)

        if response.status_code != 200:
            raise Exception("Auth0 failed to get token: " + response.text)

        self.__token = response.json()
        self.__token.update({"created_at": datetime.datetime.now()})

    def is_token_expired(self):
        created_at = self.__token.get("created_at")

        if not created_at:
            return True

        return (created_at + datetime.timedelta(seconds=self.__ttl)) < datetime.datetime.now()

    @with_refresh_token
    def create_user(self, email, password):
        url = self.__url + "/users"
        headers = {"Authorization": "Bearer " +
                   self.__token.get("access_token")}
        payload = {"connection": self.__connection,
                   "email": email, "password": password}

        response = requests.post(url, headers=headers, data=payload)

        if response.status_code != 201:
            raise Exception("Failed to create user on Auth0: " + response.text)
