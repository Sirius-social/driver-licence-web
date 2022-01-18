from django.http import HttpResponse
from django.template import loader


async def index(request):
    template = loader.get_template('index.carsharing.html')
    context = {
        'title': 'CarSharing'
    }
    return HttpResponse(template.render(context, request))
