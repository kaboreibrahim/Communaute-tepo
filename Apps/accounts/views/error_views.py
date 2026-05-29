from django.shortcuts import render

def custom_page_not_found(request, exception):
    return render(request, 'error/404.html', status=404)

def custom_permission_denied(request, exception):
    return render(request, 'error/403.html', status=403)

def custom_server_error(request):
    return render(request, 'error/500.html', status=500)

def custom_bad_request(request, exception):
    return render(request, 'error/400.html', status=400)
