import unittest

from tools.rhcsa_search import (
    exact_command_lookup,
    filter_by_topic,
    grep_rhcsa,
    library_status,
    load_topic,
    retrieve_examples,
    search_by_tag,
    search_rhcsa,
    suggest_related_commands,
)


class RHCSARetrievalTests(unittest.TestCase):
    def test_library_status_uses_local_knowledge_root(self) -> None:
        status = library_status()
        self.assertTrue(status["exists"])
        self.assertTrue(status["path"].endswith("/knowledge"))
        self.assertGreater(status["indexed_topics"], 0)

    def test_keyword_search_returns_filesystem_module(self) -> None:
        results = search_rhcsa("nawigacja plikow", limit=5)
        self.assertTrue(results)
        self.assertEqual(results[0]["category"], "filesystem")

    def test_tag_search_matches_exact_tag(self) -> None:
        results = search_by_tag("service-status", limit=5)
        self.assertTrue(results)
        self.assertTrue(any("systemctl-status.json" in item["file_location"] for item in results))

    def test_exact_command_lookup_matches_only_exact_command(self) -> None:
        results = exact_command_lookup("systemctl status", limit=5)
        self.assertTrue(results)
        self.assertTrue(any("systemctl-status.json" in item["file_location"] for item in results))

    def test_grep_retrieval_finds_literal_pattern(self) -> None:
        results = grep_rhcsa("Troubleshooting hint", limit=5)
        self.assertTrue(results)
        self.assertTrue(all("preview" in item for item in results))

    def test_topic_filter_restricts_results(self) -> None:
        results = filter_by_topic("networking", "ssh", limit=10)
        self.assertTrue(results)
        self.assertTrue(all(item["category"] == "networking" for item in results))

    def test_load_topic_returns_topic_markdown(self) -> None:
        text = load_topic("filesystem", max_chars=4000)
        self.assertIn("# Filesystem", text)

    def test_examples_retrieval_reads_local_json_examples(self) -> None:
        results = retrieve_examples("systemctl", limit=5)
        self.assertTrue(results)
        self.assertEqual(results[0]["topic"], "systemctl-status")

    def test_command_suggestions_are_deterministic(self) -> None:
        first = suggest_related_commands("podman", limit=5)
        second = suggest_related_commands("podman", limit=5)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
