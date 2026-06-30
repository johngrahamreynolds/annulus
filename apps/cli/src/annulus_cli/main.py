from __future__ import annotations

import json
import sys
from typing import Annotated

import httpx
import typer
from annulus_core.config import load_settings
from annulus_retrieval.indexer import Indexer
from typer import Option

app = typer.Typer(
    name="annulus",
    help="Annulus local-first agentic AI platform CLI",
    no_args_is_help=True,
)


def _client(settings, timeout: float = 300.0) -> httpx.Client:
    headers = {"Authorization": f"Bearer {settings.gateway.api_key}"}
    return httpx.Client(base_url=settings.gateway_base_url(), headers=headers, timeout=timeout)


@app.command("health")
def health(
    json_output: Annotated[bool, Option("--json", help="Emit JSON")] = False,
) -> None:
    """Check Annulus gateway, index, and upstream Ollama health."""
    settings = load_settings()
    with _client(settings, timeout=10.0) as client:
        response = client.get("/health")
        response.raise_for_status()
        data = response.json()

    if json_output:
        typer.echo(json.dumps(data, indent=2))
    else:
        typer.echo(f"gateway:  {data.get('status', 'unknown')}")
        typer.echo(f"ollama:   {data.get('ollama', 'unknown')}")
        if compat := data.get("ollama_openai_compat"):
            typer.echo(f"ollama_openai_compat: {compat}")
        typer.echo(f"frontier: {data.get('frontier', 'unknown')}")
        index = data.get("index", {})
        typer.echo(f"index:    {index.get('files', 0)} files, {index.get('chunks', 0)} chunks")
        if error := data.get("ollama_error") or data.get("error"):
            typer.echo(f"error:    {error}", err=True)
            raise typer.Exit(code=1)
        if data.get("ollama") != "ok":
            typer.echo("warning: Ollama is not reachable from the gateway", err=True)
            raise typer.Exit(code=1)
        if data.get("ollama_openai_compat") not in (None, "ok"):
            typer.echo(
                f"warning: Ollama OpenAI-compatible API unavailable ({data.get('ollama_openai_compat')})",
                err=True,
            )
            if detail := data.get("ollama_error") or data.get("ollama_openai_compat_error"):
                typer.echo(f"detail:   {detail}", err=True)
            raise typer.Exit(code=1)


@app.command("index")
def index(
    rebuild: Annotated[bool, Option("--rebuild", help="Rebuild index from scratch")] = True,
    json_output: Annotated[bool, Option("--json", help="Emit JSON")] = False,
) -> None:
    """Index the workspace for retrieval (FTS5 over code and docs)."""
    settings = load_settings()
    indexer = Indexer(settings)
    stats = indexer.index_all(rebuild=rebuild)
    stats["index_db"] = str(settings.resolve_index_db())
    if json_output:
        typer.echo(json.dumps(stats, indent=2))
    else:
        typer.echo(f"Indexed {stats['files']} files, {stats['chunks']} chunks")
        typer.echo(f"Index DB: {settings.resolve_index_db()}")


@app.command("chat")
def chat(
    message: Annotated[str | None, typer.Argument(help="User message")] = None,
    model: Annotated[
        str | None, Option("--model", "-m", help="Model profile or Ollama model name")
    ] = None,
    stream: Annotated[bool, Option("--stream/--no-stream", help="Stream tokens")] = True,
) -> None:
    """Send a chat message to the Annulus gateway."""
    settings = load_settings()
    profile = model or settings.router.default_profile

    if message is None:
        if sys.stdin.isatty():
            typer.echo("Enter a message (Ctrl-D to send):")
        message = sys.stdin.read().strip()
        if not message:
            typer.echo("No message provided.", err=True)
            raise typer.Exit(code=1)

    payload = {
        "model": profile,
        "messages": [{"role": "user", "content": message}],
        "stream": stream,
    }

    with _client(settings) as client:
        if stream:
            with client.stream("POST", "/v1/chat/completions", json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if error := chunk.get("error"):
                        typer.echo(str(error), err=True)
                        raise typer.Exit(code=1)
                    try:
                        delta = chunk["choices"][0]["delta"]
                        for key in ("content", "reasoning_content"):
                            piece = delta.get(key)
                            if piece:
                                typer.echo(piece, nl=False)
                    except (KeyError, IndexError):
                        continue
                typer.echo()
        else:
            response = client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            meta = data.get("annulus", {})
            if meta:
                meta_line = (
                    f"[profile={data.get('model')} escalated={meta.get('escalated')} "
                    f"iterations={meta.get('iterations')} "
                    f"tools={meta.get('tool_calls')} "
                    f"hits={len(meta.get('retrieval_hits', []))}]"
                )
                typer.echo(meta_line)
            typer.echo(content)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
