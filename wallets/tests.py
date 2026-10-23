from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from expenses.models import Expense
from .models import Invitation, Membership, Wallet

User = get_user_model()


class WalletAndExpenseTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass", first_name="Owner", last_name="One")
        self.member = User.objects.create_user(email="member@example.com", password="pass", first_name="Member", last_name="Two")
        self.outsider = User.objects.create_user(email="outside@example.com", password="pass", first_name="Outside", last_name="Three")
        self.wallet = Wallet.objects.create(name="Trip", created_by=self.owner)
        Membership.objects.create(wallet=self.wallet, user=self.owner)
        self.detail_url = reverse("wallets:detail", args=[self.wallet.pk])

    def test_create_wallet_adds_creator_as_member(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("wallets:create"), {"name": "Weekend"})
        wallet = Wallet.objects.get(name="Weekend")
        self.assertRedirects(response, reverse("wallets:list"))
        self.assertEqual(wallet.created_by, self.owner)
        self.assertTrue(wallet.members.filter(pk=self.owner.pk).exists())

    def test_only_members_can_open_wallet(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.detail_url).status_code, 404)

    def test_member_can_open_wallet(self):
        Membership.objects.create(wallet=self.wallet, user=self.member)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.detail_url).status_code, 200)

    def test_invitation_acceptance_grants_membership(self):
        invitation = Invitation.objects.create(wallet=self.wallet, email=self.member.email, invited_by=self.owner)
        self.client.force_login(self.member)
        response = self.client.post(reverse("wallets:accept", args=[invitation.pk]))
        self.assertRedirects(response, reverse("wallets:list"))
        self.assertTrue(self.wallet.members.filter(pk=self.member.pk).exists())
        self.assertTrue(Invitation.objects.get(pk=invitation.pk).accepted)

    def test_non_invited_user_cannot_accept_invitation(self):
        invitation = Invitation.objects.create(wallet=self.wallet, email=self.member.email, invited_by=self.owner)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(reverse("wallets:accept", args=[invitation.pk])).status_code, 404)

    def test_member_can_add_expense_and_total_is_shown(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.detail_url, {"description": "Train", "amount": "12.50", "paid_by": self.owner.pk, "add_expense": ""})
        self.assertRedirects(response, self.detail_url)
        expense = Expense.objects.get(wallet=self.wallet)
        self.assertEqual(expense.amount, Decimal("12.50"))
        self.assertEqual(expense.created_by, self.owner)
        self.assertEqual(expense.paid_by, self.owner)
        self.assertContains(self.client.get(self.detail_url), "12.50")

    def test_invalid_amount_is_not_saved(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.detail_url, {"description": "Invalid", "amount": "0", "paid_by": "", "add_expense": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIn("amount", response.context["expense_form"].errors)
        self.assertFalse(Expense.objects.exists())

    def test_non_member_cannot_create_expense(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(self.detail_url, {"description": "No", "amount": "1", "add_expense": ""}).status_code, 404)
        self.assertFalse(Expense.objects.exists())

    def test_only_payer_can_delete_when_payer_is_set(self):
        Membership.objects.create(wallet=self.wallet, user=self.member)
        expense = Expense.objects.create(wallet=self.wallet, description="Lunch", amount="10.00", created_by=self.owner, paid_by=self.member)
        self.client.force_login(self.owner)
        self.client.post(reverse("wallets:delete_expense", args=[expense.pk]))
        self.assertTrue(Expense.objects.filter(pk=expense.pk).exists())
        self.client.force_login(self.member)
        self.client.post(reverse("wallets:delete_expense", args=[expense.pk]))
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_creator_can_delete_when_no_payer_is_set(self):
        expense = Expense.objects.create(wallet=self.wallet, description="Cash", amount="4.00", created_by=self.owner)
        self.client.force_login(self.owner)
        self.client.post(reverse("wallets:delete_expense", args=[expense.pk]))
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_non_member_cannot_delete_expense(self):
        expense = Expense.objects.create(wallet=self.wallet, description="Lunch", amount="10.00", created_by=self.owner)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(reverse("wallets:delete_expense", args=[expense.pk])).status_code, 404)
        self.assertTrue(Expense.objects.filter(pk=expense.pk).exists())

    def test_closed_wallet_rejects_new_expenses(self):
        self.wallet.is_closed = True
        self.wallet.save()
        self.client.force_login(self.owner)
        self.client.post(self.detail_url, {"description": "After closing", "amount": "2.00", "paid_by": "", "add_expense": ""})
        self.assertFalse(Expense.objects.exists())
