# Chess Web App

A full-stack chess web application built from a custom Python chess engine, wrapped with a FastAPI backend and served through a React + Vite frontend. The app allows users to play against the engine as either white or black, adjust the engine move time, undo moves, and run the project locally or deploy it through Vercel.

## Overview

This project began as a Python chess engine and was later adapted into a browser-based application. The original engine modules remain in the backend, while the web interface communicates with the engine through a FastAPI API.

The project demonstrates:

- Python game logic and chess rule implementation
- Backend API development using FastAPI
- Frontend development with React and Vite
- Full-stack project structure
- Local development and deployment workflow
- Practical software refactoring from a local program into a web application

## Features

- Play a full game of chess against the engine
- Choose to play as white or black
- Engine automatically responds after the user's move
- Adjustable engine move time
- Undo support, taking back the user's move and the engine's reply
- Browser-based board using Unicode chess pieces
- FastAPI backend with interactive API documentation
- React + Vite frontend
- Vercel deployment configuration

## Project Structure

```text
.
├── backend/
│   ├── config_w.py
│   ├── engine_w.py
│   ├── moves_w.py
│   ├── notation_w.py
│   ├── state_w.py
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── api/
│   └── index.py
├── vercel.json
└── README.md
```

### Backend

The backend contains the original Python chess engine files, with `main.py` acting as the FastAPI wrapper. The API exposes routes that allow the frontend to retrieve the game state, submit moves, reset the board, undo moves, and configure engine behaviour.

### Frontend

The frontend is a React + Vite application. It renders the chessboard, handles user interaction, displays game information, and communicates with the backend API.

### Deployment

The root `vercel.json` file is configured so the project can be deployed from the repository root. The frontend is built from the `frontend/` directory, while API requests are routed to the FastAPI app through `api/index.py`.

## Running the Project Locally

You will need two terminals: one for the backend and one for the frontend.

### 1. Run the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The backend will run at:

```text
http://localhost:8000
```

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

### 2. Run the Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will usually run at:

```text
http://localhost:5173
```

The frontend sends API requests to the local backend during development.

## Deployment to Vercel

Deploy the project from the repository root, not from the `frontend/` directory.

The deployment setup is designed so that:

- Vercel builds the React frontend from `frontend/`
- The built frontend is served as the main web app
- Requests to `/api/*` are routed to the Python backend through `api/index.py`
- In production, the frontend calls the same Vercel origin for API requests

This allows routes such as `/api/state` to be handled by the deployed backend function.

## How the Application Works

### Single Shared Game State

The current backend stores the game state using module-level globals in `state_w.py`. This works well for a single user playing in one browser tab.

For a multi-user version, the game state would need to be refactored into separate game instances, with each game identified by a unique game ID.

### Chess Pieces

The app uses Unicode chess symbols, such as `♔`, `♕`, `♖`, `♗`, `♘`, and `♙`, rather than image files. These are mapped in:

```text
frontend/src/pieces.js
```

Using Unicode pieces keeps the project lightweight and avoids the need for image assets. Custom piece images could be added by editing `pieces.js` and the relevant CSS in `styles.css`.

### Pawn Promotion

Pawns currently auto-promote to queens. This matches the existing behaviour in the engine.

A future improvement would be to add underpromotion by passing a `promotion` field through the move request and updating the backend move-handling logic.

### Undo Behaviour

Undo reverses the user's previous move and the engine's response, so that after undoing it is again the user's turn.

### Engine Move Time

The engine move time can be adjusted from the sidebar. Increasing the move time usually allows the engine to search more deeply, improving move quality at the cost of speed.

## Technical Notes

The original engine files are preserved in the backend:

- `config_w.py` stores constants, board setup, piece values, and configuration
- `engine_w.py` contains the chess engine logic
- `moves_w.py` handles move generation and rule validation
- `notation_w.py` manages chess notation
- `state_w.py` stores live game state and move history

The web version adds:

- `backend/main.py` for the FastAPI API layer
- `frontend/` for the browser interface
- `api/index.py` for Vercel serverless routing
- `vercel.json` for deployment configuration

## Future Improvements

Potential future improvements include:

- Independent game sessions for multiple users
- Online multiplayer support
- User-selectable pawn promotion
- Stronger engine optimisation
- Improved opening book support
- Move history display with algebraic notation
- Board themes and custom piece sets
- User accounts and saved games
- Difficulty levels or engine depth presets

## Skills Demonstrated

This project demonstrates experience with:

- Python programming
- Chess rule implementation
- Algorithmic thinking
- Game state management
- API design
- FastAPI
- React
- Vite
- Full-stack development
- Debugging and refactoring
- Deployment configuration

## Author

Created by Jake Lasnitzki as a personal software and engineering project.
