from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Account


class SignupViewTest(TestCase):
    """
    Test cases for the Signup view.
    """

    def test_signup_get(self):
        """
        Test the GET request to the register view.
        - Verifies that the response status code is 200.
        - Checks that the correct template is used.
        """
        url = reverse("account_signup")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/signup.html")

    def test_signup_post(self):
        """
        Test the POST request to the signup view.
        - Checks that a new user is created after a successful registration.
        - Verifies that the response status code is 302 (redirect).
        """
        users = User.objects.all().count()
        self.assertEqual(users, 0)
        url = reverse("account_signup")
        response = self.client.post(
            url,
            {
                "email": "test@test.com",
                "password1": "testpassword",
                "password2": "testpassword",
            },
        )
        self.assertRedirects(
            response, reverse("dashboard"), fetch_redirect_response=True
        )
        users = User.objects.all().count()
        self.assertEqual(users, 1)

    def test_login_get(self):
        """
        Test the GET request to the login view.
        - Verifies that the response status code is 200.
        - Checks that the correct template is used.
        """
        url = reverse("account_login")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")

    def test_login_post(self):
        """
        Test the POST request to the login view.
        - Checks that a new user is created after a successful registration.
        - Verifies that the response status code is 302 (redirect).
        """
        user = User.objects.create_user(
            username="TestUser", email="test@test.com", password="testpassword"
        )
        user.account = Account()
        user.account.save()

        url = reverse("account_login")
        response = self.client.post(
            url,
            {
                "login": "test@test.com",
                "password": "testpassword",
            },
        )
        self.assertRedirects(
            response, reverse("dashboard"), fetch_redirect_response=True
        )


class SettingsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )
        self.user.account = Account()
        self.user.account.save()
        self.client.login(username="TestUser", password="testpassword")

    def test_get_settings(self):
        url = reverse("settings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
