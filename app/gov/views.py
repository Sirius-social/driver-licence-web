from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template import loader
from django.conf import settings

import sirius_sdk
import base64

from main.helpers import BrowserSession, build_websocket_url
from main.authorization import auth
from gov.forms import PassportForm
from gov.ssi import issue_passport


async def index(request):

    async with sirius_sdk.context(**settings.GOV['SDK']):
        browser_session = BrowserSession(request, cookie_path=reverse('gov-index'))
        connection_key = await browser_session.get_connection_key()
        if not connection_key:
            connection_key = await browser_session.create_connection_key()
        qr_url = await browser_session.get_qr_code_url("Passport office")

        if request.method == 'POST':
            form = PassportForm(request.POST, request.FILES)
            if form.is_valid():
                values = {
                    "last_name": form.cleaned_data['last_name'],
                    "first_name": form.cleaned_data['first_name'],
                    "birthday": form.cleaned_data['birthday'],
                    "place_of_birth": form.cleaned_data['place_of_birth'],
                    "issue_date": form.cleaned_data['issue_date'],
                    "expiry_date": form.cleaned_data['expiry_date'],
                    "photo": base64.urlsafe_b64encode(form.cleaned_data['photo'].read()).decode("UTF-8")
                }
                conn_key = await browser_session.get_connection_key()
                user = await auth(conn_key)
                pw = await sirius_sdk.PairwiseList.load_for_verkey(user.verkey)
                await issue_passport(conn_key, pw, values, form.cleaned_data['photo'].content_type)

        template = loader.get_template('index.gov.html')
        context = {
            'title': 'Passport table',
            'qr_url': qr_url,
            'is_authorized': False,
            'ws_url': build_websocket_url(request, path=f'/qr/{connection_key}'),
            'auth': await browser_session.auth()
        }
        response = HttpResponse(template.render(context, request))
        await browser_session.set_connection_key(response)
        return response


async def logout(request):
    async with sirius_sdk.context(**settings.GOV['SDK']):
        browser_session = BrowserSession(request, cookie_path=reverse('gov-index'))
        response = HttpResponseRedirect(redirect_to=reverse('gov-index'))
        await browser_session.logout(response)
        return response
