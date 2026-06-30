import copy
import sys
import threading

import pytest
from fastapi import HTTPException

import engine_w
import main
import state_w
from game_store import (
    GameNotFound,
    InMemoryGameRepository,
    RedisGameRepository,
    create_repository,
)
from state_w import GameState


class FakeRedisLock:
    def __init__(self):
        self.lock = threading.RLock()

    def acquire(self, blocking=True):
        return self.lock.acquire(blocking=blocking)

    def release(self):
        self.lock.release()


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}
        self.locks = {}

    def ping(self):
        return True

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.ttls[key] = ttl

    def expire(self, key, ttl):
        if key in self.values:
            self.ttls[key] = ttl

    def delete(self, key):
        self.values.pop(key, None)
        self.ttls.pop(key, None)

    def lock(self, key, timeout=30, blocking_timeout=5):
        return self.locks.setdefault(key, FakeRedisLock())


@pytest.fixture()
def repo():
    repository = InMemoryGameRepository(ttl_seconds=60)
    main.set_repository(repository)
    return repository


def test_creating_two_games_keeps_boards_independent(repo):
    first = main.create_game(main.NewGameRequest(player_color="white"))
    second = main.create_game(main.NewGameRequest(player_color="white"))

    main.make_move(
        first["game_id"],
        main.MoveRequest(start_row=6, start_col=4, end_row=4, end_col=4),
    )

    first_after = repo.get_game(first["game_id"])
    second_after = repo.get_game(second["game_id"])

    assert first_after.board[4][4] == 6
    assert second_after.board[6][4] == 6
    assert first_after.move_notation_history == ["e4"]
    assert second_after.move_notation_history == []


def test_game_state_serializes_and_restores():
    game = GameState(player_color="black")
    state_w.make_move(game, 6, 4, 4, 4)

    restored = GameState.from_dict(game.to_dict())

    assert restored.game_id == game.game_id
    assert restored.board == game.board
    assert restored.move_history == game.move_history
    assert restored.en_passant_target == game.en_passant_target
    assert restored.has_moved == game.has_moved
    assert restored.position_version == game.position_version


def test_redis_repository_preserves_game_after_recreation():
    redis = FakeRedis()
    first_repo = RedisGameRepository(redis, ttl_seconds=60)
    game = GameState(player_color="white")
    first_repo.create_game(game)
    state_w.make_move(game, 6, 4, 4, 4)
    first_repo.save_game(game)

    recreated_repo = RedisGameRepository(redis, ttl_seconds=60)
    restored = recreated_repo.get_game(game.game_id)

    assert restored.board[4][4] == 6
    assert restored.move_notation_history == ["e4"]


def test_delete_game(repo):
    game = GameState()
    repo.create_game(game)
    repo.delete_game(game.game_id)

    with pytest.raises(GameNotFound):
        repo.get_game(game.game_id)


def test_expired_games_are_removed():
    now = [100.0]
    repo = InMemoryGameRepository(ttl_seconds=10, now_fn=lambda: now[0])
    game = GameState()
    repo.create_game(game)

    now[0] = 111.0

    with pytest.raises(GameNotFound):
        repo.get_game(game.game_id)


def test_duplicate_engine_request_is_rejected(repo):
    game = GameState(player_color="white")
    state_w.make_move(game, 6, 4, 4, 4)
    game.engine_thinking = True
    repo.create_game(game)

    with pytest.raises(HTTPException) as exc:
        main.make_engine_move(game.game_id)

    assert exc.value.status_code == 409


def test_simultaneous_move_requests_only_apply_one_move(repo):
    game = GameState(player_color="white")
    repo.create_game(game)
    results = []

    def attempt(move):
        try:
            results.append(("ok", main.make_move(game.game_id, main.MoveRequest(**move))))
        except HTTPException as exc:
            results.append(("error", exc.status_code))

    first = {"start_row": 6, "start_col": 4, "end_row": 4, "end_col": 4}
    second = {"start_row": 6, "start_col": 3, "end_row": 4, "end_col": 3}
    threads = [threading.Thread(target=attempt, args=(move,)) for move in (first, second)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    stored = repo.get_game(game.game_id)
    assert len(stored.move_history) == 1
    assert sorted(result[0] for result in results) == ["error", "ok"]


def test_outdated_engine_result_is_discarded(repo, monkeypatch):
    game = GameState(player_color="white")
    state_w.make_move(game, 6, 4, 4, 4)
    repo.create_game(game)
    original_version = game.position_version

    def fake_find_best_engine_move(search_game, color=None):
        stored = repo.get_game(game.game_id)
        stored.position_version += 1
        repo.save_game(stored)
        return (1, 4, 3, 4), engine_w.SearchContext(nodes=1)

    monkeypatch.setattr(engine_w, "find_best_engine_move", fake_find_best_engine_move)

    data = main.make_engine_move(game.game_id)
    stored = repo.get_game(game.game_id)

    assert data["engine_result_discarded"] is True
    assert stored.position_version == original_version + 1
    assert stored.move_notation_history == ["e4"]
    assert stored.engine_thinking is False


def test_redis_unavailable_falls_back_to_in_memory(monkeypatch):
    class BrokenRedisFactory:
        @staticmethod
        def from_url(url):
            raise RuntimeError("redis down")

    class BrokenRedisModule:
        Redis = BrokenRedisFactory

    monkeypatch.setitem(sys.modules, "redis", BrokenRedisModule)

    repo = create_repository(redis_url="redis://example.invalid:6379")

    assert isinstance(repo, InMemoryGameRepository)
