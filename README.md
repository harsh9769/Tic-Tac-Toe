# Tic-Tac-Toe Game with Flask and SocketIO

A real-time multiplayer Tic-Tac-Toe game built with Flask, Socket.IO, and SQLAlchemy. Players can register, log in, create a game, join an existing game, and play together.

## Features:
- User registration and login
- Create and join games
- Real-time game updates using Socket.IO
- Stores game history in SQLite database
- Basic error handling and validation

## Installation:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/tic-tac-toe.git


2. Navigate to the project folder:

    cd tic-tac-toe


3. Install dependencies:

    pip install -r requirements.txt

4. Set up the database:

        python
    >>> from app import db
    >>> db.create_all()

        OR 
    Run the create.py to create the DB

5. Running the App:

    python app.py


Routes:
/ - Welcome page
/login - Login page
/register - Register page
/game1 - Create or join a game
/game_board - The game board page


Socket.IO Events:
create_game - Create a new game
join_game - Join an existing game
make_move - Make a move
game_over - End the game when a winner is determined
update_board - Update the game board in real-time

Database:
Uses SQLite to store users and game history:

User: Stores username and hashed password
GameHistory: Stores game moves and the winner
License:
MIT License

Contact:
For questions, open an issue on this repo or email directly.

css
Copy
Edit

This one-page summary condenses the project’s key details, installation, usage, and routes. You can expand it further if needed!






