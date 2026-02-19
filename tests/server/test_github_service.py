"""Tests for GitHubService with mocked PyGithub.

All PyGithub calls are mocked — no actual GitHub API calls are made.
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from server.services.github_service import GitHubService


@pytest.fixture
def gh_service():
    """GitHubService with mocked PyGithub Github instance."""
    with patch("server.services.github_service.Github") as MockGithub:
        service = GitHubService("fake-token")
        service.gh = MockGithub.return_value
        yield service


def _make_content_file(name: str, path: str, sha: str = "abc123", size: int = 100, file_type: str = "file", content_b64: str | None = None):
    """Create a mock ContentFile object."""
    mock = MagicMock()
    mock.name = name
    mock.path = path
    mock.sha = sha
    mock.size = size
    mock.type = file_type
    if content_b64:
        mock.content = content_b64
    return mock


# ---------------------------------------------------------------------------
# list_md_files
# ---------------------------------------------------------------------------

class TestListMdFiles:
    def test_lists_md_files(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        file1 = _make_content_file("prompt.md", "prompts/prompt.md")
        file2 = _make_content_file("readme.txt", "prompts/readme.txt")
        file3 = _make_content_file("other.md", "prompts/other.md")
        repo.get_contents.return_value = [file1, file2, file3]

        result = gh_service.list_md_files("owner/repo")
        assert len(result) == 2
        assert result[0]["name"] == "prompt.md"
        assert result[1]["name"] == "other.md"

    def test_lists_md_files_recursive(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        subdir = _make_content_file("sub", "prompts/sub", file_type="dir")
        file1 = _make_content_file("a.md", "prompts/a.md")
        nested = _make_content_file("b.md", "prompts/sub/b.md")

        # First call returns root contents, second returns subdir contents
        repo.get_contents.side_effect = [
            [file1, subdir],
            [nested],
        ]

        result = gh_service.list_md_files("owner/repo")
        assert len(result) == 2
        paths = {f["path"] for f in result}
        assert "prompts/a.md" in paths
        assert "prompts/sub/b.md" in paths

    def test_lists_md_files_empty_repo(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo
        repo.get_contents.return_value = []

        result = gh_service.list_md_files("owner/repo")
        assert result == []

    def test_lists_md_files_github_error(self, gh_service):
        from github import GithubException
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo
        repo.get_contents.side_effect = GithubException(404, "Not Found", None)

        result = gh_service.list_md_files("owner/repo")
        assert result == []

    def test_lists_md_files_with_subdirectory(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo
        file1 = _make_content_file("greeting.md", "src/prompts/greeting.md")
        repo.get_contents.return_value = [file1]

        result = gh_service.list_md_files("owner/repo", subdirectory="src/prompts")
        repo.get_contents.assert_called_with("src/prompts", ref="main")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_file_content
# ---------------------------------------------------------------------------

class TestGetFileContent:
    def test_returns_content_and_sha(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        content = "---\nname: greeting\n---\nHello {{ name }}"
        encoded = base64.b64encode(content.encode()).decode()
        mock_file = MagicMock()
        mock_file.content = encoded
        mock_file.sha = "file-sha-123"
        repo.get_contents.return_value = mock_file

        result_content, result_sha = gh_service.get_file_content("owner/repo", "prompts/greeting.md")
        assert result_content == content
        assert result_sha == "file-sha-123"

    def test_raises_on_directory(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo
        repo.get_contents.return_value = [MagicMock(), MagicMock()]

        with pytest.raises(ValueError, match="Expected file, got directory"):
            gh_service.get_file_content("owner/repo", "prompts/")


# ---------------------------------------------------------------------------
# get_file_history
# ---------------------------------------------------------------------------

class TestGetFileHistory:
    def test_returns_commit_history(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        mock_commit = MagicMock()
        mock_commit.sha = "abc123"
        mock_commit.commit.message = "Update greeting"
        mock_commit.commit.author.name = "Test User"
        mock_commit.commit.author.date.isoformat.return_value = "2026-01-01T00:00:00"

        repo.get_commits.return_value = [mock_commit]

        result = gh_service.get_file_history("owner/repo", "prompts/greeting.md")
        assert len(result) == 1
        assert result[0]["sha"] == "abc123"
        assert result[0]["message"] == "Update greeting"

    def test_respects_limit(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        commits = []
        for i in range(25):
            c = MagicMock()
            c.sha = f"sha-{i}"
            c.commit.message = f"Commit {i}"
            c.commit.author.name = "User"
            c.commit.author.date.isoformat.return_value = "2026-01-01"
            commits.append(c)

        repo.get_commits.return_value = commits

        result = gh_service.get_file_history("owner/repo", "file.md", limit=5)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# create_file
# ---------------------------------------------------------------------------

class TestCreateFile:
    def test_creates_file_and_returns_sha(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        mock_commit = MagicMock()
        mock_commit.sha = "new-commit-sha"
        repo.create_file.return_value = {"commit": mock_commit}

        sha = gh_service.create_file(
            "owner/repo", "prompts/new.md",
            "---\nname: new\n---\nContent",
            "Create new prompt",
        )
        assert sha == "new-commit-sha"
        repo.create_file.assert_called_once()

    def test_creates_file_with_author(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        mock_commit = MagicMock()
        mock_commit.sha = "sha"
        repo.create_file.return_value = {"commit": mock_commit}

        gh_service.create_file(
            "owner/repo", "prompts/new.md", "content", "msg",
            author_name="Test", author_email="test@example.com",
        )

        call_kwargs = repo.create_file.call_args
        assert call_kwargs.kwargs.get("author") is not None or call_kwargs[1].get("author") is not None


# ---------------------------------------------------------------------------
# update_file
# ---------------------------------------------------------------------------

class TestUpdateFile:
    def test_updates_file_and_returns_sha(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        mock_commit = MagicMock()
        mock_commit.sha = "updated-sha"
        repo.update_file.return_value = {"commit": mock_commit}

        sha = gh_service.update_file(
            "owner/repo", "prompts/greeting.md",
            "Updated content", "Update greeting",
            sha="old-sha",
        )
        assert sha == "updated-sha"
        repo.update_file.assert_called_once()


# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------

class TestDeleteFile:
    def test_deletes_file_and_returns_sha(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        mock_commit = MagicMock()
        mock_commit.sha = "delete-sha"
        repo.delete_file.return_value = {"commit": mock_commit}

        sha = gh_service.delete_file(
            "owner/repo", "prompts/old.md",
            "Delete old prompt", sha="file-sha",
        )
        assert sha == "delete-sha"


# ---------------------------------------------------------------------------
# get_diff
# ---------------------------------------------------------------------------

class TestGetDiff:
    def test_returns_patch(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        mock_file = MagicMock()
        mock_file.filename = "prompts/greeting.md"
        mock_file.patch = "@@ -1 +1 @@\n-old\n+new"

        mock_comparison = MagicMock()
        mock_comparison.files = [mock_file]
        repo.compare.return_value = mock_comparison

        result = gh_service.get_diff("owner/repo", "prompts/greeting.md", "abc123")
        assert result is not None
        assert "+new" in result

    def test_returns_none_for_missing_file(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        mock_file = MagicMock()
        mock_file.filename = "other/file.md"
        mock_comparison = MagicMock()
        mock_comparison.files = [mock_file]
        repo.compare.return_value = mock_comparison

        result = gh_service.get_diff("owner/repo", "prompts/greeting.md", "abc123")
        assert result is None

    def test_returns_none_on_github_error(self, gh_service):
        from github import GithubException
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo
        repo.compare.side_effect = GithubException(404, "Not Found", None)

        result = gh_service.get_diff("owner/repo", "prompts/greeting.md", "abc123")
        assert result is None


# ---------------------------------------------------------------------------
# create_or_update_files (bulk commit via Git Trees API)
# ---------------------------------------------------------------------------

class TestBulkCommit:
    def test_creates_multiple_files_in_one_commit(self, gh_service):
        repo = MagicMock()
        gh_service.gh.get_repo.return_value = repo

        # Set up the chain: ref → base_commit → base_tree
        mock_ref = MagicMock()
        mock_ref.object.sha = "base-ref-sha"
        repo.get_git_ref.return_value = mock_ref

        mock_base_commit = MagicMock()
        mock_base_commit.tree = MagicMock()
        repo.get_git_commit.return_value = mock_base_commit

        # Blob creation
        mock_blob = MagicMock()
        mock_blob.sha = "blob-sha"
        repo.create_git_blob.return_value = mock_blob

        # Tree creation
        mock_tree = MagicMock()
        repo.create_git_tree.return_value = mock_tree

        # Commit creation
        mock_new_commit = MagicMock()
        mock_new_commit.sha = "new-tree-commit-sha"
        repo.create_git_commit.return_value = mock_new_commit

        files = [
            {"path": "prompts/a.md", "content": "Content A"},
            {"path": "prompts/b.md", "content": "Content B"},
        ]

        sha = gh_service.create_or_update_files("owner/repo", files, "Bulk commit")
        assert sha == "new-tree-commit-sha"
        assert repo.create_git_blob.call_count == 2
        mock_ref.edit.assert_called_once_with("new-tree-commit-sha")


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

class TestClose:
    def test_close_calls_github_close(self, gh_service):
        gh_service.close()
        gh_service.gh.close.assert_called_once()
