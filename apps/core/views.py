from django.shortcuts import render


def website(request):
	return render(request, 'website.html')

# Create your views here.
