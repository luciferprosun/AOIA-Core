from __future__ import annotations

import unittest

from apps.aoia_desktop_demo.state.chat_session import ChatSession


class ChatSessionTests(unittest.TestCase):
    def test_add_user_message_ignores_blank_text(self) -> None:
        session = ChatSession()
        session.add_user_message("   ")
        self.assertEqual(session.transcript, [])

    def test_messages_for_provider_preserves_roles_and_system_separately(self) -> None:
        session = ChatSession()
        session.system_context = "system baseline"
        session.add_user_message("hi")
        session.add_assistant_message("hello")
        session.add_error_message("should not appear in provider messages")

        messages = session.messages_for_provider()
        self.assertEqual(messages[0].role, "system")
        self.assertEqual(messages[0].content, "system baseline")
        roles = [message.role for message in messages]
        self.assertNotIn("error", roles)
        self.assertEqual(roles.count("user"), 1)
        self.assertEqual(roles.count("assistant"), 1)

    def test_extra_system_message_is_appended_not_replacing_base_context(self) -> None:
        session = ChatSession()
        session.system_context = "base"
        session.add_user_message("hi")
        messages = session.messages_for_provider(extra_system_message="evidence block")
        system_messages = [m.content for m in messages if m.role == "system"]
        self.assertEqual(system_messages, ["base", "evidence block"])

    def test_request_lifecycle_and_cancellation(self) -> None:
        session = ChatSession()
        request_id = session.begin_request()
        self.assertTrue(session.has_active_request)
        self.assertTrue(session.is_current(request_id))

        session.cancel_active_request()
        self.assertFalse(session.has_active_request)
        self.assertFalse(session.is_current(request_id), "a canceled request must never be treated as current again")

    def test_end_request_only_clears_matching_id(self) -> None:
        session = ChatSession()
        first_id = session.begin_request()
        session.end_request(first_id + 999)  # some other, non-matching id
        self.assertTrue(session.is_current(first_id), "end_request must not clear an unrelated id")
        session.end_request(first_id)
        self.assertFalse(session.has_active_request)

    def test_new_chat_resets_everything(self) -> None:
        session = ChatSession()
        session.system_context = "x"
        session.add_user_message("hi")
        session.begin_request()
        session.new_chat()
        self.assertEqual(session.transcript, [])
        self.assertIsNone(session.system_context)
        self.assertFalse(session.has_active_request)

    def test_ids_are_unique_across_sessions(self) -> None:
        session_a = ChatSession()
        session_b = ChatSession()
        id_a = session_a.begin_request()
        id_b = session_b.begin_request()
        self.assertNotEqual(id_a, id_b)


if __name__ == "__main__":
    unittest.main()
