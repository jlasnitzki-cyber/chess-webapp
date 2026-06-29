# Chess web app

Your existing engine (`config_w.py`, `engine_w.py`, `moves_w.py`,
`notation_w.py`, `state_w.py`) is unchanged in `backend/`. The only new
backend file is `main.py`, which wraps it in a FastAPI server. The
`frontend/` folder is a React + Vite app that talks to that server.

## Run the backend

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

This serves the API at `http://localhost:8000`. Visiting
`http://localhost:8000/docs` gives you interactive API docs.

## Run the frontend

In a separate terminal:

```
cd frontend
npm install
npm run dev
```

This opens the app at `http://localhost:5173`. You can choose white or
black; the engine plays the other side and moves automatically.

## How it works

- **One shared game.** `state_w.py` keeps the game in module-level
  globals, so this server holds a single game for the whole process —
  exactly right for one person playing in one browser tab. If you ever
  want multiple independent games (e.g. sharing this with friends),
  `state_w`'s globals would need to become an instance you can have
  many of, keyed by a game id in `main.py`.
- **Pieces are Unicode glyphs** (♔♕♖♗♘♙ etc.), mapped in
  `frontend/src/pieces.js`, so the app works without any image assets.
  Swap in your own piece images by editing that file and the `.piece`
  CSS class in `styles.css`.
- **Pawns auto-promote to queen** (matches your existing
  `notation_w.py`/`moves_w.py` behavior). Adding an underpromotion
  choice would mean adding a `promotion` field to the `/api/move`
  request and threading it through `apply_special_moves`.
- **Undo** takes back your last move plus any engine reply after it, so
  it's always your turn afterward.
- **Engine move time** is adjustable from the sidebar. More time usually
  means a stronger but slower bot.
