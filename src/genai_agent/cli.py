from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from genai_agent.agent import GenAILearningAgent
from genai_agent.config import AgentConfig
from genai_agent.notifiers import (
    save_markdown_digest,
    send_email_digest,
    send_telegram_digest,
)

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="genai-agent",
        description="Autonomous Gemini Agent that pulls and synthesizes the latest Generative AI papers, blogs, and news for your learning.",
    )
    parser.add_argument(
        "--topics",
        type=str,
        default=None,
        help="Comma-separated focus topics (overrides LEARNING_FOCUS_TOPICS in .env).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Lookback window in days for community & web news (default: 2).",
    )
    parser.add_argument(
        "--max-per-source",
        type=int,
        default=None,
        help="Maximum items to pull per source category (default: 10).",
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Fetch all sources and build a raw Markdown digest without calling Gemini API.",
    )
    parser.add_argument(
        "--agentic-tools",
        action="store_true",
        help="Run Gemini in autonomous function-calling loop to invoke source tools dynamically.",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Force sending digest to Telegram (even if TELEGRAM_ENABLED=false in .env).",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Force sending digest via Email (even if EMAIL_ENABLED=false in .env).",
    )
    parser.add_argument(
        "--no-notifications",
        action="store_true",
        help="Skip sending Telegram and Email notifications for this run.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print the full Markdown digest to the terminal (useful for cron jobs).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)

    config = AgentConfig.from_env()
    if args.topics:
        config.focus_topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    if args.days is not None:
        config.lookback_days = args.days
    if args.max_per_source is not None:
        config.max_items_per_source = args.max_per_source
    if args.send_telegram:
        config.telegram_enabled = True
    if args.send_email:
        config.email_enabled = True

    console.print(
        Panel.fit(
            f"[bold cyan]🚀 Generative AI Learning & News Agent[/bold cyan]\n"
            f"[dim]Model:[/dim] {config.gemini_model}  |  "
            f"[dim]Focus:[/dim] {', '.join(config.focus_topics[:5])}"
            + ("..." if len(config.focus_topics) > 5 else ""),
            border_style="cyan",
        )
    )

    if not config.gemini_api_key and not args.collect_only:
        console.print(
            "[yellow]⚠️  GEMINI_API_KEY is not set in .env or environment. "
            "Running in --collect-only mode (fetching live sources into a raw digest).[/yellow]"
        )

    agent = GenAILearningAgent(config)

    with console.status("[bold green]Pulling latest GenAI papers, blogs, community news & synthesizing digest...[/bold green]"):
        result = agent.run(
            collect_only=args.collect_only,
            agentic_tools_mode=args.agentic_tools,
        )

    # Display source collection summary table
    if result.sources_breakdown:
        table = Table(title="📡 Sources Pulled", show_header=True, header_style="bold magenta")
        table.add_column("Source Feed", style="cyan")
        table.add_column("Items Fetched", justify="right", style="green")
        for src_name, count in result.sources_breakdown.items():
            table.add_row(src_name, str(count))
        table.add_row("[bold]Total Unique Items[/bold]", f"[bold]{result.items_collected}[/bold]")
        console.print(table)

    # Save local Markdown digest
    saved_path = save_markdown_digest(
        markdown_content=result.markdown_content,
        output_dir=config.digest_output_dir,
        timestamp=result.generated_at,
    )
    result.saved_path = str(saved_path)
    console.print(f"[bold green]✔ Saved local Markdown digest:[/bold green] {saved_path}")

    # Notifications
    if not args.no_notifications:
        if config.telegram_enabled:
            with console.status("[cyan]Sending digest to Telegram...[/cyan]"):
                ok = send_telegram_digest(config, result.markdown_content)
            if ok:
                console.print("[bold green]✔ Telegram notification sent![/bold green]")
            else:
                console.print("[bold red]✖ Failed to send Telegram notification (check TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID).[/bold red]")

        if config.email_enabled:
            with console.status("[cyan]Sending digest via Email...[/cyan]"):
                ok = send_email_digest(config, subject=result.title, markdown_content=result.markdown_content)
            if ok:
                console.print(f"[bold green]✔ Email digest sent to {config.email_to}![/bold green]")
            else:
                console.print("[bold red]✖ Failed to send Email digest (check SMTP / Resend credentials in .env).[/bold red]")

    if not args.quiet:
        console.print("\n")
        console.print(Panel(Markdown(result.markdown_content), title=result.title, border_style="green"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
