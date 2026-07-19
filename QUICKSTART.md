# 🚀 Quick Start Guide

Get the game running in 5 minutes!

## Prerequisites

- PostgreSQL installed and running
- Python 3.8+
- Node.js 18+

## Step 1: Database Setup (2 minutes)

```bash
# Create database
createdb game_db

# Create tables
psql game_db << EOF
CREATE TABLE room (
    id SERIAL PRIMARY KEY,
    join_code TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting',
    events_json JSON DEFAULT '[]'
);

CREATE TABLE player (
    id SERIAL PRIMARY KEY,
    room_id INTEGER REFERENCES room(id) ON DELETE CASCADE,
    current_board JSON DEFAULT '{}',
    points INTEGER DEFAULT 0
);

CREATE INDEX idx_room_join_code ON room(join_code);
CREATE INDEX idx_player_room_id ON player(room_id);
EOF
```

## Step 2: Backend Setup (1 minute)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (or just use defaults)
echo "DB_HOST=localhost" > .env
echo "DB_NAME=game_db" >> .env
echo "DB_USER=postgres" >> .env
echo "DB_PASSWORD=postgres" >> .env
echo "DB_PORT=5432" >> .env

# Run server
python app.py
```

Backend now running on **http://localhost:5000** ✅

## Step 3: Frontend Setup (2 minutes)

Open a new terminal:

```bash
cd superhack

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:5000" > .env.local

# Run dev server
npm run dev
```

Frontend now running on **http://localhost:3000** ✅

## Step 4: Play! 🎮

1. **Open** http://localhost:3000
2. **Enter your username** (e.g., "Player1")
3. **Click "Create New Room"** - You'll get a 6-character room code!
4. **Share the room code** with friends
5. Friends can **join** by entering the code

## Test It Yourself

Open two browser windows:

### Window 1 (Host):
1. Go to http://localhost:3000
2. Username: "Alice"
3. Click "Create New Room"
4. Note the room code (e.g., "ABC123")

### Window 2 (Guest):
1. Go to http://localhost:3000
2. Username: "Bob"
3. Room Code: "ABC123"
4. Click "Join Room"

Both players now in the same room! 🎉

## Troubleshooting

### Backend won't start?
- Check PostgreSQL is running: `pg_isready`
- Check port 5000 is free: `lsof -i :5000`
- Verify database exists: `psql -l | grep game_db`

### Frontend won't connect?
- Verify backend is running on port 5000
- Check `.env.local` has correct API URL
- Try restarting both servers

### Database connection failed?
- Update `.env` with correct credentials
- Test connection: `psql game_db -c "SELECT 1;"`

## What's Next?

- Host clicks "Start Game" to begin
- Add your game logic to the game board area
- Use the player and room API endpoints to save game state

## API Quick Reference

```bash
# Create room
curl -X POST http://localhost:5000/api/create-room \
  -H "Content-Type: application/json" \
  -d '{"username": "Player1"}'

# Join room
curl -X POST http://localhost:5000/api/join-room \
  -H "Content-Type: application/json" \
  -d '{"room_code": "ABC123", "username": "Player2"}'

# Get room details
curl http://localhost:5000/api/room/1

# Update room status (host only in your game)
curl -X PUT http://localhost:5000/api/room/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "playing"}'
```

## Features Included ✨

- ✅ Create room functionality
- ✅ Join room with code
- ✅ Host/guest roles
- ✅ Real-time room updates (polls every 2s)
- ✅ Player list display
- ✅ Points tracking
- ✅ Room status management
- ✅ Dark mode support

Now start building your game! 🎮