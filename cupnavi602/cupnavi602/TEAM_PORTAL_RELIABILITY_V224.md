# CupNavi v.1.224 – Team Portal Reliability Bundle

## Included in this sweep

### 1. Unread messages no longer disappear automatically
Streamlit executes every `st.tabs` body on a rerun. The previous implementation
therefore marked inbox messages as read even when the user never opened the
Meddelanden tab.

Automatic read marking is removed.

Unread messages now remain unread until the user explicitly presses
`Markera alla som lästa`. The tab/header keeps the red unread indicator until
that action is performed.

The same correction is applied to the organizer/Admin inbox.

### 2. Read-state ownership protection
The read helper updates only messages that belong to:
- the current tournament; and
- the current team inbox, or the organizer inbox.

Passing stale/foreign message IDs cannot mark another team's messages as read.

### 3. Contact information optimistic locking
Lagportal contact information now uses a snapshot-based conditional UPDATE.
An old browser session cannot silently overwrite newer contact details.

### 4. Contact email validation
A non-empty responsible-email field must have a basic valid email shape before
persistence.

### 5. Clearer unread presentation
Unread inbox items retain a red marker in both the team and organizer inboxes.

## Preserved
Message sending, email notifications, permissions, match data, player/roster
concurrency protection, scheduling and E2E setup are unchanged.
