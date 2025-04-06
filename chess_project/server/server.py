# server.py – Pełny serwer gry szachowej online z rejestracją, znajomymi, historią
import socket
import threading
import json
import os

HOST = '0.0.0.0'
PORT = 5555

USERS_FILE = 'users.json'
clients = {}  # username -> conn
waiting_players = []  # queue for matchmaking
friend_invites = {}  # username -> invited friend

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def register(username, password):
    users = load_users()
    if username in users:
        return False, "Uzytkownik juz istnieje."
    users[username] = {"password": password, "friends": [], "requests": [], "history": []}
    save_users(users)
    return True, "Zarejestrowano."

def login(username, password):
    users = load_users()
    if username not in users:
        return False, "Brak konta."
    if users[username]['password'] != password:
        return False, "Zle haslo."
    return True, "Zalogowano."

def record_game(player1, player2, result):
    users = load_users()
    for p in [player1, player2]:
        if p in users:
            users[p].setdefault("history", []).append({"vs": player2 if p == player1 else player1, "result": result})
    save_users(users)

def handle_client(conn, addr):
    print(f"[Polaczono] {addr}")
    username = None
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            parts = data.split("|")
            command = parts[0]

            if command == 'REGISTER':
                success, msg = register(parts[1], parts[2])
                conn.send(f"REGISTER_RESPONSE|{msg}".encode())

            elif command == 'LOGIN':
                success, msg = login(parts[1], parts[2])
                if success:
                    username = parts[1]
                    clients[username] = conn
                conn.send(f"LOGIN_RESPONSE|{msg}".encode())

            elif command == 'FRIEND_REQUEST':
                target = parts[1]
                users = load_users()
                if target in users:
                    if username not in users[target]['requests']:
                        users[target]['requests'].append(username)
                    save_users(users)
                    conn.send(f"FRIEND_RESPONSE|Wyslano zaproszenie".encode())
                else:
                    conn.send(f"FRIEND_RESPONSE|Nie znaleziono gracza".encode())

            elif command == 'GET_REQUESTS':
                users = load_users()
                requests = users[username]['requests']
                conn.send(f"REQUESTS|{','.join(requests)}".encode())

            elif command == 'ACCEPT_REQUEST':
                friend = parts[1]
                users = load_users()
                if friend in users[username]['requests']:
                    users[username]['requests'].remove(friend)
                    if friend not in users[username]['friends']:
                        users[username]['friends'].append(friend)
                    if username not in users[friend]['friends']:
                        users[friend]['friends'].append(username)
                    save_users(users)
                    conn.send(f"FRIEND_RESPONSE|Dodano do znajomych".encode())

            elif command == 'GET_FRIENDS':
                users = load_users()
                friends = users[username]['friends']
                conn.send(f"FRIENDS|{','.join(friends)}".encode())

            elif command == 'INVITE':
                target = parts[1]
                if target in clients:
                    friend_invites[target] = username
                    clients[target].send(f"INVITE_RECEIVED|{username}".encode())

            elif command == 'ACCEPT_INVITE':
                inviter = parts[1]
                if inviter in clients and username in friend_invites and friend_invites[username] == inviter:
                    clients[inviter].send(f"MATCH_START|white|{username}".encode())
                    conn.send(f"MATCH_START|black|{inviter}".encode())
                    del friend_invites[username]

            elif command == 'START_MATCH':
                waiting_players.append((username, conn))
                if len(waiting_players) >= 2:
                    p1 = waiting_players.pop(0)
                    p2 = waiting_players.pop(0)
                    p1[1].send(f"MATCH_START|white|{p2[0]}".encode())
                    p2[1].send(f"MATCH_START|black|{p1[0]}".encode())

            elif command == 'MOVE':
                opponent = parts[1]
                move = parts[2]
                if opponent in clients:
                    clients[opponent].send(f"OPPONENT_MOVE|{move}".encode())

            elif command == 'GAME_OVER':
                p1, p2, result = parts[1], parts[2], parts[3]
                record_game(p1, p2, result)
                for p in [p1, p2]:
                    if p in clients:
                        clients[p].send(f"GAME_RECORDED|{result}".encode())

            elif command == 'GET_HISTORY':
                users = load_users()
                history = users.get(username, {}).get("history", [])
                formatted = ";".join([f"vs {h['vs']} - {h['result']}" for h in history])
                conn.send(f"HISTORY|{formatted}".encode())

    except Exception as e:
        print(f"[Blad] {e}")
    finally:
        print(f"[Rozlaczenie] {addr}")
        if username and username in clients:
            del clients[username]
        conn.close()

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[Serwer] Nasluchuje na {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()
