"""GitHub API wrapper using PyGithub for reading/writing prompt files."""

from __future__ import annotations

import base64
import logging
from typing import Any

from github import Github, GithubException, InputGitAuthor

logger = logging.getLogger(__name__)


class GitHubService:
    """Wraps PyGithub to read/write .md prompt files in GitHub repos."""

    def __init__(self, access_token: str):
        self.gh = Github(access_token)

    def close(self):
        self.gh.close()

    # ── Read operations ──

    def list_repos(self) -> list[dict]:
        """List repos accessible to the authenticated user."""
        repos = []
        for repo in self.gh.get_user().get_repos(sort="updated"):
            repos.append({
                "full_name": repo.full_name,
                "name": repo.name,
                "owner": repo.owner.login,
                "default_branch": repo.default_branch,
                "private": repo.private,
                "description": repo.description,
            })
        return repos

    def list_orgs(self) -> list[dict]:
        """List organizations the user belongs to."""
        orgs = []
        for org in self.gh.get_user().get_orgs():
            orgs.append({
                "login": org.login,
                "avatar_url": org.avatar_url,
                "description": org.description,
            })
        return orgs

    def list_md_files(
        self, repo_full_name: str, subdirectory: str = "", branch: str = "main"
    ) -> list[dict]:
        """List all .md files in a repo/subdirectory."""
        repo = self.gh.get_repo(repo_full_name)
        path = subdirectory.strip("/") if subdirectory else ""

        files = []
        try:
            contents = repo.get_contents(path, ref=branch)
        except GithubException as e:
            logger.warning("Failed to list files in %s/%s: %s", repo_full_name, path, e)
            return []

        # Handle both single file and directory listing
        if not isinstance(contents, list):
            contents = [contents]

        queue = list(contents)
        while queue:
            item = queue.pop(0)
            if item.type == "dir":
                try:
                    sub_contents = repo.get_contents(item.path, ref=branch)
                    if isinstance(sub_contents, list):
                        queue.extend(sub_contents)
                except GithubException:
                    continue
            elif item.type == "file" and item.name.endswith(".md"):
                files.append({
                    "path": item.path,
                    "name": item.name,
                    "sha": item.sha,
                    "size": item.size,
                })
        return files

    def get_file_content(
        self, repo_full_name: str, file_path: str, branch: str = "main"
    ) -> tuple[str, str]:
        """Get file content and SHA. Returns (content, sha)."""
        repo = self.gh.get_repo(repo_full_name)
        file = repo.get_contents(file_path, ref=branch)
        if isinstance(file, list):
            raise ValueError(f"Expected file, got directory: {file_path}")
        content = base64.b64decode(file.content).decode("utf-8")
        return content, file.sha

    def get_file_history(
        self, repo_full_name: str, file_path: str, branch: str = "main", limit: int = 20
    ) -> list[dict]:
        """Get git commit history for a specific file."""
        repo = self.gh.get_repo(repo_full_name)
        commits = repo.get_commits(path=file_path, sha=branch)
        history = []
        for i, commit in enumerate(commits):
            if i >= limit:
                break
            history.append({
                "sha": commit.sha,
                "message": commit.commit.message,
                "author": commit.commit.author.name if commit.commit.author else None,
                "date": commit.commit.author.date.isoformat() if commit.commit.author else None,
            })
        return history

    def get_file_content_at_sha(
        self, repo_full_name: str, file_path: str, sha: str
    ) -> tuple[str, str]:
        """Get file content at a specific commit SHA. Returns (content, blob_sha)."""
        repo = self.gh.get_repo(repo_full_name)
        commit = repo.get_commit(sha)
        for file in commit.files:
            if file.filename == file_path:
                # Fetch the blob content at this commit
                tree = commit.commit.tree
                blob = self._find_blob_in_tree(repo, tree, file_path)
                if blob:
                    content = base64.b64decode(blob.content).decode("utf-8")
                    return content, blob.sha
        raise ValueError(f"File {file_path} not found at commit {sha}")

    def _find_blob_in_tree(self, repo, tree, file_path: str):
        """Walk the git tree to find a blob by file path."""
        parts = file_path.split("/")
        current_tree = tree
        for i, part in enumerate(parts):
            for element in current_tree.tree:
                if element.path == part:
                    if i == len(parts) - 1:
                        # Leaf node — should be a blob
                        return repo.get_git_blob(element.sha)
                    else:
                        # Directory — recurse into subtree
                        current_tree = repo.get_git_tree(element.sha)
                        break
            else:
                return None
        return None

    # ── Write operations ──

    def create_file(
        self,
        repo_full_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> str:
        """Create a new file in the repo. Returns the commit SHA."""
        repo = self.gh.get_repo(repo_full_name)
        author = None
        if author_name and author_email:
            author = InputGitAuthor(author_name, author_email)

        result = repo.create_file(
            path=file_path,
            message=commit_message,
            content=content,
            branch=branch,
            author=author,
        )
        return result["commit"].sha

    def update_file(
        self,
        repo_full_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        sha: str,
        branch: str = "main",
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> str:
        """Update an existing file. Requires current file SHA. Returns commit SHA."""
        repo = self.gh.get_repo(repo_full_name)
        author = None
        if author_name and author_email:
            author = InputGitAuthor(author_name, author_email)

        result = repo.update_file(
            path=file_path,
            message=commit_message,
            content=content,
            sha=sha,
            branch=branch,
            author=author,
        )
        return result["commit"].sha

    def delete_file(
        self,
        repo_full_name: str,
        file_path: str,
        commit_message: str,
        sha: str,
        branch: str = "main",
    ) -> str:
        """Delete a file from the repo. Returns commit SHA."""
        repo = self.gh.get_repo(repo_full_name)
        result = repo.delete_file(
            path=file_path,
            message=commit_message,
            sha=sha,
            branch=branch,
        )
        return result["commit"].sha

    def create_or_update_files(
        self,
        repo_full_name: str,
        files: list[dict],
        commit_message: str,
        branch: str = "main",
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> str:
        """Commit multiple files in a single commit using the Git Trees API.

        Args:
            files: List of dicts with 'path' and 'content' keys.
            commit_message: Message for the single commit.

        Returns the new commit SHA.
        """
        repo = self.gh.get_repo(repo_full_name)
        ref = repo.get_git_ref(f"heads/{branch}")
        base_commit = repo.get_git_commit(ref.object.sha)
        base_tree = base_commit.tree

        # Build tree elements for all files
        tree_elements = []
        for f in files:
            blob = repo.create_git_blob(f["content"], "utf-8")
            tree_elements.append({
                "path": f["path"],
                "mode": "100644",
                "type": "blob",
                "sha": blob.sha,
            })

        from github import InputGitTreeElement
        elements = [
            InputGitTreeElement(
                path=e["path"], mode=e["mode"], type=e["type"], sha=e["sha"]
            )
            for e in tree_elements
        ]
        new_tree = repo.create_git_tree(elements, base_tree)

        # Create commit
        author = None
        if author_name and author_email:
            author = InputGitAuthor(author_name, author_email)

        new_commit = repo.create_git_commit(
            commit_message, new_tree, [base_commit],
            author=author, committer=author,
        )
        ref.edit(new_commit.sha)

        return new_commit.sha

    def get_diff(
        self, repo_full_name: str, file_path: str, sha: str, branch: str = "main"
    ) -> str | None:
        """Get diff of a file between a specific commit and the current branch tip."""
        repo = self.gh.get_repo(repo_full_name)
        try:
            comparison = repo.compare(sha, branch)
            for file in comparison.files:
                if file.filename == file_path:
                    return file.patch
        except GithubException:
            return None
        return None
