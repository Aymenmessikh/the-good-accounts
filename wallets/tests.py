from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from expenses.models import Expense
from .models import Invitation, Membership, Reimbursement, Wallet
from .settlement import compute_balances, minimize_transfers

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


class SettlementAlgorithmTests(TestCase):
    def test_transfers_settle_every_balance(self):
        balances = {1: 3000, 2: -1000, 3: -1000, 4: -1000}
        transfers = minimize_transfers(balances)
        self.assertEqual(len(transfers), 3)
        result = dict(balances)
        for debtor, creditor, cents in transfers:
            result[debtor] += cents
            result[creditor] -= cents
        self.assertTrue(all(value == 0 for value in result.values()))

    def test_exact_matches_are_settled_in_one_transfer(self):
        transfers = minimize_transfers({1: 500, 2: 700, 3: -700, 4: -500})
        self.assertCountEqual(transfers, [(3, 2, 700), (4, 1, 500)])

    def test_settled_wallet_needs_no_transfer(self):
        self.assertEqual(minimize_transfers({1: 0, 2: 0}), [])


class ClosedWalletTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email="alice@example.com", password="pass", first_name="Alice", last_name="A")
        self.bob = User.objects.create_user(email="bob@example.com", password="pass", first_name="Bob", last_name="B")
        self.carol = User.objects.create_user(email="carol@example.com", password="pass", first_name="Carol", last_name="C")
        self.wallet = Wallet.objects.create(name="Trip", created_by=self.alice)
        for user in (self.alice, self.bob, self.carol):
            Membership.objects.create(wallet=self.wallet, user=user)
        Expense.objects.create(wallet=self.wallet, description="Hotel", amount="100.00", created_by=self.alice)
        Expense.objects.create(wallet=self.wallet, description="Taxi", amount="20.00", created_by=self.alice, paid_by=self.bob)
        self.wallet.is_closed = True
        self.wallet.save()
        self.reimburse_url = reverse("wallets:reimburse", args=[self.wallet.pk])

    def test_balances_sum_to_zero_with_rounding(self):
        Expense.objects.create(wallet=self.wallet, description="Coffee", amount="0.01", created_by=self.carol)
        balances = compute_balances(self.wallet)
        self.assertEqual(sum(balances.values()), 0)

    def test_closed_wallet_lists_givers_receivers_and_transfers(self):
        self.client.force_login(self.carol)
        response = self.client.get(reverse("wallets:detail", args=[self.wallet.pk]))
        self.assertContains(response, "Doivent recevoir")
        self.assertContains(response, "Doivent donner")
        # Alice +60, Bob -20, Carol -40: two transfers.
        self.assertEqual(len(response.context["transfers"]), 2)

    def test_debtor_can_reimburse_and_debt_disappears(self):
        self.client.force_login(self.carol)
        self.client.post(self.reimburse_url, {"to_user": self.alice.pk})
        reimbursement = Reimbursement.objects.get()
        self.assertEqual(reimbursement.amount, Decimal("40.00"))
        self.assertEqual(compute_balances(self.wallet)[self.carol.pk], 0)
        self.client.post(self.reimburse_url, {"to_user": self.alice.pk})
        self.assertEqual(Reimbursement.objects.count(), 1)

    def test_creditor_cannot_reimburse(self):
        self.client.force_login(self.alice)
        self.client.post(self.reimburse_url, {"to_user": self.bob.pk})
        self.assertFalse(Reimbursement.objects.exists())

    def test_cannot_reimburse_open_wallet(self):
        self.wallet.is_closed = False
        self.wallet.save()
        self.client.force_login(self.carol)
        self.client.post(self.reimburse_url, {"to_user": self.alice.pk})
        self.assertFalse(Reimbursement.objects.exists())


class LiveUpdateTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass", first_name="Owner", last_name="One")
        self.wallet = Wallet.objects.create(name="Trip", created_by=self.owner)
        Membership.objects.create(wallet=self.wallet, user=self.owner)
        self.live_url = reverse("wallets:live", args=[self.wallet.pk])
        self.client.force_login(self.owner)

    def test_unchanged_wallet_returns_204(self):
        version = self.client.get(self.live_url).json()["version"]
        self.assertEqual(self.client.get(self.live_url, {"v": version}).status_code, 204)

    def test_new_and_deleted_expenses_change_the_version(self):
        version = self.client.get(self.live_url).json()["version"]
        expense = Expense.objects.create(wallet=self.wallet, description="Pizza", amount="9.00", created_by=self.owner)
        data = self.client.get(self.live_url, {"v": version}).json()
        self.assertIn("Pizza", data["html"])
        expense.delete()
        self.assertEqual(self.client.get(self.live_url, {"v": data["version"]}).status_code, 200)

    def test_non_member_cannot_poll(self):
        outsider = User.objects.create_user(email="outside@example.com", password="pass", first_name="Out", last_name="Side")
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(self.live_url).status_code, 404)
