from __future__ import annotations

import json
import types
import unittest
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from orchestrator.knowledge_router import (
    KnowledgeRouteProposal,
    KnowledgeRouter,
    NON_AUTHORITATIVE,
)
from retrieval import facade as retrieval_facade
from runtime.human_decision_gated_artifact_write import (
    write_artifact_after_human_gate,
)


class ForbiddenCallable:
    def __call__(self, *args, **kwargs):
        raise AssertionError("routing must not invoke caller-supplied callables")


def iter_data_values(value):
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from iter_data_values(getattr(value, field.name))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from iter_data_values(key)
            yield from iter_data_values(item)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            yield from iter_data_values(item)
        return
    yield value


class KnowledgeRouterInertness1ATests(unittest.TestCase):
    def create_router(self, root: Path, **kwargs) -> KnowledgeRouter:
        return KnowledgeRouter(root, **kwargs)

    def test_route_returns_immutable_non_authoritative_metadata_only(self) -> None:
        with TemporaryDirectory() as tmp:
            proposal = self.create_router(Path(tmp)).route(
                "How do I inspect systemctl status on Linux?"
            )

        self.assertIsInstance(proposal, KnowledgeRouteProposal)
        self.assertEqual("ROUTE_PROPOSED", proposal.route_status)
        self.assertEqual("linux_rhcsa_retrieval_v1", proposal.selected_route_id)
        self.assertEqual("hat_002", proposal.selected_hat_id)
        self.assertEqual(NON_AUTHORITATIVE, proposal.authority_status)
        self.assertFalse(proposal.should_handle_locally)
        self.assertEqual("", proposal.response)
        self.assertIsNone(proposal.hit)
        self.assertIsNotNone(proposal.retrieval_request)
        self.assertFalse(proposal.retrieval_request.execution_allowed)
        self.assertTrue(proposal.retrieval_request.requires_explicit_caller)
        with self.assertRaises(FrozenInstanceError):
            proposal.route_status = "EXECUTE"  # type: ignore[misc]

    def test_injected_retriever_and_engine_callbacks_are_never_invoked(self) -> None:
        forbidden = ForbiddenCallable()
        engine = types.SimpleNamespace(retrieve_operational_memory=forbidden)
        with TemporaryDirectory() as tmp:
            router = self.create_router(
                Path(tmp),
                retriever=forbidden,
                engine=engine,
            )
            proposal = router.route(
                "systemctl status",
                active_hat={
                    "route_candidate": forbidden,
                    "call": forbidden,
                    "provider_output": {"route": "linux"},
                },
            )

        self.assertEqual("ROUTE_PROPOSED", proposal.route_status)

    def test_route_performs_no_filesystem_write_and_returns_report_data(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            router = self.create_router(root)
            with (
                patch.object(
                    Path,
                    "write_text",
                    side_effect=AssertionError("routing must not write files"),
                ) as write_text,
                patch.object(
                    Path,
                    "write_bytes",
                    side_effect=AssertionError("routing must not write files"),
                ) as write_bytes,
                patch(
                    "builtins.open",
                    side_effect=AssertionError("routing must not open files"),
                ) as open_file,
            ):
                proposal = router.route("journalctl service failure")
                report = router.write_token_savings_report(proposal)
                serialized = json.dumps(proposal.to_dict(), sort_keys=True)

            write_text.assert_not_called()
            write_bytes.assert_not_called()
            open_file.assert_not_called()
            self.assertFalse(report["filesystem_persisted"])
            self.assertFalse(report["retrieval_executed"])
            self.assertIn('"authority_status": "NON_AUTHORITATIVE"', serialized)
            self.assertFalse(router.report_path.exists())

    def test_route_result_contains_no_callable_module_or_path(self) -> None:
        with TemporaryDirectory() as tmp:
            proposal = self.create_router(Path(tmp)).route("systemctl status")

        for value in iter_data_values(proposal):
            self.assertFalse(callable(value), repr(value))
            self.assertFalse(isinstance(value, types.ModuleType), repr(value))
            self.assertFalse(isinstance(value, Path), repr(value))

    def test_route_is_deterministic_and_metadata_cannot_force_it(self) -> None:
        with TemporaryDirectory() as tmp:
            router = self.create_router(Path(tmp))
            first = router.route(
                "  SYSTEMCTL   status ",
                active_hat={"provider_output": {"approved": True}},
            )
            second = router.route(
                "systemctl status",
                active_hat={"pheromone": 1_000_000, "route": "execute"},
            )
            unrelated_provider = router.route(
                "summarize this ordinary paragraph",
                active_hat={
                    "name": "Linux",
                    "provider_output": {"force_route": True},
                },
            )
            unrelated_pheromone = router.route(
                "write a poem",
                active_hat={"pheromone": {"route": "linux", "score": 999}},
            )

        self.assertEqual(first, second)
        self.assertEqual("NO_ROUTE", unrelated_provider.route_status)
        self.assertEqual("NO_ROUTE", unrelated_pheromone.route_status)

    def test_ambiguous_or_unrelated_query_does_not_force_unix_route(self) -> None:
        with TemporaryDirectory() as tmp:
            router = self.create_router(Path(tmp))
            ambiguous = router.route("linux")
            unrelated = router.route("quarterly planning notes")

        self.assertEqual("REVIEW_NEEDED", ambiguous.route_status)
        self.assertIsNone(ambiguous.retrieval_request)
        self.assertEqual("NO_ROUTE", unrelated.route_status)
        self.assertIsNone(unrelated.retrieval_request)

    def test_retrieval_is_a_separate_explicit_caller_action(self) -> None:
        sentinel = object()
        with TemporaryDirectory() as tmp:
            router = self.create_router(Path(tmp))
            with patch.object(
                retrieval_facade,
                "retrieve_linux_knowledge",
                return_value=sentinel,
            ) as retrieve:
                proposal = router.route("systemctl status")
                retrieve.assert_not_called()
                request = proposal.retrieval_request
                self.assertIsNotNone(request)
                result = retrieval_facade.retrieve_linux_knowledge(
                    request.query,
                    max_results=request.max_results,
                    project_dir=Path(tmp),
                )

        retrieve.assert_called_once()
        self.assertIs(sentinel, result)

    def test_route_proposal_is_rejected_as_human_gate_authority(self) -> None:
        artifact_writer = Mock(
            side_effect=AssertionError("writer must not run for route metadata")
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            proposal = self.create_router(root).route("systemctl status")
            result = write_artifact_after_human_gate(
                gate_result=proposal,
                artifact_request=object(),
                workspace_root=str(root),
                artifact_writer=artifact_writer,
            )

        self.assertFalse(result.write_attempted)
        self.assertFalse(result.artifact_write_occurred)
        artifact_writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
