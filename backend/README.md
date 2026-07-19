# Game Backend API

Flask backend for the multiplayer game with PostgreSQL database.

## 🚀 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Database Setup

Make sure you have PostgreSQL installed and running.

Create the database and tables:

```sql
-- Create database
CREATE DATABASE game_db;

-- Connect to the database
\c game_db

-- Create room table
CREATE TABLE room (
    id SERIAL PRIMARY KEY,
    join_code TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting',
    events_json JSON DEFAULT '[]'
);

-- Create player table
CREATE TABLE player (
    id SERIAL PRIMARY KEY,
    room_id INTEGER REFERENCES room(id) ON DELETE CASCADE,
    current_board JSON DEFAULT '{}',
    points INTEGER DEFAULT 0
);

-- Create indexes
CREATE INDEX idx_room_join_code ON room(join_code);
CREATE INDEX idx_player_room_id ON player(room_id);
```

### 3. Configure Environment

Copy `env.example` to `.env` and update with your database credentials:

```bash
cp env.example .env
```

Edit `.env`:
```
DB_HOST=localhost
DB_NAME=game_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432
```

### 4. Run the Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

## 📡 API Endpoints

### Health Check
```
GET /health
```
Returns server status.

### Create Room
```
POST /api/create-room
Content-Type: application/json

{
  "username": "PlayerName"
}
```

Response:
```json
{
  "room_id": 1,
  "player_id": 1,
  "join_code": "ABC123",
  "username": "PlayerName"
}
```

### Join Room
```
POST /api/join-room
Content-Type: application/json

{
  "room_code": "ABC123",
  "username": "PlayerName"
}
```

Response:
```json
{
  "room_id": 1,
  "player_id": 2,
  "join_code": "ABC123",
  "username": "PlayerName",
  "status": "waiting"
}
```

### Get Room Details
```
GET /api/room/{room_id}
```

Response:
```json
{
  "room": {
    "id": 1,
    "join_code": "ABC123",
    "status": "waiting",
    "events_json": []
  },
  "players": [
    {
      "id": 1,
      "room_id": 1,
      "current_board": {},
      "points": 0
    }
  ]
}
```

### Get Player Details
```
GET /api/player/{player_id}
```

### Update Player Board
```
PUT /api/player/{player_id}/board
Content-Type: application/json

{
  "current_board": {
    "tiles": [...],
    "moves": 5
  }
}
```

### Update Player Points
```
PUT /api/player/{player_id}/points
Content-Type: application/json

{
  "points": 100
}
```

### Update Room Status
```
PUT /api/room/{room_id}/status
Content-Type: application/json

{
  "status": "playing"
}
```

Valid statuses: `waiting`, `playing`, `finished`

## 🗄️ Database Schema

### `room` table
- `id` (SERIAL PRIMARY KEY)
- `join_code` (TEXT UNIQUE) - 6-character room code
- `status` (TEXT) - Room status: waiting, playing, finished
- `events_json` (JSON) - Game events log

### `player` table
- `id` (SERIAL PRIMARY KEY)
- `room_id` (INTEGER) - Foreign key to room
- `current_board` (JSON) - Player's current game state
- `points` (INTEGER) - Player's score

## 🔧 Development

### Enable Debug Mode

The server runs with `debug=True` by default for development.

### CORS

CORS is enabled for all origins to allow the frontend to connect.

For production, update the CORS configuration in `app.py`:

```python
CORS(app, origins=["https://yourdomain.com"])
```

## 🐛 Troubleshooting

### Database Connection Error

Make sure PostgreSQL is running:
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql
```

### Port Already in Use

Change the port in `app.py`:
```python
app.run(debug=True, host="0.0.0.0", port=5001)
```

### Import Error

Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## 📦 Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
