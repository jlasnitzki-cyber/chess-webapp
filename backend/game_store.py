import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Optional

from state_w import GameState


LOGGER = logging.getLogger(__name__)
DEFAULT_GAME_TTL_SECONDS = 24 * 60 * 60


class GameNotFound(Exception):
    pass


class GameRepository:
    def create_game(self, game: GameState) -> GameState:
        raise NotImplementedError

    def get_game(self, game_id: str) -> GameState:
        raise NotImplementedError

    def save_game(self, game: GameState) -> GameState:
        raise NotImplementedError

    def delete_game(self, game_id: str) -> None:
        raise NotImplementedError

    @contextmanager
    def lock_game(self, game_id: str, blocking_timeout: float = 5.0):
        yield


class InMemoryGameRepository(GameRepository):
    def __init__(self, ttl_seconds: int = DEFAULT_GAME_TTL_SECONDS, now_fn=None):
        self.ttl_seconds = ttl_seconds
        self.now_fn = now_fn or time.time
        self.games: dict[str, dict] = {}
        self.expires_at: dict[str, float] = {}
        self.locks: dict[str, threading.RLock] = {}
        self.index_lock = threading.RLock()
        LOGGER.warning(
            "Redis is unavailable or REDIS_URL is not configured; using temporary in-memory game storage."
        )

    def _purge_if_expired(self, game_id: str):
        expires_at = self.expires_at.get(game_id)
        if expires_at is not None and expires_at <= self.now_fn():
            self.games.pop(game_id, None)
            self.expires_at.pop(game_id, None)
            self.locks.pop(game_id, None)

    def _refresh(self, game_id: str):
        self.expires_at[game_id] = self.now_fn() + self.ttl_seconds

    def create_game(self, game: GameState) -> GameState:
        with self.index_lock:
            self.games[game.game_id] = game.to_dict()
            self.locks.setdefault(game.game_id, threading.RLock())
            self._refresh(game.game_id)
        return game

    def get_game(self, game_id: str) -> GameState:
        with self.index_lock:
            self._purge_if_expired(game_id)
            data = self.games.get(game_id)
            if data is None:
                raise GameNotFound(game_id)
            self._refresh(game_id)
            return GameState.from_dict(data)

    def save_game(self, game: GameState) -> GameState:
        with self.index_lock:
            self.games[game.game_id] = game.to_dict()
            self.locks.setdefault(game.game_id, threading.RLock())
            self._refresh(game.game_id)
        return game

    def delete_game(self, game_id: str) -> None:
        with self.index_lock:
            self.games.pop(game_id, None)
            self.expires_at.pop(game_id, None)
            self.locks.pop(game_id, None)

    @contextmanager
    def lock_game(self, game_id: str, blocking_timeout: float = 5.0):
        with self.index_lock:
            lock = self.locks.setdefault(game_id, threading.RLock())
        acquired = lock.acquire(timeout=blocking_timeout)
        if not acquired:
            raise TimeoutError(f"Could not acquire lock for game {game_id}")
        try:
            yield
        finally:
            lock.release()


class RedisGameRepository(GameRepository):
    def __init__(self, redis_client, ttl_seconds: int = DEFAULT_GAME_TTL_SECONDS):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.local_locks: dict[str, threading.RLock] = {}
        self.local_locks_guard = threading.RLock()

    def key(self, game_id: str) -> str:
        return f"game:{game_id}"

    def lock_key(self, game_id: str) -> str:
        return f"game-lock:{game_id}"

    def create_game(self, game: GameState) -> GameState:
        self.save_game(game)
        return game

    def get_game(self, game_id: str) -> GameState:
        raw = self.redis.get(self.key(game_id))
        if raw is None:
            raise GameNotFound(game_id)
        self.redis.expire(self.key(game_id), self.ttl_seconds)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return GameState.from_dict(json.loads(raw))

    def save_game(self, game: GameState) -> GameState:
        self.redis.setex(
            self.key(game.game_id),
            self.ttl_seconds,
            json.dumps(game.to_dict()),
        )
        return game

    def delete_game(self, game_id: str) -> None:
        self.redis.delete(self.key(game_id))

    @contextmanager
    def lock_game(self, game_id: str, blocking_timeout: float = 5.0):
        lock = self.redis.lock(
            self.lock_key(game_id),
            timeout=30,
            blocking_timeout=blocking_timeout,
        )
        acquired = lock.acquire(blocking=True)
        if not acquired:
            raise TimeoutError(f"Could not acquire lock for game {game_id}")
        try:
            yield
        finally:
            try:
                lock.release()
            except Exception:
                LOGGER.exception("Failed to release Redis lock for game %s", game_id)


def create_repository(
    redis_url: Optional[str] = None,
    ttl_seconds: int = DEFAULT_GAME_TTL_SECONDS,
) -> GameRepository:
    redis_url = redis_url if redis_url is not None else os.getenv("REDIS_URL")
    if not redis_url:
        return InMemoryGameRepository(ttl_seconds=ttl_seconds)

    try:
        import redis

        client = redis.Redis.from_url(redis_url)
        client.ping()
        LOGGER.info("Using Redis game storage.")
        return RedisGameRepository(client, ttl_seconds=ttl_seconds)
    except Exception:
        LOGGER.exception(
            "Redis is unavailable; falling back to temporary in-memory game storage."
        )
        return InMemoryGameRepository(ttl_seconds=ttl_seconds)
