import sys
import traceback
from app import app, get_user_id
import json

with app.test_client() as client:
    response = client.post('/chat', json={
        "message": "hOi",
        "session_id": "test_session_123"
    }, headers={"Authorization": "Bearer fake_token"})
    print("Status:", response.status_code)
    print("Data:", response.get_data(as_text=True))
