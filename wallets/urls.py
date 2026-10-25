from django.urls import path
from . import views

app_name = "wallets"
urlpatterns = [
    path("wallets/", views.wallet_list, name="list"),
    path("wallets/create/", views.wallet_create, name="create"),
    path("wallets/invitations/<int:invitation_id>/accept/", views.invitation_accept, name="accept"),
    path("wallets/<int:wallet_id>/", views.wallet_detail, name="detail"),
    path("wallets/<int:wallet_id>/close/", views.wallet_close, name="close"),
    path("wallets/<int:wallet_id>/live/", views.wallet_live, name="live"),
    path("wallets/<int:wallet_id>/reimburse/", views.reimburse, name="reimburse"),
    path("expenses/<int:expense_id>/delete/", views.expense_delete, name="delete_expense"),
]
