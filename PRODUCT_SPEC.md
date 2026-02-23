# Product Specification — AI-Agent Shared Group Calendar

A closed-group collaborative scheduling platform (≤15 users) with an AI reasoning layer (ReAct pattern) above a deterministic backend.

---

## §5 Data Model

### §5.1 Users
- `user_id` (UUID, primary key)
- `display_name` (string, **unique**, max 100 chars)
- `password_hash` (bcrypt, never stored in plaintext)
- `default_timezone` (IANA tz string, default "UTC")
- `dnd_window_start_local` / `dnd_window_end_local` (time, nullable — "Quiet Hours")
- `aliases` (JSON array of strings, nullable)
- `enable_transit_checks` (boolean, default false)
- `created_at` (timestamp)

### §5.2 Groups
- `group_id` (UUID), `name` (string), `created_by` (FK → User)
- Members join via `GroupMembership` (user_id, group_id, role)

### §5.3 Events
- `event_id` (UUID), `group_id` (FK), `organizer_id` (FK → User)
- `title`, `start_time_utc`, `end_time_utc`, `constraint_level` (Hard/Soft)
- `status` (Scheduled / Cancelled), `version` (int, optimistic locking)

### §5.4 Attendees
- `event_id` (FK), `user_id` (FK), `rsvp_status` (invited/going/maybe/declined)

### §5.5 ChangeRequests
- Non-organizer users submit change requests (pending → approved/rejected by organizer)

### §5.6 Mutation Ledger
- Append-only `EventMutation` records for full audit trail (action_type, before/after snapshots, idempotency_key)

---

## §6 AI Agent Tools
- ReAct pattern agent with function-calling
- Tools: create_event, update_event, cancel_event, find_availability, summarize_schedule

### §6.3 Organizer Auto-RSVP
- When a user creates an event, they are automatically added as an attendee with `going` status

---

## §7 Invariants

### §7.1 Authorization
- Only the organizer may edit or cancel an event directly
- Non-organizers must use change requests (§10 HITL)

### §7.2 Cancellation
- Cancelled events are soft-deleted (status = "Cancelled"), never hard-deleted

### §7.3 Constraint Resolution
- Hard + Hard overlap → reject
- Soft + Soft overlap → allow
- Hard + Soft overlap → allow (soft yields)
- Hard constraint events cannot be created during any attendee's DND window

### §7.4 DND Evaluation
- Timezone-aware: backend converts DND local times to UTC for comparison
- Hard events blocked during DND; soft events allowed with warning

---

## §10 Human-in-the-Loop (HITL)
- Non-organizers submit `ChangeRequest` instead of direct edits
- Organizer approves or rejects each request

---

## §15 Optimistic Locking
- All event mutations require matching `version` field
- Concurrent update conflicts return 409

---

## §16 Authentication & Security *(Added Feb 2026)*

### §16.1 User Registration
- Users register with `display_name` + `password`
- `display_name` must be **unique** (exact match, case-sensitive)
  - Example: "Eric L" and "Eric A" are both valid; two "Eric L" are not
- Password is hashed with **bcrypt** (cost factor ≥ 12) before storage
- Password must be ≥ 8 characters

### §16.2 Login
- Users authenticate by `display_name` + `password`
- Backend verifies password against stored bcrypt hash
- On success, returns user object (MVP; JWT tokens for production)

### §16.3 Security Practices
- Passwords never stored in plaintext
- Passwords never returned in API responses
- bcrypt used for constant-time hash comparison

---

## §17 Frontend UX *(Added Feb 2026)*

### §17.1 Calendar Views
- **Personal calendar**: shows only the current user's events across all groups
- **Group calendar**: shows all events for a selected group
- Toggle between views in the sidebar

### §17.2 Group Onboarding
- During first use, user is prompted to create or join a group by name
- Group name is user-defined (e.g. "College Friends", "Work Team")

### §17.3 Theme
- Light mode / Dark mode / System default
- System (browser) setting is the default
- User can override via toggle (persisted in localStorage)

### §17.4 Design Principles
- Minimalist, clean UI (no unnecessary emojis or decorative icons)
- Google Calendar-inspired layout
- Three-column layout: sidebar, calendar, AI chat
