import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_courses(client: AsyncClient):
    response = await client.get("/api/v1/courses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(c["id"] == "COURSE-TEST-001" for c in data)


@pytest.mark.asyncio
async def test_create_course(client: AsyncClient):
    payload = {
        "id": "CYBER-001",
        "title": "Cybersecurity & Ethical Hacking",
        "description": "CEH and network security bootcamp",
        "full_price": 50000.0,
        "down_payment_amount": 6000.0,
        "currency": "INR",
    }
    response = await client.post("/api/v1/courses", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "CYBER-001"
    assert data["title"] == "Cybersecurity & Ethical Hacking"
    assert data["down_payment_amount"] == 6000.0


@pytest.mark.asyncio
async def test_create_duplicate_course_fails(client: AsyncClient):
    payload = {
        "id": "COURSE-TEST-001",
        "title": "Duplicate",
        "full_price": 1000.0,
        "down_payment_amount": 100.0,
    }
    response = await client.post("/api/v1/courses", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_root_dashboard(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "GUVI Payment Reminder Service" in response.text

