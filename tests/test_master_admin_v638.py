from cupnavi_api import admin_repository as repo


def test_master_email_allowlist_is_server_controlled(monkeypatch):
    monkeypatch.setenv("CUPNAVI_MASTER_EMAILS", " MASTER@example.com , second@example.com ")
    assert repo._is_master_email("master@example.com") is True
    assert repo._is_master_email("SECOND@example.com") is True
    assert repo._is_master_email("other@example.com") is False


def test_master_tournament_access_bypasses_membership_only_for_existing_cup(monkeypatch):
    monkeypatch.setattr(repo, "_account_is_master", lambda account_id: account_id == 99)
    monkeypatch.setattr(repo, "one", lambda sql, params=(): {"allowed": 1} if "FROM tournaments" in sql and params == (7,) else None)
    assert repo._has_tournament_access(99, 7) is True
    assert repo._has_tournament_access(99, 8) is False


def test_normal_account_still_requires_membership(monkeypatch):
    monkeypatch.setattr(repo, "_account_is_master", lambda account_id: False)
    seen = []
    def fake_one(sql, params=()):
        seen.append((sql, params))
        return {"allowed": 1} if params == (12, 7) else None
    monkeypatch.setattr(repo, "one", fake_one)
    assert repo._has_tournament_access(12, 7) is True
    assert repo._has_tournament_access(12, 8) is False
    assert any("tournament_members" in sql for sql, _ in seen)


def test_master_sees_all_cups_with_master_role(monkeypatch):
    monkeypatch.setattr(repo, "_account_is_master", lambda account_id: True)
    monkeypatch.setattr(repo, "all_rows", lambda sql, params=(): [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}])
    cups = repo.organizer_tournaments(99)
    assert [cup["id"] for cup in cups] == [1, 2]
    assert all(cup["role"] == "master" for cup in cups)
