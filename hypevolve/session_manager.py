"""Persistent agent sessions driven through CLI command templates."""
import abc
import json
import shlex
import subprocess
from pathlib import Path


def _extract_output(stdout: str) -> str:
    try:
        obj = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return stdout.strip()
    if isinstance(obj, dict) and "result" in obj:
        return str(obj["result"])
    return stdout.strip()


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
    raise ValueError(f"unknown agent kind: {kind}")
