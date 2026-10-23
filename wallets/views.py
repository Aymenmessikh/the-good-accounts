from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from expenses.forms import ExpenseForm
from expenses.models import Expense
from .forms import InvitationForm, WalletForm
from .models import Invitation, Membership, Wallet


@login_required
def wallet_list(request):
    """Show the current user's wallets and invitations addressed to them."""
    wallets = Wallet.objects.filter(members=request.user).distinct()
    invitations = Invitation.objects.filter(email__iexact=request.user.email, accepted=False)
    return render(request, "wallets/list.html", {"wallets": wallets, "invitations": invitations, "form": WalletForm()})


@login_required
def wallet_create(request):
    """Create a wallet and add its creator as the first member."""
    form = WalletForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        wallet = form.save(commit=False)
        wallet.created_by = request.user
        wallet.save()
        Membership.objects.create(wallet=wallet, user=request.user)
        messages.success(request, "Porte-monnaie créé.")
    return redirect("wallets:list")


@login_required
def invitation_accept(request, invitation_id):
    """Accept an invitation addressed to the current user's email."""
    invitation = get_object_or_404(Invitation, pk=invitation_id, email__iexact=request.user.email, accepted=False)
    invitation.accepted = True
    invitation.save(update_fields=["accepted"])
    Membership.objects.get_or_create(wallet=invitation.wallet, user=request.user)
    messages.success(request, "Invitation acceptée.")
    return redirect("wallets:list")


@login_required
def wallet_detail(request, wallet_id):
    """Show a member-only wallet page and handle expense or invite forms."""
    wallet = get_object_or_404(Wallet, pk=wallet_id, members=request.user)
    expense_form = ExpenseForm(request.POST or None)
    expense_form.fields["paid_by"].queryset = wallet.members.all()
    invitation_form = InvitationForm(request.POST or None, prefix="invite")
    if request.method == "POST":
        if "add_expense" in request.POST:
            if not wallet.is_closed and expense_form.is_valid():
                expense = expense_form.save(commit=False)
                expense.wallet = wallet
                expense.created_by = request.user
                expense.save()
                messages.success(request, "Dépense ajoutée.")
                return redirect("wallets:detail", wallet_id=wallet.id)
        if "invite" in request.POST and invitation_form.is_valid():
            email = invitation_form.cleaned_data["email"].lower()
            if not wallet.members.filter(email__iexact=email).exists():
                Invitation.objects.get_or_create(wallet=wallet, email=email, defaults={"invited_by": request.user})
            messages.success(request, "Invitation enregistrée.")
            return redirect("wallets:detail", wallet_id=wallet.id)
    expenses = wallet.expenses.select_related("created_by", "paid_by")
    for expense in expenses:
        expense.can_delete = not wallet.is_closed and (
            expense.paid_by_id == request.user.id
            if expense.paid_by_id
            else expense.created_by_id == request.user.id
        )
    pending_invitations = wallet.invitations.filter(accepted=False)
    total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    balances = []
    if wallet.is_closed:
        members = list(wallet.members.all())
        share = total / len(members) if members else Decimal("0")
        for member in members:
            paid = expenses.filter(Q(paid_by=member) | Q(paid_by__isnull=True, created_by=member)).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            balances.append({"user": member, "balance": (paid - share).quantize(Decimal("0.01"))})
    return render(request, "wallets/detail.html", {"wallet": wallet, "expenses": expenses, "total": total, "expense_form": expense_form, "invitation_form": invitation_form, "balances": balances, "pending_invitations": pending_invitations})


@login_required
def expense_delete(request, expense_id):
    """Delete an expense only when the current user is allowed to do so."""
    expense = get_object_or_404(Expense.objects.select_related("wallet"), pk=expense_id, wallet__members=request.user)
    can_delete = expense.paid_by_id == request.user.id if expense.paid_by_id else expense.created_by_id == request.user.id
    if request.method == "POST" and not expense.wallet.is_closed and can_delete:
        wallet_id = expense.wallet_id
        expense.delete()
        messages.success(request, "Dépense supprimée.")
        return redirect("wallets:detail", wallet_id=wallet_id)
    return redirect("wallets:detail", wallet_id=expense.wallet_id)


@login_required
@transaction.atomic
def wallet_close(request, wallet_id):
    """Close a wallet so members can review the simple equal-share balance."""
    wallet = get_object_or_404(Wallet.objects.select_for_update(), pk=wallet_id, members=request.user)
    if request.method == "POST":
        wallet.is_closed = True
        wallet.save(update_fields=["is_closed"])
        messages.success(request, "Porte-monnaie clôturé. Les soldes sont calculés à parts égales.")
    return redirect("wallets:detail", wallet_id=wallet.id)
