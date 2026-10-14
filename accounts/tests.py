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

        self.assertRedirects(response, reverse("accounts:login"))
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

class ProfileAPITests(APITestCase):
    def setUp(self):
        self.url = reverse("accounts_api:me")
        self.user = User.objects.create_user(
            email="alice@example.com", password="S3cure-pass!",
            first_name="Alice", last_name="Martin",
        )

    def test_get_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_returns_own_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "alice@example.com")
        self.assertEqual(response.data["first_name"], "Alice")
        self.assertNotIn("password", response.data)

    def test_patch_updates_names(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            self.url, {"first_name": "Alicia", "last_name": "Dupont"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alicia")
        self.assertEqual(self.user.last_name, "Dupont")

    def test_patch_is_partial(self):
        self.client.force_login(self.user)
        response = self.client.patch(self.url, {"first_name": "Alicia"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alicia")
        self.assertEqual(self.user.last_name, "Martin")

    def test_patch_ignores_read_only_fields(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            self.url, {"email": "hacker@example.com", "is_staff": True}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "alice@example.com")
        self.assertFalse(self.user.is_staff)

    def test_patch_rejects_blank_first_name(self):
        self.client.force_login(self.user)
        response = self.client.patch(self.url, {"first_name": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", response.data)

    def test_patch_requires_authentication(self):
        response = self.client.patch(self.url, {"first_name": "X"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_is_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.put(
            self.url, {"first_name": "A", "last_name": "B"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ChangePasswordAPITests(APITestCase):
    def setUp(self):
        self.url = reverse("accounts_api:change_password")
        self.user = User.objects.create_user(
            email="alice@example.com", password="S3cure-pass!",
            first_name="Alice", last_name="Martin",
        )
        self.payload = {
            "old_password": "S3cure-pass!",
            "new_password": "N3w-secure-pass!",
            "new_password_confirm": "N3w-secure-pass!",
        }
        self.client.force_login(self.user)

    def test_change_password_success(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("N3w-secure-pass!"))
        self.assertFalse(self.user.check_password("S3cure-pass!"))

    def test_user_stays_logged_in_after_change(self):
        self.client.post(self.url, self.payload, format="json")
        response = self.client.get(reverse("accounts_api:me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_wrong_old_password(self):
        self.payload["old_password"] = "not-my-password"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("S3cure-pass!"))

    def test_new_passwords_do_not_match(self):
        self.payload["new_password_confirm"] = "Different-pass1!"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password_confirm", response.data)

    def test_weak_new_password(self):
        self.payload["new_password"] = self.payload["new_password_confirm"] = "password"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("S3cure-pass!"))

    def test_new_password_must_differ_from_old(self):
        self.payload["new_password"] = self.payload["new_password_confirm"] = "S3cure-pass!"
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)

    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProfilePageTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:profile")
        self.user = User.objects.create_user(
            email="alice@example.com", password="S3cure-pass!",
            first_name="Alice", last_name="Martin",
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={self.url}"
        )

    def test_get_shows_the_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        self.assertContains(response, "alice@example.com")

    def test_post_updates_names_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, {"first_name": "Alicia", "last_name": "Dupont"}
        )

        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alicia")
        self.assertEqual(self.user.last_name, "Dupont")

    def test_post_blank_first_name_shows_error(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"first_name": "", "last_name": "Dupont"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("first_name", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alice")

    def test_email_cannot_be_changed_from_the_page(self):
        self.client.force_login(self.user)
        self.client.post(
            self.url,
            {"first_name": "Alice", "last_name": "Martin", "email": "other@example.com"},
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "alice@example.com")


class PasswordChangePageTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:password_change")
        self.user = User.objects.create_user(
            email="alice@example.com", password="S3cure-pass!",
            first_name="Alice", last_name="Martin",
        )
        self.data = {
            "old_password": "S3cure-pass!",
            "new_password1": "N3w-secure-pass!",
            "new_password2": "N3w-secure-pass!",
        }

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={self.url}"
        )

    def test_get_renders_the_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/password_change.html")

    def test_change_password_success_keeps_user_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.data)

        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("N3w-secure-pass!"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_wrong_old_password_shows_error(self):
        self.client.force_login(self.user)
        self.data["old_password"] = "not-my-password"
        response = self.client.post(self.url, self.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("old_password", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("S3cure-pass!"))

    def test_mismatched_new_passwords_show_error(self):
        self.client.force_login(self.user)
        self.data["new_password2"] = "Different-pass1!"
        response = self.client.post(self.url, self.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("new_password2", response.context["form"].errors)