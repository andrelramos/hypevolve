"""Persistent agent sessions driven through CLI command templates."""
import abc
import json
import shlex
import subprocess
import tempfile
from pathlib import Path


def _extract_output(stdout: str) -> str:
    try:
        obj = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return stdout.strip()
    if isinstance(obj, dict) and "result" in obj:
        return str(obj["result"])
    return stdout.strip()


def _read_last_message(path: Path) -> str:
    """Read agent's last message from --output-last-message file."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


class AgentSession(abc.ABC):
    def __init__(self, session_id: str, cwd: str) -> None:
        self.session_id = session_id
        self.cwd = cwd
        self.transcript_path: Path | None = None

    @abc.abstractmethod
    def send(self, prompt: str) -> str: ...

    def close(self) -> None:
        return None

    def _log(self, prompt: str, reply: str) -> None:
        if not self.transcript_path:
            return
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.transcript_path, "a", encoding="utf-8") as fh:
            fh.write(f"[PROMPT]\n{prompt}\n[/PROMPT]\n[RESPONSE]\n{reply}\n[/RESPONSE]\n")


class CmdAgentSession(AgentSession):
    def __init__(
        self,
        session_id: str,
        start_cmd_template: str,
        cont_cmd_template: str,
        cwd: str,
        timeout_seconds: int = 600,
        transcript_path: Path | None = None,
    ) -> None:
        super().__init__(session_id, cwd)
        self.start_template = start_cmd_template
        self.cont_template = cont_cmd_template
        self.timeout = timeout_seconds
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self._started = False

    def send(self, prompt: str) -> str:
        template = self.cont_template if self._started else self.start_template
        cmd = template.format(session_id=self.session_id)
        try:
            proc = subprocess.run(
                shlex.split(cmd),
                input=prompt,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"agent timed out: {cmd}") from exc
        if proc.returncode != 0:
            raise RuntimeError(f"agent failed ({proc.returncode}): {proc.stderr[-2000:]}")
        self._started = True
        reply = _extract_output(proc.stdout)
        self._log(prompt, reply)
        return reply


class CodexSession(AgentSession):
    """Non-interactive Codex CLI session (codex exec)."""

    def __init__(
        self,
        session_id: str,
        cwd: str,
        model: str | None = None,
        timeout_seconds: int = 600,
        transcript_path: Path | None = None,
    ) -> None:
        super().__init__(session_id, cwd)
        self.model = model
        self.timeout = timeout_seconds
        self.transcript_path = Path(transcript_path) if transcript_path else None

    def send(self, prompt: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=".codex-msg.txt", delete=False) as handle:
            out_file = Path(handle.name)
        cmd = [
            "codex", "exec",
            "--ephemeral",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-o", str(out_file),
        ]
        if self.model:
            cmd += ["-m", self.model]
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"codex timed out after {self.timeout}s") from exc
        reply = _read_last_message(out_file)
        if proc.returncode != 0 or not reply:
            # A non-zero exit means the agent never delivered a patch it stands behind
            # (out of credits, rate limited, crashed). Never fall back to stdout: the
            # stderr echo of the prompt would be parsed as if it were the agent's answer.
            err = (proc.stderr or "").strip()[-2000:]
            self._log(prompt, f"[agent error rc={proc.returncode}]\n{err}")
            raise RuntimeError(f"codex failed (rc={proc.returncode}): {err}")
        self._log(prompt, reply)
        try:
            out_file.unlink(missing_ok=True)
        except OSError:
            pass
        return reply


class FakeAgentSession(AgentSession):
    def __init__(
        self, session_id: str, cwd: str, replies: list[str], transcript_path: Path | None = None
    ) -> None:
        super().__init__(session_id, cwd)
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self._replies = list(replies)
        self.sent: list[str] = []

    def send(self, prompt: str) -> str:
        self.sent.append(prompt)
        if len(self._replies) > 1:
            reply = self._replies.pop(0)
        else:
            reply = self._replies[0]
        self._log(prompt, reply)
        return reply


class ClaudeSession(AgentSession):
    """Non-interactive Claude Code CLI session (claude -p)."""

    def __init__(
        self,
        session_id: str,
        cwd: str,
        model: str | None = None,
        timeout_seconds: int = 600,
        transcript_path: Path | None = None,
    ) -> None:
        super().__init__(session_id, cwd)
        self.model = model
        self.timeout = timeout_seconds
        self.transcript_path = Path(transcript_path) if transcript_path else None

    def send(self, prompt: str) -> str:
        cmd = [
            "claude", "-p",
            "--dangerously-skip-permissions",
            "--output-format", "text",
        ]
        if self.model:
            cmd += ["--model", self.model]
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"claude timed out after {self.timeout}s") from exc
        reply = proc.stdout.strip() if proc.stdout else ""
        if proc.returncode != 0 or not reply:
            err = (proc.stderr or "").strip()[-2000:]
            self._log(prompt, f"[agent error rc={proc.returncode}]\n{err}")
            raise RuntimeError(f"claude failed (rc={proc.returncode}): {err}")
        self._log(prompt, reply)
        return reply


def make_session(
    agent_cfg: dict, session_id: str, cwd: str, transcript_path: Path | None = None
) -> AgentSession:
    kind = agent_cfg.get("kind", "cmd")
    if kind == "fake":
        return FakeAgentSession(session_id, cwd, agent_cfg.get("replies", []), transcript_path=transcript_path)
    if kind == "cmd":
        return CmdAgentSession(
            session_id,
            agent_cfg["start_cmd_template"],
            agent_cfg["cont_cmd_template"],
            cwd,
            timeout_seconds=int(agent_cfg.get("timeout_seconds", 600)),
            transcript_path=transcript_path,
        )
    if kind == "codex":
        return CodexSession(
            session_id,
            cwd,
            model=agent_cfg.get("model"),
            timeout_seconds=int(agent_cfg.get("timeout_seconds", 600)),
            transcript_path=transcript_path,
        )
    if kind == "claude":
        return ClaudeSession(
            session_id,
            cwd,
            model=agent_cfg.get("model"),
            timeout_seconds=int(agent_cfg.get("timeout_seconds", 600)),
            transcript_path=transcript_path,
        )
    raise ValueError(f"unknown agent kind: {kind}")
