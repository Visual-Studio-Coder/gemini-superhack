DROP TABLE IF EXISTS player;
DROP TABLE IF EXISTS room;

CREATE TABLE room (
    id SERIAL PRIMARY KEY,
    join_code VARCHAR(10) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'waiting', -- waiting, playing, finished
    events_json JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE player (
    id SERIAL PRIMARY KEY,
    room_id INTEGER REFERENCES room(id) ON DELETE CASCADE,
    username VARCHAR(50) NOT NULL,
    current_board JSONB DEFAULT '{}', -- 5x5 grid state
    points INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
