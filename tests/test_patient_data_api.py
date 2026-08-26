import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth_header(username: str = "patient_demo", password: str = "patient_pass"):
    res = client.post("/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def get_admin_header():
    res = client.post("/auth/login", data={"username": "admin_demo", "password": "admin_pass"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_patient_endpoints_return_401():
    endpoints = [
        ("GET", "/vitals/me"),
        ("POST", "/vitals/me"),
        ("GET", "/medications/me"),
        ("GET", "/reminders/me"),
        ("POST", "/reminders/me"),
        ("POST", "/reminders/1/cancel"),
    ]
    for method, endpoint in endpoints:
        if method == "GET":
            res = client.get(endpoint)
        else:
            res = client.post(endpoint, json={})
        assert res.status_code == 401, f"{method} {endpoint} should return 401 unauthenticated"


def test_admin_patient_endpoints_return_403():
    headers = get_admin_header()
    endpoints = [
        ("GET", "/vitals/me"),
        ("POST", "/vitals/me"),
        ("GET", "/medications/me"),
        ("GET", "/reminders/me"),
        ("POST", "/reminders/me"),
        ("POST", "/reminders/1/cancel"),
    ]
    for method, endpoint in endpoints:
        if method == "GET":
            res = client.get(endpoint, headers=headers)
        else:
            res = client.post(endpoint, json={}, headers=headers)
        assert res.status_code == 403, f"{method} {endpoint} should return 403 for admin"


def test_patient_can_get_medications():
    headers = get_auth_header()
    res = client.get("/medications/me", headers=headers)
    assert res.status_code == 200
    meds = res.json()
    assert isinstance(meds, list)
    assert len(meds) >= 2
    med_names = [m["name"] for m in meds]
    assert "Lisinopril" in med_names
    assert "Vitamin D3" in med_names


def test_patient_can_get_and_post_vitals():
    headers = get_auth_header()
    
    # 1. GET initial vitals
    res = client.get("/vitals/me", headers=headers)
    assert res.status_code == 200
    initial_count = len(res.json())

    # 2. POST new valid vital
    post_res = client.post(
        "/vitals/me",
        json={"vital_type": "spo2", "value": "99", "unit": "%"},
        headers=headers
    )
    assert post_res.status_code == 201
    vital_data = post_res.json()
    assert vital_data["vital_type"] == "spo2"
    assert vital_data["value"] == "99"

    # 3. GET filtered vitals by vital_type
    filtered_res = client.get("/vitals/me?vital_type=spo2", headers=headers)
    assert filtered_res.status_code == 200
    spo2_list = filtered_res.json()
    assert len(spo2_list) >= 1
    assert all(v["vital_type"] == "spo2" for v in spo2_list)

    # 4. POST invalid vital_type -> 400 Bad Request
    bad_res = client.post(
        "/vitals/me",
        json={"vital_type": "invalid_vital_name", "value": "100"},
        headers=headers
    )
    assert bad_res.status_code == 400
    assert "Invalid vital_type" in bad_res.json()["detail"]


def test_patient_reminders_crud_flow_and_cross_patient_isolation():
    # 1. Register and login Patient A
    username_a = "api_patient_a"
    password_a = "password_a"
    client.post("/auth/register", json={"username": username_a, "password": password_a, "role": "patient"})
    login_a = client.post("/auth/login", data={"username": username_a, "password": password_a})
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    client.post("/patients/me", json={"first_name": "Alice", "last_name": "A"}, headers=headers_a)

    # 2. Register and login Patient B
    username_b = "api_patient_b"
    password_b = "password_b"
    client.post("/auth/register", json={"username": username_b, "password": password_b, "role": "patient"})
    login_b = client.post("/auth/login", data={"username": username_b, "password": password_b})
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    client.post("/patients/me", json={"first_name": "Bob", "last_name": "B"}, headers=headers_b)

    # 3. Patient A creates a reminder
    rem_a_res = client.post(
        "/reminders/me",
        json={"reminder_text": "Take Evening Medicine", "reminder_time": "09:00 PM"},
        headers=headers_a
    )
    assert rem_a_res.status_code == 201
    reminder_a = rem_a_res.json()
    rem_id_a = reminder_a["id"]
    assert reminder_a["status"] == "active"

    # 4. Cross-patient security check: Patient B attempts to cancel Patient A's reminder -> 404
    cross_cancel_res = client.post(f"/reminders/{rem_id_a}/cancel", headers=headers_b)
    assert cross_cancel_res.status_code == 404

    # 5. Non-existent reminder cancellation -> 404
    non_existent_res = client.post("/reminders/999999/cancel", headers=headers_a)
    assert non_existent_res.status_code == 404

    # 6. Patient A cancels own reminder -> 200 OK
    cancel_res = client.post(f"/reminders/{rem_id_a}/cancel", headers=headers_a)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"
