from __future__ import annotations

import json
import sys
from typing import Annotated

import httpx
import typer
from annulus_core.config import load_settings
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
    """Check Annulus gateway and upstream Ollama health."""
    settings = load_settings()
    with _client(settings, timeout=10.0) as client:
        response = client.get("/health")
        response.raise_for_status()
        data = response.json()

    if json_output:
        typer.echo(json.dumps(data, indent=2))
    else:
        status = data.get("status", "unknown")
        ollama = data.get("ollama", "unknown")
        typer.echo(f"gateway: {status}")
        typer.echo(f"ollama:  {ollama}")
        if error := data.get("error"):
            typer.echo(f"error:   {error}", err=True)
            raise typer.Exit(code=1)
        if ollama != "ok":
            typer.echo("warning: Ollama is not reachable from the gateway", err=True)
            raise typer.Exit(code=1)


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
                        delta = chunk["choices"][0]["delta"]
                        content = delta.get("content")
                        if content:
                            typer.echo(content, nl=False)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                typer.echo()
        else:
            response = client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            typer.echo(content)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
