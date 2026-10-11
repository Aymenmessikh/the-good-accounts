import uuid

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user_with_email_and_password(self):
        user = User.objects.create_user(
            email="alice@example.com",
            password="S3cure-pass!",
            first_name="Alice",
            last_name="Martin",
        )
        self.assertEqual(user.email, "alice@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_password_is_hashed(self):
        user = User.objects.create_user(
            email="alice@example.com", password="S3cure-pass!",
            first_name="Alice", last_name="Martin",
        )
        self.assertNotEqual(user.password, "S3cure-pass!")
        self.assertTrue(user.check_password("S3cure-pass!"))

    def test_primary_key_is_uuid(self):
        user = User.objects.create_user(
            email="alice@example.com", password="x",
            first_name="Alice", last_name="Martin",
        )
        self.assertIsInstance(user.pk, uuid.UUID)

    def test_email_is_normalized_to_lowercase(self):
        user = User.objects.create_user(
            email="Alice@EXAMPLE.com", password="x",
            first_name="Alice", last_name="Martin",
        )
        self.assertEqual(user.email, "alice@example.com")

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_superuser_sets_flags(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="x",
            first_name="Ad", last_name="Min",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_create_superuser_with_is_staff_false_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="x", is_staff=False,
            )


class UserModelTests(TestCase):
    def test_email_must_be_unique(self):
        User.objects.create_user(
            email="alice@example.com", password="x",
            first_name="Alice", last_name="Martin",
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email="alice@example.com", password="y",
                first_name="Other", last_name="Person",
            )

    def test_email_uniqueness_is_case_insensitive(self):
        User.objects.create_user(
            email="alice@example.com", password="x",
            first_name="Alice", last_name="Martin",
        )
        # Bypass the manager's lowercasing to hit the DB constraint directly
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(
                email="ALICE@example.com", first_name="A", last_name="B",
            )

    def test_full_name_and_str(self):
        user = User.objects.create_user(
            email="alice@example.com", password="x",
            first_name="Alice", last_name="Martin",
        )
        self.assertEqual(user.get_full_name(), "Alice Martin")
        self.assertEqual(str(user), "alice@example.com")