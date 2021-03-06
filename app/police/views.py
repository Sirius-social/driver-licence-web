from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template import loader
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import sirius_sdk
import base64
import requests
import os
import random

from main.helpers import BrowserSession, build_websocket_url
from main.authorization import auth, save_passport, save_driving_school_diploma
from police.forms import IssueDriverLicenseForm, VerifyFaceForm
from police.ssi import ask_passport, ask_driver_school_diploma, issue_driver_license


async def index(request):

    async with sirius_sdk.context(**settings.POLICE['SDK']):
        browser_session = BrowserSession(request, cookie_path=reverse('police-index'))
        connection_key = await browser_session.get_connection_key()
        if not connection_key:
            connection_key = await browser_session.create_connection_key()
        qr_url = await browser_session.get_qr_code_url("Police")

        user = await auth(connection_key)
        passport = user.passport if user else None
        diploma = user.driving_school_diploma if user else None

        if request.method == 'POST':
            form = IssueDriverLicenseForm(request.POST)
            if form.is_valid():
                values = {
                    "issue_date": form.cleaned_data['issue_date'],
                    "expiry_date": form.cleaned_data['expiry_date'],
                    "place_of_residence": form.cleaned_data['place_of_residence']
                }
                if passport:
                    values["first_name"] = passport["first_name"]
                    values["last_name"] = passport["last_name"]
                    values["birthday"] = passport["birthday"]
                    values["place_of_birth"] = passport["place_of_birth"]
                    values["photo"] = passport["photo"]
                if diploma:
                    values["categories"] = diploma["categories"]

                pw = await sirius_sdk.PairwiseList.load_for_verkey(user.verkey)
                await issue_driver_license(connection_key, pw, values, "image/jpeg")

        template = loader.get_template('index.police.html')
        context = {
            'title': 'Police',
            'qr_url': qr_url,
            'ws_url': build_websocket_url(request, path=f'/qr/{connection_key}'),
            'auth': await browser_session.auth()
        }
        if passport:
            context["first_name"] = passport["first_name"]
            context["last_name"] = passport["last_name"]
            context["birthday"] = passport["birthday"]
            context["place_of_birth"] = passport["place_of_birth"]
            context["user_photo"] = os.path.join(settings.MEDIA_URL, connection_key + ".jpg")
        if diploma:
            context["categories"] = diploma["categories"]
        response = HttpResponse(template.render(context, request))
        await browser_session.set_connection_key(response)
        return response


async def logout(request):
    async with sirius_sdk.context(**settings.POLICE['SDK']):
        browser_session = BrowserSession(request, cookie_path=reverse('police-index'))
        response = HttpResponseRedirect(redirect_to=reverse('police-index'))
        await browser_session.logout(response)
        return response


@csrf_exempt
def verify_face(request):
    data = {
        "status": True,
        "similarity": 0.98 + random.randint(0, 1000)/10000/5,
    }
    return JsonResponse(data)


def save_driver_photo(connection_key: str, b64: str):
    imgdata = base64.urlsafe_b64decode(b64)
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    with open(os.path.join(settings.MEDIA_ROOT, connection_key + ".jpg"), 'wb') as f:
        print(f.write(imgdata))
        print(f.name)


async def request_passport(request):
    async with sirius_sdk.context(**settings.POLICE['SDK']):
        browser_session = BrowserSession(request, cookie_path=reverse('police-index'))
        conn_key = await browser_session.get_connection_key()
        user = await auth(conn_key)
        pw = await sirius_sdk.PairwiseList.load_for_verkey(user.verkey)
        ok, passport_attrs = await ask_passport(conn_key, pw)
        if ok:
            await save_passport(await browser_session.get_connection_key(), passport_attrs)
            save_driver_photo(conn_key, passport_attrs["photo"])

    response = HttpResponseRedirect(redirect_to=reverse('police-index'))
    return response


async def request_driver_school_diploma(request):
    async with sirius_sdk.context(**settings.POLICE['SDK']):
        browser_session = BrowserSession(request, cookie_path=reverse('police-index'))
        conn_key = await browser_session.get_connection_key()
        user = await auth(conn_key)
        pw = await sirius_sdk.PairwiseList.load_for_verkey(user.verkey)
        ok, diploma_attrs = await ask_driver_school_diploma(conn_key, pw)
        if ok:
            await save_driving_school_diploma(await browser_session.get_connection_key(), diploma_attrs)

    response = HttpResponseRedirect(redirect_to=reverse('police-index'))
    return response

