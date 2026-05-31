from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class UserInfo:
    id: int
    username: str | None
    full_name: str


@dataclass
class FormSession:
    form: dict[str, Any]
    user: UserInfo
    current_index: int = 0
    responses: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[int, FormSession] = {}

    def start_session(self, user: UserInfo, form: dict[str, Any]) -> FormSession:
        session = FormSession(form=form, user=user)
        self._sessions[user.id] = session
        return session

    def get_session(self, user_id: int) -> FormSession | None:
        return self._sessions.get(user_id)

    def clear_session(self, user_id: int) -> None:
        self._sessions.pop(user_id, None)

    def get_current_field(self, user_id: int) -> dict[str, Any] | None:
        session = self.get_session(user_id)
        if session is None:
            return None

        fields = session.form.get("fields", [])
        if session.current_index >= len(fields):
            return None

        return fields[session.current_index]

    def save_response(self, user_id: int, field_name: str, value: Any) -> None:
        session = self.get_session(user_id)
        if session is None:
            return
        session.responses[field_name] = value

    def advance(self, user_id: int) -> None:
        session = self.get_session(user_id)
        if session is None:
            return
        session.current_index += 1

    def is_complete(self, user_id: int) -> bool:
        session = self.get_session(user_id)
        if session is None:
            return False

        total_fields = len(session.form.get("fields", []))
        return session.current_index >= total_fields

    def build_payload(self, user_id: int) -> dict[str, Any] | None:
        session = self.get_session(user_id)
        if session is None:
            return None

        return {
            "form_id": session.form.get("id"),
            "user": {
                "id": session.user.id,
                "username": session.user.username,
                "full_name": session.user.full_name,
            },
            "responses": session.responses,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
