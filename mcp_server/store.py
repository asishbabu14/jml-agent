"""SQLite state for the mock directory, tickets, and approvals."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hr_employees (
    email TEXT PRIMARY KEY,
    employee_id TEXT,
    first_name TEXT,
    last_name TEXT,
    department TEXT,
    title TEXT,
    manager_email TEXT,
    status TEXT,
    start_date TEXT,
    last_day TEXT,
    new_department TEXT,
    new_title TEXT
);
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    id TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    department TEXT,
    title TEXT,
    manager_email TEXT,
    status TEXT NOT NULL,
    mfa_enrolled INTEGER NOT NULL DEFAULT 0,
    mfa_reset_at TEXT,
    sessions_cleared_at TEXT
);
CREATE TABLE IF NOT EXISTS groups (
    name TEXT PRIMARY KEY,
    description TEXT,
    owner_email TEXT
);
CREATE TABLE IF NOT EXISTS memberships (
    email TEXT NOT NULL,
    group_name TEXT NOT NULL,
    PRIMARY KEY (email, group_name)
);
CREATE TABLE IF NOT EXISTS google_users (
    email TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    drive_transferred_to TEXT,
    drive_status TEXT
);
CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    email TEXT,
    platform TEXT,
    os_version TEXT,
    filevault INTEGER,
    edr_status TEXT,
    last_checkin TEXT,
    compliant INTEGER,
    source TEXT,
    assignment_status TEXT
);
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    category TEXT NOT NULL,
    urgency TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    requester TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    tool TEXT NOT NULL,
    requester TEXT NOT NULL,
    subject_email TEXT,
    params_json TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    created_at TEXT NOT NULL,
    executed_at TEXT
);
CREATE TABLE IF NOT EXISTS approval_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_id TEXT NOT NULL,
    approver TEXT NOT NULL,
    role TEXT NOT NULL,
    decision TEXT NOT NULL,
    identity_verified INTEGER NOT NULL,
    verification_method TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (approval_id, approver)
);
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def get_meta(self, key: str) -> str | None:
        row = self._one("SELECT value FROM meta WHERE key = ?", (key,))
        return None if row is None else str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            self.conn.commit()

    def upsert_hr(self, row: dict[str, str]) -> None:
        self._exec(
            """
            INSERT INTO hr_employees(
                email, employee_id, first_name, last_name, department, title,
                manager_email, status, start_date, last_day, new_department, new_title
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                employee_id = excluded.employee_id,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                department = excluded.department,
                title = excluded.title,
                manager_email = excluded.manager_email,
                status = excluded.status,
                start_date = excluded.start_date,
                last_day = excluded.last_day,
                new_department = excluded.new_department,
                new_title = excluded.new_title
            """,
            (
                row["email"],
                row.get("employee_id", ""),
                row.get("first_name", ""),
                row.get("last_name", ""),
                row.get("department", ""),
                row.get("title", ""),
                row.get("manager_email", ""),
                row.get("status", ""),
                row.get("start_date", ""),
                row.get("last_day", ""),
                row.get("new_department", ""),
                row.get("new_title", ""),
            ),
        )

    def get_hr(self, email: str) -> dict[str, Any] | None:
        return self._dict("SELECT * FROM hr_employees WHERE email = ?", (email,))

    def update_hr_status(self, email: str, status: str, department: str, title: str) -> None:
        self._exec(
            "UPDATE hr_employees SET status = ?, department = ?, title = ?, "
            "new_department = '', new_title = '' WHERE email = ?",
            (status, department, title, email),
        )

    def upsert_group(self, name: str, description: str, owner_email: str) -> None:
        self._exec(
            """
            INSERT INTO groups(name, description, owner_email) VALUES(?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                description = excluded.description,
                owner_email = excluded.owner_email
            """,
            (name, description, owner_email),
        )

    def group_exists(self, name: str) -> bool:
        return self._one("SELECT 1 FROM groups WHERE name = ?", (name,)) is not None

    def upsert_user(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO users(
                email, id, first_name, last_name, department, title, manager_email,
                status, mfa_enrolled, mfa_reset_at, sessions_cleared_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                department = excluded.department,
                title = excluded.title,
                manager_email = excluded.manager_email,
                status = excluded.status,
                mfa_enrolled = excluded.mfa_enrolled,
                mfa_reset_at = excluded.mfa_reset_at,
                sessions_cleared_at = excluded.sessions_cleared_at
            """,
            (
                row["email"],
                row["id"],
                row.get("first_name", ""),
                row.get("last_name", ""),
                row.get("department", ""),
                row.get("title", ""),
                row.get("manager_email", ""),
                row["status"],
                1 if row.get("mfa_enrolled") else 0,
                row.get("mfa_reset_at"),
                row.get("sessions_cleared_at"),
            ),
        )

    def get_user(self, email: str) -> dict[str, Any] | None:
        return self._dict("SELECT * FROM users WHERE email = ?", (email,))

    def add_membership(self, email: str, group_name: str) -> None:
        self._exec(
            "INSERT OR IGNORE INTO memberships(email, group_name) VALUES(?, ?)",
            (email, group_name),
        )

    def groups_for(self, email: str) -> list[str]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT group_name FROM memberships WHERE email = ? ORDER BY group_name",
                (email,),
            ).fetchall()
        return [str(row["group_name"]) for row in rows]

    def remove_all_memberships(self, email: str) -> list[str]:
        current = self.groups_for(email)
        self._exec("DELETE FROM memberships WHERE email = ?", (email,))
        return current

    def remove_memberships(self, email: str, names: list[str]) -> None:
        with self._lock:
            self.conn.executemany(
                "DELETE FROM memberships WHERE email = ? AND group_name = ?",
                [(email, name) for name in names],
            )
            self.conn.commit()

    def upsert_google(self, email: str, status: str) -> None:
        self._exec(
            """
            INSERT INTO google_users(email, status, drive_transferred_to, drive_status)
            VALUES(?, ?, NULL, 'in_place')
            ON CONFLICT(email) DO UPDATE SET status = excluded.status
            """,
            (email, status),
        )

    def get_google(self, email: str) -> dict[str, Any] | None:
        return self._dict("SELECT * FROM google_users WHERE email = ?", (email,))

    def set_google(self, email: str, **fields: Any) -> None:
        current = self.get_google(email) or {
            "email": email,
            "status": "active",
            "drive_transferred_to": None,
            "drive_status": "in_place",
        }
        current.update(fields)
        self._exec(
            """
            INSERT INTO google_users(email, status, drive_transferred_to, drive_status)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                status = excluded.status,
                drive_transferred_to = excluded.drive_transferred_to,
                drive_status = excluded.drive_status
            """,
            (
                email,
                current["status"],
                current.get("drive_transferred_to"),
                current.get("drive_status"),
            ),
        )

    def upsert_device(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO devices(
                id, email, platform, os_version, filevault, edr_status,
                last_checkin, compliant, source, assignment_status
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                email = excluded.email,
                platform = excluded.platform,
                os_version = excluded.os_version,
                filevault = excluded.filevault,
                edr_status = excluded.edr_status,
                last_checkin = excluded.last_checkin,
                compliant = excluded.compliant,
                source = excluded.source,
                assignment_status = excluded.assignment_status
            """,
            (
                row["id"],
                row.get("email"),
                row.get("platform"),
                row.get("os_version"),
                1 if row.get("filevault") else 0,
                row.get("edr_status"),
                row.get("last_checkin"),
                1 if row.get("compliant") else 0,
                row.get("source"),
                row.get("assignment_status"),
            ),
        )

    def devices_for(self, email: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM devices WHERE email = ? ORDER BY id",
                (email,),
            ).fetchall()
        return [dict(row) for row in rows]

    def release_devices(self, email: str) -> list[str]:
        devices = self.devices_for(email)
        self._exec(
            "UPDATE devices SET assignment_status = 'pending_retrieval', compliant = 0 WHERE email = ?",
            (email,),
        )
        return [str(device["id"]) for device in devices]

    def create_ticket(self, row: dict[str, Any]) -> dict[str, Any]:
        self._exec(
            """
            INSERT INTO tickets(id, summary, category, urgency, status, owner, requester, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["summary"],
                row["category"],
                row["urgency"],
                row["status"],
                row["owner"],
                row["requester"],
                row["created_at"],
            ),
        )
        return row

    def create_approval(self, row: dict[str, Any]) -> dict[str, Any]:
        self._exec(
            """
            INSERT INTO approvals(
                id, tool, requester, subject_email, params_json, status, result_json,
                created_at, executed_at
            ) VALUES(?, ?, ?, ?, ?, ?, NULL, ?, NULL)
            """,
            (
                row["id"],
                row["tool"],
                row["requester"],
                row.get("subject_email"),
                json.dumps(row["params"], sort_keys=True),
                row["status"],
                row["created_at"],
            ),
        )
        return row

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        row = self._dict("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        if row is None:
            return None
        row["params"] = json.loads(row.pop("params_json"))
        raw_result = row.pop("result_json")
        row["result"] = json.loads(raw_result) if raw_result else None
        return row

    def set_approval_status(self, approval_id: str, status: str, result: dict[str, Any] | None = None) -> None:
        executed_at = utc_now() if status in {"executed", "failed"} else None
        payload = json.dumps(result, sort_keys=True) if result is not None else None
        self._exec(
            """
            UPDATE approvals
            SET status = ?,
                result_json = COALESCE(?, result_json),
                executed_at = COALESCE(?, executed_at)
            WHERE id = ?
            """,
            (status, payload, executed_at, approval_id),
        )

    def add_decision(self, row: dict[str, Any]) -> None:
        self._exec(
            """
            INSERT INTO approval_decisions(
                approval_id, approver, role, decision, identity_verified,
                verification_method, note, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["approval_id"],
                row["approver"],
                row["role"],
                row["decision"],
                1 if row.get("identity_verified") else 0,
                row.get("verification_method") or "",
                row.get("note") or "",
                row["created_at"],
            ),
        )

    def decisions_for(self, approval_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM approval_decisions WHERE approval_id = ? ORDER BY id",
                (approval_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _exec(self, sql: str, params: tuple[Any, ...]) -> None:
        with self._lock:
            self.conn.execute(sql, params)
            self.conn.commit()

    def _one(self, sql: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def _dict(self, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        row = self._one(sql, params)
        return None if row is None else dict(row)
