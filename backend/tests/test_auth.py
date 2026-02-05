"""
Tests for authentication endpoints.
"""
import pytest
from fastapi import status


@pytest.mark.unit
class TestLogin:
    """Test login functionality."""
    
    def test_login_success(self, client, admin_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_email(self, client):
        """Test login with invalid email."""
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@test.com", "password": "password"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_invalid_password(self, client, admin_user):
        """Test login with invalid password."""
        response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_inactive_user(self, client, db_session):
        """Test login with inactive user."""
        from app.models import User, Role
        from app.auth import get_password_hash
        
        inactive_user = User(
            email="inactive@test.com",
            name="Inactive User",
            password_hash=get_password_hash("password"),
            role=Role.ADMIN,
            is_active=False
        )
        db_session.add(inactive_user)
        db_session.commit()
        
        response = client.post(
            "/auth/login",
            json={"email": "inactive@test.com", "password": "password"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
class TestLogout:
    """Test logout functionality."""
    
    def test_logout_success(self, client, auth_headers):
        """Test successful logout."""
        response = client.post("/auth/logout", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Logged out successfully"


@pytest.mark.unit
class TestForgotPassword:
    """Test forgot password functionality."""
    
    def test_forgot_password_existing_email(self, client, admin_user):
        """Test forgot password with existing email."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "admin@test.com"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "password reset link" in response.json()["message"].lower()
    
    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with non-existent email (should still return success)."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@test.com"}
        )
        # Should return success to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestAuthFlow:
    """Test complete authentication flow."""
    
    def test_login_and_access_protected_route(self, client, admin_user):
        """Test login and accessing protected route."""
        # Login
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        
        # Access protected route
        headers = {"Authorization": f"Bearer {token}"}
        me_response = client.get("/users/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["email"] == "admin@test.com"
    
    def test_access_protected_route_without_token(self, client):
        """Test accessing protected route without token."""
        response = client.get("/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
