# client.py - Klient szachowy z AI, znajomymi i losowym przeciwnikiem
import pygame
import socket
import threading
import time
import sys
import chess
import csv
import random
from chess.engine import SimpleEngine

pygame.init()
FONT = pygame.font.SysFont("Arial", 24)
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Online")
clock = pygame.time.Clock()

SERVER_IP = "13.38.13.177"
SERVER_PORT = 5555

username = ""
password = ""
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client_socket.connect((SERVER_IP, SERVER_PORT))
except Exception as e:
    print("Blad polaczenia z serwerem:", e)
    sys.exit()
piece_images = {}
def load_piece_images():
    pieces = ['wp','wr','wn','wb','wq','wk','bp','br','bn','bb','bq','bk']
    for p in pieces:
        path = os.path.join("pieces", f"{p}.png")
        piece_images[p] = pygame.transform.scale(pygame.image.load(path), (64, 64))
load_piece_images()

def send_to_server(data):
    try:
        client_socket.send(data.encode())
        return client_socket.recv(2048).decode()
    except:
        return "ERROR|Blad komunikacji"
def login_screen():
    global username, password
    username = "Buldozer"
    password = "123"
    send_to_server(f"LOGIN|{username}|{password}")

def draw_board(board):
    square_size = 64
    board_width = square_size * 8
    board_height = square_size * 8
    offset_x = (WIDTH - board_width) // 2
    offset_y = (HEIGHT - board_height) // 2

    colors = [(240, 217, 181), (181, 136, 99)]
    for rank in range(8):
        for file in range(8):
            rect = pygame.Rect(offset_x + file * square_size, offset_y + rank * square_size, square_size, square_size)
            color = colors[(rank + file) % 2]
            pygame.draw.rect(screen, color, rect)
            square = chess.square(file, 7 - rank)
            piece = board.piece_at(square)
            if piece:
                symbol = piece.symbol().lower()
                color_prefix = 'w' if piece.color == chess.WHITE else 'b'
                img = piece_images.get(color_prefix + symbol)
                if img:
                    img_rect = img.get_rect(center=rect.center)
                    screen.blit(img, img_rect)
def play_against_ai():
    board = chess.Board()
    selected_square = None
    running = True

    while running:
        screen.fill((30, 30, 30))
        draw_board(board)
        pygame.display.flip()

        if board.is_game_over():
            result = board.result()
            print("Gra zakonczona:", result)
            time.sleep(3)
            break

        if board.turn == chess.WHITE:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    file = (x - 100) // 60
                    rank = 7 - ((y - 50) // 60)
                    square = chess.square(file, rank)
                    if selected_square is None:
                        if board.piece_at(square) and board.piece_at(square).color == chess.WHITE:
                            selected_square = square
                    else:
                        move = chess.Move(selected_square, square)
                        if move in board.legal_moves:
                            board.push(move)
                        selected_square = None
        else:
            time.sleep(0.5)
            move = random.choice(list(board.legal_moves))
            board.push(move)
        clock.tick(30)

def launch_online_game(color, opponent):
    board = chess.Board()
    is_white = color == "white"
    selected_square = None
    running = True

    def receive_thread():
        nonlocal board
        while True:
            data = client_socket.recv(1024).decode()
            if data.startswith("OPPONENT_MOVE"):
                move = data.split("|")[1]
                board.push_uci(move)

    threading.Thread(target=receive_thread, daemon=True).start()

    while running:
        screen.fill((30, 30, 30))
        draw_board(board)
        pygame.display.flip()

        if board.is_game_over():
            result = board.result()
            send_to_server(f"GAME_OVER|{username}|{opponent}|{result}")
            time.sleep(3)
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if (board.turn == chess.WHITE and is_white) or (board.turn == chess.BLACK and not is_white):
                    x, y = event.pos
                    file = (x - 100) // 60
                    rank = 7 - ((y - 50) // 60)
                    square = chess.square(file, rank)
                    if selected_square is None:
                        if board.piece_at(square) and board.piece_at(square).color == board.turn:
                            selected_square = square
                    else:
                        move = chess.Move(selected_square, square)
                        if move in board.legal_moves:
                            board.push(move)
                            client_socket.send(f"MOVE|{opponent}|{move.uci()}".encode())
                        selected_square = None
        clock.tick(30)

def choose_opponent():
    while True:
        screen.fill((20, 20, 20))
        screen.blit(FONT.render("Wybierz przeciwnika", True, (255, 255, 255)), (WIDTH // 2 - 120, 50))
        pygame.draw.rect(screen, (100, 100, 250), (250, 120, 300, 40))
        screen.blit(FONT.render("Losowy gracz online", True, (0, 0, 0)), (270, 125))
        pygame.draw.rect(screen, (100, 200, 100), (250, 180, 300, 40))
        screen.blit(FONT.render("Zagraj z botem (AI)", True, (0, 0, 0)), (270, 185))
        pygame.draw.rect(screen, (200, 100, 100), (250, 240, 300, 40))
        screen.blit(FONT.render("Anuluj", True, (0, 0, 0)), (360, 245))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if 250 <= x <= 550:
                    if 120 <= y <= 160:
                        send_to_server("START_MATCH")
                        wait_for_match()
                        return
                    elif 180 <= y <= 220:
                        play_against_ai()
                        return
                    elif 240 <= y <= 280:
                        return
        clock.tick(30)

def draw_lobby():
    screen.fill((20, 20, 20))
    screen.blit(FONT.render(f"Witaj, {username}!", True, (255, 255, 255)), (50, 30))
    pygame.draw.rect(screen, (80, 80, 200), (50, 100, 200, 40))
    screen.blit(FONT.render("Szybki mecz online", True, (0, 0, 0)), (55, 110))
    pygame.draw.rect(screen, (80, 200, 100), (50, 160, 200, 40))
    screen.blit(FONT.render("Statystyki", True, (0, 0, 0)), (90, 170))
    pygame.draw.rect(screen, (200, 80, 80), (50, 220, 200, 40))
    screen.blit(FONT.render("Wyloguj", True, (0, 0, 0)), (115, 230))
    pygame.display.flip()

def lobby_screen():
    while True:
        draw_lobby()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if 50 <= event.pos[0] <= 250:
                    if 100 <= event.pos[1] <= 140:
                        choose_opponent()
                    elif 160 <= event.pos[1] <= 200:
                        stats_screen()
                    elif 220 <= event.pos[1] <= 260:
                        return
        clock.tick(30)


if __name__ == "__main__":
    login_screen()
    lobby_screen()
