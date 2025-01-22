from flask import Flask, render_template, redirect, request, flash, url_for, session
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db?timeout=10"
app.config["SECRET_KEY"] = "harsh"

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)

class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Winner is nullable initially
    game_date = db.Column(db.DateTime, default=datetime.utcnow)
    moves = db.Column(db.String(500))  # You can store moves in a string format or JSON

    player1 = db.relationship('User', foreign_keys=[player1_id])
    player2 = db.relationship('User', foreign_keys=[player2_id])
    winner = db.relationship('User', foreign_keys=[winner_id])

    def __repr__(self):
        return f'<GameHistory {self.id}>'


# Store active games
active_games = {}

@app.route("/")
def main():
    return render_template("welcome.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("game1"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.", "danger")
            return redirect(url_for("register"))
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("User registered successfully!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/game1")
def game1():
    return render_template("game1.html")

@app.route("/game_board")
def game_board():
    return render_template("game_board1.html")

# Event to create a new game
@socketio.on('create_game')
def handle_create_game():
    game_id = str(uuid.uuid4())  # Generate unique game ID
    active_games[game_id] = {
        'players': [],
        'current_turn': 'X',  # Start with Player 1 ('X')
        'symbols': {},
        'board': [None] * 9,  # Initialize 9 empty cells
        'status': 'waiting'  # Game is waiting for players
    }
    join_room(game_id)
    active_games[game_id]['players'].append(request.sid)  # Add Player 1 (socket ID)
    active_games[game_id]['symbols'][request.sid] = 'X'  # Assign Player 1 'X'
    emit('game_created', {'game_id': game_id, 'symbol': 'X'}, room=game_id)  # Emit the game_id so it's displayed
    print(f"Game created: {game_id}")

# Event to join a game
@socketio.on('join_game')
def handle_join_game(data):
    game_id = data.get('game_id')
    if game_id in active_games and len(active_games[game_id]['players']) < 2:
        join_room(game_id)
        active_games[game_id]['players'].append(request.sid)  # Add Player 2 (socket ID)
        active_games[game_id]['symbols'][request.sid] = 'O'  # Assign Player 2 'O'
        
        # Emit Player 2's symbol so they know their symbol
        emit('game_created', {'game_id': game_id, 'symbol': 'O'}, room=request.sid)  # Send Player 2 their symbol
        
        emit('player_joined', {'game_id': game_id, 'status': 'success', 'message': 'Player 2 joined'}, room=active_games[game_id]['players'][0])  # Notify Player 1
        emit('player_joined', {'game_id': game_id, 'status': 'success', 'message': 'Game Ready'}, room=request.sid)  # Notify Player 2

        # Start the game if both players are in
        if len(active_games[game_id]['players']) == 2:
            active_games[game_id]['status'] = 'in_progress'
            emit('start_game', {'message': 'Both players have joined. Game is starting! Player 1, your turn!'}, room=game_id)
            emit('redirect', {'url': '/game_board'}, room=game_id)  # Emit redirect event to both players
        print(f"Player joined game: {game_id}")
    else:
        emit('join_error', {'error': 'Invalid game ID or room is full.'}, room=request.sid)


# Event to handle player moves
@socketio.on('make_move')
def handle_move(data):
    game_id = data.get('game_id')
    try:
        move = int(data.get('move'))  # Ensure move is an integer
    except (ValueError, TypeError):
        emit('invalid_move', {'error': 'Invalid move. Move must be a number.'}, room=request.sid)
        return
    player_id = request.sid  # Get the player’s socket ID

    if game_id in active_games:
        game = active_games[game_id]

        # Ensure the game is in progress and it's the player's turn
        if game['status'] == 'over':
            emit('invalid_move', {'error': 'Game is over. No more moves allowed.'}, room=game_id)
            return

        if game['current_turn'] == game['symbols'][player_id]:
            # Process the move
            process_move(game_id, move, player_id)
        else:
            # It's not the player's turn
            emit('invalid_move', {'error': 'It is not your turn!'}, room=game_id)

# Function to process the move (you can implement game logic here)
def process_move(game_id, move, player_id):
    game = active_games.get(game_id)

    if not game:
        print(f"Game {game_id} not found.")
        return "Game not found"

    # Check if the move is valid (cell is empty)
    if game['board'][move] is not None:
        print(f"Invalid move. Cell {move} is already taken.")
        emit('invalid_move', {'error': f"Cell {move} is already taken."}, room=game_id)
        return

    # Update the game state
    symbol = game['symbols'][player_id]
    game['board'][move] = symbol
    print(f"Player {player_id} placed {symbol} at position {move}.")

    # Check for win or draw
    if check_win(game['board'], symbol):
        print(f"Emitting update_board event to room {game_id}")  # Debugging log
        emit('update_board', {'board': game['board'], 'current_turn': game['current_turn']}, room=game_id)
        game['status'] = 'over'
        game['winner'] = symbol
        print(f"Player {player_id} wins!")
        emit('game_over', {'winner': symbol}, room=game_id)
        save_game_history(game,player_id)
        emit('restart_game', {'message': 'Game Over. Restarting game...'}, room=game_id)  # Restart the game
        return

    if check_draw(game['board']):
        game['status'] = 'over'
        print("The game is a draw.")
        emit('game_over', {'message': 'The game is a draw.'}, room=game_id)
        emit('restart_game', {'message': 'Game Over. Restarting game...'}, room=game_id)  # Restart the game
        return

    # Switch to the next player's turn
    game['current_turn'] = 'O' if game['current_turn'] == 'X' else 'X'

    print(f"Now it's Player {game['current_turn']}'s turn.")

    # Emit updated board to all players in the room
    print(f"Emitting update_board event to room {game_id}")  # Debugging log
    emit('update_board', {'board': game['board'], 'current_turn': game['current_turn']}, room=game_id)

    # Save the updated game state (to a database or in-memory store)
    save_game_state(game)
    return "Move processed successfully."

def check_win(board, symbol):
    # Check all possible winning combinations
    winning_combinations = [
        [0, 1, 2],  # Row 1
        [3, 4, 5],  # Row 2
        [6, 7, 8],  # Row 3
        [0, 3, 6],  # Column 1
        [1, 4, 7],  # Column 2
        [2, 5, 8],  # Column 3
        [0, 4, 8],  # Diagonal 1
        [2, 4, 6]  # Diagonal 2
    ]

    for combo in winning_combinations:
        if all(board[i] == symbol for i in combo):
            return True
    return False

def check_draw(board):
    # If all cells are filled and no winner, it's a draw
    return all(cell is not None for cell in board)

def save_game_state(game):
    # Save the updated game state to the database or in-memory store
    # For demonstration, we'll just print the updated game state
    print("Game state updated:", game)

def save_game_history(game, winner_id):
    # Get the player IDs from the active game
    player1_id = game['players'][0]
    player2_id = game['players'][1]

    # Create a GameHistory record
    game_history = GameHistory(
        player1_id=player1_id,
        player2_id=player2_id,
        winner_id=winner_id,
        game_date=datetime.utcnow(),
        moves=str(game['board'])  # Or you can store the full move history
    )

    # Save the game history to the database
    db.session.add(game_history)
    db.session.commit()

    print(f"Game history saved: {game_history}")

if __name__ == '__main__':
    socketio.run(app, debug=True)
