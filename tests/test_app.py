import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


@pytest.fixture
def client_with_fresh_data():
    """Fixture to reset activities before each test"""
    from app import activities
    
    # Save original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield client
    
    # Restore original state
    for name, original_details in original_activities.items():
        activities[name]["participants"] = original_details["participants"].copy()


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""
    
    def test_get_activities(self):
        """Test that activities endpoint returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Basketball Team" in data
        assert "Tennis Club" in data
        assert len(data) > 0
    
    def test_activities_have_required_fields(self):
        """Test that each activity has all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_new_participant(self, client_with_fresh_data):
        """Test signing up a new participant"""
        response = client_with_fresh_data.post(
            "/activities/Basketball%20Team/signup?email=newyear@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newyear@mergington.edu" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client_with_fresh_data):
        """Test that signup actually adds participant to the list"""
        response = client_with_fresh_data.post(
            "/activities/Basketball%20Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        activities_response = client_with_fresh_data.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Basketball Team"]["participants"]
    
    def test_signup_duplicate_participant(self, client_with_fresh_data):
        """Test that signing up the same participant twice fails"""
        # First signup should succeed
        response1 = client_with_fresh_data.post(
            "/activities/Basketball%20Team/signup?email=duplicate@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client_with_fresh_data.post(
            "/activities/Basketball%20Team/signup?email=duplicate@mergington.edu"
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_nonexistent_activity(self, client_with_fresh_data):
        """Test signup for activity that doesn't exist"""
        response = client_with_fresh_data.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_signup_with_empty_email(self, client_with_fresh_data):
        """Test signup with empty email"""
        response = client_with_fresh_data.post(
            "/activities/Basketball%20Team/signup?email="
        )
        # Should either fail validation or succeed with empty email
        # Depends on validation rules - checking it's handled
        assert response.status_code in [200, 422]


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""
    
    def test_unregister_existing_participant(self, client_with_fresh_data):
        """Test unregistering an existing participant"""
        # First, sign up a participant
        client_with_fresh_data.post(
            "/activities/Basketball%20Team/signup?email=unregister_test@mergington.edu"
        )
        
        # Then unregister them
        response = client_with_fresh_data.post(
            "/activities/Basketball%20Team/unregister?email=unregister_test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client_with_fresh_data):
        """Test that unregister actually removes participant"""
        # Sign up
        client_with_fresh_data.post(
            "/activities/Tennis%20Club/signup?email=removed@mergington.edu"
        )
        
        # Unregister
        client_with_fresh_data.post(
            "/activities/Tennis%20Club/unregister?email=removed@mergington.edu"
        )
        
        # Verify removed
        activities_response = client_with_fresh_data.get("/activities")
        activities_data = activities_response.json()
        assert "removed@mergington.edu" not in activities_data["Tennis Club"]["participants"]
    
    def test_unregister_nonexistent_participant(self, client_with_fresh_data):
        """Test unregistering a participant not in the activity"""
        response = client_with_fresh_data.post(
            "/activities/Basketball%20Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]
    
    def test_unregister_nonexistent_activity(self, client_with_fresh_data):
        """Test unregister for activity that doesn't exist"""
        response = client_with_fresh_data.post(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirect(self):
        """Test that root endpoint redirects to index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
