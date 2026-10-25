from django.conf import settings
from django.db import models


class Wallet(models.Model):
    """A shared space for members, invitations, and expenses."""

    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_wallets")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Membership", related_name="wallets")
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    """Links a user to a wallet they are allowed to access."""

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["wallet", "user"], name="unique_wallet_member")]


class Invitation(models.Model):
    """Pending invitation addressed to a user's email address."""

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["wallet", "email"], name="unique_wallet_invitation")]


class Reimbursement(models.Model):
    """Simulated (mock) transfer of money between two members of a closed wallet."""

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="reimbursements")
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reimbursements_sent")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reimbursements_received")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_user} → {self.to_user} : {self.amount} €"
