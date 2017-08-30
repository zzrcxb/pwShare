from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import MultipleObjectsReturned

from .models import UserFile
from pwShare.settings import DATA_PATH
from .utils import *

from mimetypes import guess_type
from datetime import datetime

import logging
import re


@require_http_methods(['POST', 'GET', ])
@csrf_exempt
def upload(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        alias = request.POST.get('Alias')
        passwd = request.POST.get('Password')

        if len(passwd) == 0:
            passwd = passwd_generator(4)

        print(passwd, alias)
        # Check alias, passwd and file
        alias_pattern = re.compile(r'^[^/]{7,32}$')
        passwd_pattern = re.compile(r'^[0-9a-zA-Z]{4,6}$')
        if len(alias) > 0:
            if re.match(alias_pattern, alias) is None or len(UserFile.objects.filter(alias=alias, passwd=passwd)):
                return render(request, 'pshare/index.html', dict(a_wrong=True, p_wrong=False))

        if re.match(passwd_pattern, passwd) is None:
            return render(request, 'pshare/index.html', dict(a_wrong=False, p_wrong=True))

        if file is None:
            return render(request, 'pshare/index.html', dict(empty_file=True))

        hash_value = save_file(file)

        UserFile.objects.filter(alias=alias, passwd=passwd).delete()

        user_file = UserFile(
            filename=file.name,
            alias=alias if len(alias) > 0 else None,
            passwd=passwd,
            sha1=hash_value,
            uploaded_date=datetime.utcnow(),
        )
        user_file.save()

        result = dict(
            hash_value=hash_value,
            has_alias=len(alias) != 0,
            alias=alias,
            passwd=passwd
        )
        return render(request, 'pshare/upload.html', result)
    else:
        return render(request, 'pshare/index.html', dict(a_wrong=False, p_wrong=False, empty_file=False))


@require_http_methods(['GET', 'POST', ])
@csrf_exempt
def download(request, prefix):
    if len(prefix) == 40:
        prefix = prefix.lower()

    if request.method == 'POST':
        passwd = request.POST.get('Password')
        if len(prefix) == 40:
            try:
                file = get_object_or_404(UserFile, sha1=prefix, passwd=passwd)
            except MultipleObjectsReturned as e:
                file = UserFile.objects.filter(sha1=prefix, passwd=passwd)[0]
            except Http404:
                return render(request, 'pshare/download.html', dict(alias=prefix, wrong=True))
        else:
            try:
                file = get_object_or_404(UserFile, alias=prefix, passwd=passwd)
            except MultipleObjectsReturned as e:
                logging.error(repr(e))
                return HttpResponse(status=500)
            except Http404:
                return render(request, 'pshare/download.html', dict(alias=prefix, wrong=True))

        hash_value = file.sha1
        path = os.path.join(DATA_PATH, hash_value[:2], hash_value[2:4], hash_value)
        print(guess_type(file.filename), file.filename)
        f = open(path, 'rb')
        return HttpResponse(content=f, content_type=guess_type(file.filename)[0])

    else:
        is_file_existed = False
        # SHA-1
        if len(prefix) == 40:
            files = UserFile.objects.filter(sha1=prefix)
            if len(files) > 0:
                is_file_existed = True
        else:
            files = UserFile.objects.filter(alias=prefix)
            if len(files) > 0:
                is_file_existed = True

        if is_file_existed:
            return render(request, 'pshare/download.html', dict(alias=prefix, wrong=False))
        else:
            raise Http404(repr(prefix) + ' is not found, please check the SHA-1 or alias you inputted.')

# rt_file = open(r'C:\Users\Neil\Desktop\survey.pdf', 'rb')
# response = HttpResponse(content=rt_file, content_type='application/pdf')
# response['Content-Disposition'] = 'attachment; filename=%s' % smart_str('test.pdf')
# response['X-Sendfile'] = smart_str()