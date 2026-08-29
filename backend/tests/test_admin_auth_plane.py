import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.admin import create_access_token, router as admin_router


class AdminAuthPlaneTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(admin_router)
        self.client = TestClient(app)

    def test_user_principal_token_cannot_access_admin_profile(self):
        token = create_access_token(
            data={
                "sub": "nina@wanderco.com",
                "principal_type": "user",
                "user_type": "operator",
            }
        )

        response = self.client.get(
            "/admin/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid or expired credentials", response.text)

    def test_invalid_admin_subject_id_returns_401_not_500(self):
        token = create_access_token(
            data={
                "sub": "not-an-object-id",
                "principal_type": "admin",
            }
        )

        response = self.client.get(
            "/admin/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid or expired credentials", response.text)


if __name__ == "__main__":
    unittest.main()
