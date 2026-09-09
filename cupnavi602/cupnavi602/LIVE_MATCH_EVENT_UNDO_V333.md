# CupNavi v333 – Live Match Event Undo

- Adds a one-tap **Ångra senaste** action directly below the persistent latest-event confirmation in Matchhändelser.
- Undo targets the exact latest quick-entry player and event field, even if the reporter has already moved to another player.
- Reuses the existing optimistic-locking `save_event_rows` path with a `-1` delta; no direct delete or bypass is introduced.
- If another reporter changed the player row first, undo is rejected and fresh values are loaded.
- Existing correction panel and bulk event editor remain unchanged.
