import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_register():
    data = {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "testpass123"
    }
    response = requests.post(f"{BASE_URL}/register/", json=data)
    print("Register Response:", response.status_code)
    print("Response:", response.json())
    return response

def test_login():
    data = {
        "username": "testuser2",
        "password": "testpass123"
    }
    response = requests.post(f"{BASE_URL}/login/", json=data)
    print("Login Response:", response.status_code)
    print("Response:", response.json())
    return response

def test_puzzle(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/game/question/", headers=headers)
    print("Game Question Response:", response.status_code)
    print("Response:", response.json())
    return response

def test_check_answer(token, puzzle_id, answer):
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "puzzle_id": puzzle_id,
        "answer": answer,
        "time_taken": 30
    }
    response = requests.post(f"{BASE_URL}/game/answer/", json=data, headers=headers)
    print("Game Answer Response:", response.status_code)
    print("Response:", response.json())
    return response

def test_game_history(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/game/history/", headers=headers)
    print("Game History Response:", response.status_code)
    print("Response:", response.json())
    return response

if __name__ == "__main__":
    # Test registration
    reg_response = test_register()

    # Test login
    login_response = test_login()
    if login_response.status_code == 200:
        token = login_response.json()['access']

        # Test getting puzzle
        puzzle_response = test_puzzle(token)
        if puzzle_response.status_code == 200:
            puzzle_id = puzzle_response.json()['puzzle_id']

            # Test checking answer
            test_check_answer(token, puzzle_id, "4")  # Assuming the sample puzzle answer
