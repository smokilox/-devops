from tests.conftest import *  # noqa: F401, F403 (если используешь хелперы, лучше импортировать явно)


def create_mountain(client, name="Эльбрус"):
    response = client.post(
        "/api/mountains",
        json={
            "name": name,
            "country": "Россия",
            "region": "Кавказ",
            "height_m": 5642,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_climber(client):
    response = client.post(
        "/api/climbers",
        json={
            "full_name": "Иванов Иван Иванович",
            "email": "ivanov@example.com",
            "birth_date": "2000-01-01",
            "experience_level": "intermediate",
            "medical_clearance": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_group(client, name="Группа 1"):
    response = client.post(
        "/api/groups",
        json={
            "name": name,
            "description": "Тестовая группа",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_ascent(client, mountain_id, group_id):
    response = client.post(
        "/api/ascents",
        json={
            "mountain_id": mountain_id,
            "group_id": group_id,
            "route_name": "Классический маршрут",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "notes": "Тестовое восхождение",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


def test_create_mountain(client):
    mountain = create_mountain(client)
    # ИСПРАВЛЕНО: не привязываемся к конкретному ID
    assert "id" in mountain
    assert mountain["name"] == "Эльбрус"


def test_create_mountain_invalid_height(client):
    response = client.post(
        "/api/mountains",
        json={
            "name": "Некорректная гора",
            "country": "Россия",
            "height_m": 0,
        },
    )
    assert response.status_code == 422


def test_ascent_invalid_dates(client):
    mountain = create_mountain(client)
    group = create_group(client)

    response = client.post(
        "/api/ascents",
        json={
            "mountain_id": mountain["id"],
            "group_id": group["id"],
            "start_date": "2026-09-05",
            "end_date": "2026-09-01",
        },
    )
    assert response.status_code == 422


def test_complete_ascent_without_participants(client):
    mountain = create_mountain(client)
    group = create_group(client)
    ascent = create_ascent(client, mountain["id"], group["id"])

    response = client.post(f"/api/ascents/{ascent['id']}/complete")
    assert response.status_code == 409


def test_full_flow(client):
    mountain = create_mountain(client)
    climber = create_climber(client)
    group = create_group(client)

    response = client.post(
        f"/api/groups/{group['id']}/climbers",
        json={
            "climber_id": climber["id"],
            "role": "leader",
        },
    )
    assert response.status_code == 201

    ascent = create_ascent(client, mountain["id"], group["id"])

    # Попытка создать отчёт до завершения восхождения
    response = client.post(
        "/api/reports",
        json={
            "ascent_id": ascent["id"],
            "title": "Итоговый отчёт",
            "summary": "Отчёт до завершения восхождения",
        },
    )
    assert response.status_code == 409

    # Завершаем восхождение
    response = client.post(f"/api/ascents/{ascent['id']}/complete")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # Создаём отчёт после завершения
    response = client.post(
        "/api/reports",
        json={
            "ascent_id": ascent["id"],
            "title": "Итоговый отчёт",
            "summary": "Восхождение завершено без происшествий",
        },
    )
    assert response.status_code == 201
