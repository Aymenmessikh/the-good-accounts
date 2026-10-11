import uuid

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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


class RegisterAPITests(APITestCase):
    def setUp(self):
        self.url = reverse("accounts_api:register")
        self.payload = {
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Martin",
            "password": "S3cure-pass!",
            "password_confirm": "S3cure-pass!",
        }

    def test_register_success(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "alice@example.com")
        self.assertNotIn("password", response.data)
        user = User.objects.get(email="alice@example.com")
        self.assertTrue(user.check_password("S3cure-pass!"))

    def test_register_normalizes_email(self):
        self.payload["email"] = "Alice@Example.COM"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="alice@example.com").exists())

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email="alice@example.com", password="x",
            first_name="Old", last_name="User",
        )
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_register_duplicate_email_different_case(self):
        User.objects.create_user(
            email="alice@example.com", password="x",
            first_name="Old", last_name="User",
        )
        self.payload["email"] = "ALICE@example.com"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_password_mismatch(self):
        self.payload["password_confirm"] = "Different-pass1!"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_register_weak_password(self):
        for weak in ["short1", "password", "12345678"]:
            with self.subTest(password=weak):
                self.payload["password"] = weak
                self.payload["password_confirm"] = weak
                response = self.client.post(self.url, self.payload, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("password", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_register_missing_fields(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ["email", "first_name", "last_name", "password", "password_confirm"]:
            self.assertIn(field, response.data)


class RegisterPageTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:register")
        self.data = {
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Martin",
            "password1": "S3cure-pass!",
            "password2": "S3cure-pass!",
        }

    def test_get_renders_the_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_post_valid_data_creates_user_and_redirects(self):
        response = self.client.post(self.url, self.data)

        self.assertRedirects(response, self.url)
        self.assertTrue(User.objects.filter(email="alice@example.com").exists())

    def test_post_duplicate_email_shows_error(self):
        User.objects.create_user(
            email="alice@example.com", password="x",
            first_name="Old", last_name="User",
        )
        response = self.client.post(self.url, self.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_post_weak_password_shows_error(self):
        self.data["password1"] = self.data["password2"] = "password"
        response = self.client.post(self.url, self.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("password1", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 0)