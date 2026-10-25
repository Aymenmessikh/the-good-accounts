"""Balance and settlement computations for a closed wallet.

All arithmetic is done in integer cents so that balances always sum to zero
and no rounding error can leave a transfer of 0.01 € unaccounted for.
"""

import heapq
from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce


def to_cents(amount):
    """Convert a Decimal amount in euros to an integer number of cents."""
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


def to_euros(cents):
    """Convert an integer number of cents back to a Decimal amount in euros."""
    return (Decimal(cents) / 100).quantize(Decimal("0.01"))


def compute_balances(wallet):
    """Return {user_id: balance_in_cents} for every member of the wallet.

    A positive balance means the member must receive money, a negative one
    means the member must give money. The total is split equally; leftover
    cents go to the first members (by id) so the shares add up to the total.
    Recorded reimbursements are applied on top of the expense balances.
    """
    member_ids = sorted(wallet.members.values_list("id", flat=True))
    if not member_ids:
        return {}

    paid = defaultdict(int)
    # An expense without an explicit payer is attributed to its creator.
    rows = (
        wallet.expenses.annotate(payer=Coalesce("paid_by", "created_by"))
        .values("payer")
        .annotate(total=Sum("amount"))
    )
    for row in rows:
        paid[row["payer"]] += to_cents(row["total"])

    total = sum(paid.values())
    share, remainder = divmod(total, len(member_ids))
    balances = {}
    for index, user_id in enumerate(member_ids):
        owed = share + (1 if index < remainder else 0)
        balances[user_id] = paid[user_id] - owed

    for reimbursement in wallet.reimbursements.values("from_user_id", "to_user_id", "amount"):
        cents = to_cents(reimbursement["amount"])
        balances[reimbursement["from_user_id"]] = balances.get(reimbursement["from_user_id"], 0) + cents
        balances[reimbursement["to_user_id"]] = balances.get(reimbursement["to_user_id"], 0) - cents
    return balances


def minimize_transfers(balances):
    """Return a list of (debtor_id, creditor_id, cents) settling the balances.

    Exact matches (a debt equal to a credit) are settled first, since each one
    removes two people with a single transfer. The rest is settled greedily by
    always pairing the largest debtor with the largest creditor, which needs at
    most n - 1 transfers and runs in O(n log n). Finding the true minimum is
    NP-hard, so this heuristic is the usual practical choice.
    """
    debtors = {user_id: -amount for user_id, amount in balances.items() if amount < 0}
    creditors = {user_id: amount for user_id, amount in balances.items() if amount > 0}
    transfers = []

    creditors_by_amount = defaultdict(list)
    for user_id, amount in sorted(creditors.items()):
        creditors_by_amount[amount].append(user_id)
    for debtor_id, amount in sorted(debtors.items()):
        if creditors_by_amount.get(amount):
            creditor_id = creditors_by_amount[amount].pop(0)
            transfers.append((debtor_id, creditor_id, amount))
            del creditors[creditor_id]
            debtors[debtor_id] = 0

    # heapq is a min-heap, so amounts are negated to pop the largest first.
    debtor_heap = [(-amount, user_id) for user_id, amount in debtors.items() if amount > 0]
    creditor_heap = [(-amount, user_id) for user_id, amount in creditors.items()]
    heapq.heapify(debtor_heap)
    heapq.heapify(creditor_heap)
    while debtor_heap and creditor_heap:
        debt, debtor_id = heapq.heappop(debtor_heap)
        credit, creditor_id = heapq.heappop(creditor_heap)
        amount = min(-debt, -credit)
        transfers.append((debtor_id, creditor_id, amount))
        if -debt > amount:
            heapq.heappush(debtor_heap, (debt + amount, debtor_id))
        if -credit > amount:
            heapq.heappush(creditor_heap, (credit + amount, creditor_id))
    return transfers
