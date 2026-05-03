from django.contrib import admin

# Register your models here.

from .models import Account, Business, Transaction, Card

admin.site.register(Account)
admin.site.register(Business)
admin.site.register(Transaction)
admin.site.register(Card)

