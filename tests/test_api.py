from fastapi.testclient import TestClient
from src.api import app


def register(client, email):
    response = client.post('/auth/register', json={'name': 'Test User', 'email': email, 'password': 'strong-pass-123'})
    if response.status_code == 409:
        response = client.post('/auth/login', json={'email': email, 'password': 'strong-pass-123'})
    assert response.status_code in (200, 201)
    return response.json()


def test_health():
    with TestClient(app) as client:
        assert client.get('/health').json() == {'status': 'ok'}


def test_rejects_unsupported_upload():
    with TestClient(app) as client:
        register(client, 'unsupported@example.com')
        response = client.post('/calls/upload', files={'file': ('notes.txt', b'not audio', 'text/plain')})
        assert response.status_code == 415


def test_upload_list_and_status_update():
    with TestClient(app) as client:
        register(client, 'status@example.com')
        created = client.post('/calls/upload', files={'file': ('demo.wav', b'RIFFdemo', 'audio/wav')})
        assert created.status_code == 201
        call_id = created.json()['id']
        assert client.get(f'/calls/{call_id}').status_code == 200
        changed = client.patch(f'/calls/{call_id}/status', json={'status': 'In Review'})
        assert changed.json()['status'] == 'In Review'


def test_human_edit_is_saved_and_audited():
    with TestClient(app) as client:
        register(client, 'edit@example.com')
        call = client.post('/calls/upload', files={'file': ('edit.wav', b'RIFFdemo', 'audio/wav')}).json()
        payload = {
            'caller_name': 'Fictional Customer', 'caller_phone': None, 'company_name': 'Demo Freight',
            'category': 'Shipment Tracking Inquiry', 'priority': 'High',
            'priority_reason': 'Delivery is expected today.', 'summary': 'Customer requested a status update.',
            'important_information': ['Shipment: 458'], 'recommended_next_action': 'Verify status and call back.',
            'missing_information': [], 'confidence_notes': [], 'transcript': 'Where is shipment 458?'
        }
        updated = client.patch(f"/calls/{call['id']}/analysis", json=payload)
        assert updated.status_code == 200
        assert updated.json()['caller_name'] == 'Fictional Customer'
        events = client.get(f"/calls/{call['id']}/events").json()
        assert any(event['event_type'] == 'human_edit' for event in events)


def test_uploaded_audio_can_be_streamed():
    with TestClient(app) as client:
        register(client, 'audio@example.com')
        call = client.post('/calls/upload', files={'file': ('playback.wav', b'RIFFdemo', 'audio/wav')}).json()
        response = client.get(f"/calls/{call['id']}/audio")
        assert response.status_code == 200
        assert response.content == b'RIFFdemo'


def test_upload_requires_login():
    with TestClient(app) as client:
        response = client.post('/calls/upload', files={'file': ('private.wav', b'RIFFdemo', 'audio/wav')})
        assert response.status_code == 401


def test_login_logout_flow():
    with TestClient(app) as client:
        register(client, 'login@example.com')
        assert client.get('/auth/me').status_code == 200
        assert client.post('/auth/logout').status_code == 204
        assert client.get('/auth/me').status_code == 401
        login = client.post('/auth/login', json={'email': 'login@example.com', 'password': 'strong-pass-123'})
        assert login.status_code == 200
        assert client.get('/auth/me').json()['email'] == 'login@example.com'


def test_calls_are_private_to_their_owner():
    with TestClient(app) as client:
        register(client, 'owner@example.com')
        call = client.post('/calls/upload', files={'file': ('owner.wav', b'RIFFdemo', 'audio/wav')}).json()
        client.post('/auth/logout')
        register(client, 'other@example.com')
        assert client.get(f"/calls/{call['id']}").status_code == 404
