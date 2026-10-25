import hashlib
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from expenses.forms import ExpenseForm
from expenses.models import Expense
from .forms import InvitationForm, WalletForm
from .models import Invitation, Membership, Reimbursement, Wallet
from .settlement import compute_balances, minimize_transfers, to_euros


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


def build_wallet_context(request, wallet):
    """Collect everything the live part of the wallet page needs.

    Shared by the full page and by the polling endpoint so both always render
    the same data (expenses, total, balances, transfers, reimbursements).
    """
    expenses = wallet.expenses.select_related("created_by", "paid_by")
    for expense in expenses:
        expense.can_delete = not wallet.is_closed and (
            expense.paid_by_id == request.user.id
            if expense.paid_by_id
            else expense.created_by_id == request.user.id
        )
    total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    context = {
        "wallet": wallet,
        "members": wallet.members.all(),
        "expenses": expenses,
        "total": total,
        "pending_invitations": wallet.invitations.filter(accepted=False),
        "version": wallet_version(wallet),
    }
    if wallet.is_closed:
        users = {user.id: user for user in wallet.members.all()}
        balances = compute_balances(wallet)
        context["creditors"] = [{"user": users[uid], "amount": to_euros(c)} for uid, c in balances.items() if c > 0]
        context["debtors"] = [{"user": users[uid], "amount": to_euros(-c)} for uid, c in balances.items() if c < 0]
        context["transfers"] = [
            {"from": users[d], "to": users[c], "amount": to_euros(cents), "is_mine": d == request.user.id}
            for d, c, cents in minimize_transfers(balances)
        ]
        context["reimbursements"] = wallet.reimbursements.select_related("from_user", "to_user")
    return context


def wallet_version(wallet):
    """Return a short fingerprint that changes whenever the wallet page content changes.

    Adding or deleting an expense changes the count, max id or sum; closing,
    joining or reimbursing changes the other fields. Cheap aggregates only.
    """
    stats = wallet.expenses.aggregate(count=Count("id"), last=Max("id"), total=Sum("amount"))
    parts = [
        stats["count"], stats["last"], stats["total"], wallet.is_closed,
        wallet.members.count(), wallet.invitations.filter(accepted=False).count(),
        wallet.reimbursements.count(),
    ]
    return hashlib.sha1(repr(parts).encode()).hexdigest()[:12]


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
    context = build_wallet_context(request, wallet)
    context.update({"expense_form": expense_form, "invitation_form": invitation_form})
    return render(request, "wallets/detail.html", context)


@login_required
def wallet_live(request, wallet_id):
    """Polling endpoint: return the refreshed live section when the wallet changed.

    The page sends the version it currently displays (``?v=``). If nothing
    changed, an empty 204 response is returned so polling stays cheap;
    otherwise the new version and the re-rendered HTML fragment are sent.
    """
    wallet = get_object_or_404(Wallet, pk=wallet_id, members=request.user)
    version = wallet_version(wallet)
    if request.GET.get("v") == version:
        return HttpResponse(status=204)
    context = build_wallet_context(request, wallet)
    html = render_to_string("wallets/_live.html", context, request=request)
    return JsonResponse({"version": version, "closed": wallet.is_closed, "html": html})


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


@login_required
@transaction.atomic
def reimburse(request, wallet_id):
    """Record a mock reimbursement from the current user to another member.

    Only a transfer currently suggested for the current user can be paid, and
    its amount is taken from the server-side computation, never from the form.
    The wallet row is locked so a double click cannot pay the same debt twice.
    """
    wallet = get_object_or_404(Wallet.objects.select_for_update(), pk=wallet_id, members=request.user)
    if request.method == "POST" and wallet.is_closed:
        to_user_id = request.POST.get("to_user")
        for debtor_id, creditor_id, cents in minimize_transfers(compute_balances(wallet)):
            if debtor_id == request.user.id and str(creditor_id) == to_user_id:
                reimbursement = Reimbursement.objects.create(
                    wallet=wallet, from_user=request.user, to_user_id=creditor_id, amount=to_euros(cents)
                )
                messages.success(request, f"Remboursement simulé de {reimbursement.amount} € enregistré.")
                break
        else:
            messages.error(request, "Aucun remboursement à effectuer vers ce compte.")
    return redirect("wallets:detail", wallet_id=wallet.id)
