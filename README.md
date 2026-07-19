# Gemini Hackathon - Multiplayer Game

A real-time multiplayer game with Next.js frontend and Flask backend.

## 🏗️ Project Structure

```
Gemini-Hackathon/
├── superhack/          # Next.js frontend
│   ├── app/           # App router pages
│   ├── components/    # shadcn/ui components
│   └── package.json
└── backend/           # Flask API
    ├── app.py         # Main API server
    ├── requirements.txt
    └── README.md
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- Python 3.8+
- PostgreSQL 12+

### 1. Setup Database

```bash
# Create database
createdb game_db

# Or using psql
psql postgres
CREATE DATABASE game_db;
\q
```

Create tables:

```sql
psql game_db

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

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure database (create .env file)
cp env.example .env
# Edit .env with your database credentials

# Run server
python app.py
```

Backend runs on `http://localhost:5000`

### 3. Setup Frontend

```bash
cd superhack

# Install dependencies
npm install

# Create .env.local for API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:5000" > .env.local

# Run development server
npm run dev
```

Frontend runs on `http://localhost:3000`

## 🎮 How to Play

1. **Start the backend**: Make sure Flask server is running on port 5000
2. **Start the frontend**: Next.js dev server on port 3000
3. **Join a game**:
   - Enter a room code (6 characters, e.g., "ABC123")
   - Enter your username
   - Click "Submit"
4. **Create a new room**: Use the backend API to create rooms

## 📡 API Endpoints

### Join Room
```bash
curl -X POST http://localhost:5000/api/join-room \
  -H "Content-Type: application/json" \
  -d '{"room_code": "ABC123", "username": "Player1"}'
```

### Create Room
```bash
curl -X POST http://localhost:5000/api/create-room \
  -H "Content-Type: application/json" \
  -d '{"username": "Player1"}'
```

### Get Room Details
```bash
curl http://localhost:5000/api/room/1
```

See `backend/README.md` for complete API documentation.

## 🗄️ Database Schema

### Room Table
- `id` - Unique room identifier
- `join_code` - 6-character code to join room
- `status` - Room status (waiting, playing, finished)
- `events_json` - JSON array of game events

### Player Table
- `id` - Unique player identifier
- `room_id` - Foreign key to room
- `current_board` - JSON object of player's board state
- `points` - Player's score

## 🎨 Frontend Features

- ✅ Clean, simple UI with shadcn/ui components
- ✅ Room code and username inputs
- ✅ Form validation
- ✅ Error handling
- ✅ Loading states
- ✅ Dark mode support
- ✅ Responsive design
- ✅ Real-time room updates (polling every 2s)

## 🔧 Backend Features

- ✅ RESTful API with Flask
- ✅ PostgreSQL database integration
- ✅ CORS enabled for frontend
- ✅ Room creation with unique join codes
- ✅ Player management
- ✅ Room status tracking
- ✅ Error handling

## 🛠️ Tech Stack

### Frontend
- **Next.js 16** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS v4** - Styling
- **shadcn/ui** - UI components

### Backend
- **Flask** - Python web framework
- **PostgreSQL** - Database
- **psycopg2** - PostgreSQL adapter
- **Flask-CORS** - CORS support

## 📝 Development

### Frontend Development

```bash
cd superhack
npm run dev          # Start dev server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Lint code
```

### Backend Development

```bash
cd backend
source venv/bin/activate
python app.py        # Run with debug mode
```

## 🐛 Troubleshooting

### Database Connection Failed
- Check PostgreSQL is running: `pg_isready`
- Verify credentials in `.env`
- Ensure database exists: `psql -l | grep game_db`

### Frontend Can't Connect to Backend
- Check backend is running on port 5000
- Verify `NEXT_PUBLIC_API_URL` in `.env.local`
- Check CORS is enabled in backend

### Port Already in Use
- Backend: Change port in `app.py`
- Frontend: Use `PORT=3001 npm run dev`

## 🚀 Deployment

### Backend (Railway/Render/Heroku)
1. Add `Procfile`: `web: gunicorn app:app`
2. Set environment variables
3. Deploy

### Frontend (Vercel/Netlify)
1. Set `NEXT_PUBLIC_API_URL` environment variable
2. Deploy from GitHub
3. Done!

## 📄 License

MIT License

## 👥 Contributors

Built for the Gemini Hackathon