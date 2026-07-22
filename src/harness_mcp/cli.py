import sys
from pathlib import Path

import click

from harness_mcp import __version__
from harness_mcp.core import (
    add_servers,
    get_catalog,
    get_harness,
    get_status,
    remove_servers,
    search_catalog,
)


@click.group(invoke_without_command=False)
@click.version_option(__version__, prog_name="harness-mcp")
@click.option(
    "--harness",
    default=None,
    help="Harness to target (opencode, claude, cursor). Auto-detected if not specified.",
)
@click.option(
    "--scope",
    default="project",
    type=click.Choice(["project", "global"]),
    help="Where to write config (project or global)",
)
@click.option("--cwd", default=None, help="Working directory for project-scoped config")
def cli(harness, scope, cwd):
    ctx = click.get_current_context()
    cwd_path = Path(cwd) if cwd else Path.cwd()
    ctx.ensure_object(dict)
    ctx.obj["harness_name"] = harness
    ctx.obj["scope"] = scope
    ctx.obj["cwd"] = cwd_path

    h = get_harness(name=harness, cwd=cwd_path)
    if h is None:
        detected = get_harness(name=None, cwd=cwd_path)
        if detected:
            h = detected
        else:
            click.secho(
                "No harness detected. Use --harness to specify one (opencode, claude, cursor).",
                fg="red",
            )
            sys.exit(1)
    ctx.obj["harness"] = h
    ctx.obj["catalog"] = get_catalog()


def _prompt_missing_env_vars(harness, catalog, server_ids, env_overrides):
    """Prompt for required env vars that weren't provided via --env."""
    for sid in server_ids:
        server = catalog.get(sid)
        if server is None or not server.env_vars:
            continue

        required_missing = [
            ev for ev in server.env_vars
            if ev.required and ev.name not in env_overrides
        ]
        if not required_missing:
            continue

        click.secho(f"\n{server.name} needs:", fg="cyan")
        for ev in required_missing:
            hide = any(kw in ev.name.upper()
                       for kw in ("TOKEN", "KEY", "SECRET", "PASSWORD", "SECRETS", "API_KEY"))
            value = click.prompt(
                f"  {ev.name} ({ev.description})",
                default=ev.default or "",
                hide_input=hide,
                show_default=False,
            )
            if value:
                env_overrides[ev.name] = value
            else:
                env_overrides[ev.name] = harness.env_var_to_placeholder(ev.name)


@cli.command("list")
@click.pass_context
def ls(ctx):
    """List all available MCP servers in the catalog."""
    catalog = ctx.obj["catalog"]
    servers = catalog.all()

    if not servers:
        click.echo("No MCP servers found in catalog.")
        return

    click.secho("\nAvailable MCP Servers", bold=True, fg="cyan")
    click.secho("=" * 60, fg="cyan")

    for server_id, server in sorted(servers.items()):
        type_color = "green" if server.type == "local" else "yellow"
        click.secho(f"  {server_id}", fg="bright_white", bold=True, nl=False)
        click.secho(f"  [{server.type}]", fg=type_color)
        click.echo(f"    {server.description}")
        if server.tags:
            click.echo(f"    tags: {', '.join(server.tags)}")
        if server.env_vars:
            required = [e.name for e in server.env_vars if e.required]
            if required:
                click.echo(f"    env vars required: {', '.join(required)}")
        click.echo()


@cli.command()
@click.argument("servers", nargs=-1, required=True)
@click.option("--tag", default=None, help="Add all servers with this tag")
@click.option("--env", "-e", "env_vars", multiple=True, help="Environment variables (KEY=VALUE)")
@click.option("--dry-run", is_flag=True, help="Show what would be added without writing")
@click.pass_context
def add(ctx, servers, tag, env_vars, dry_run):
    """Add one or more MCP servers to your harness config."""
    harness = ctx.obj["harness"]
    catalog = ctx.obj["catalog"]
    scope = ctx.obj["scope"]
    cwd = ctx.obj["cwd"]

    to_add = list(servers)
    if tag:
        tagged = catalog.by_tag(tag)
        to_add.extend([s.id for s in tagged])

    if not to_add:
        click.secho("No servers specified.", fg="yellow")
        return

    env_overrides = {}
    for ev in env_vars:
        if "=" in ev:
            key, value = ev.split("=", 1)
            env_overrides[key] = value

    _prompt_missing_env_vars(harness, catalog, to_add, env_overrides)

    if dry_run:
        click.secho("[DRY RUN] Would add:", fg="yellow")
        for sid in to_add:
            server = catalog.get(sid)
            if server:
                click.echo(f"  + {sid} ({server.name}) - {server.type}")
            else:
                click.echo(f"  ? {sid} - not found in catalog")
        return

    result = add_servers(
        harness, catalog, to_add, scope=scope, cwd=cwd, env_overrides=env_overrides
    )

    if result["added"]:
        click.secho("Added servers:", fg="green")
        for sid in result["added"]:
            server = catalog.get(sid)
            click.echo(f"  + {sid} ({server.name if server else 'unknown'})")

        click.echo(f"\nConfig written to: {result['path']}")
        click.echo("Run 'harness-mcp status' to verify.")

    if result["skipped"]:
        click.secho("Skipped (already present or not found):", fg="yellow")
        for sid in result["skipped"]:
            click.echo(f"  - {sid}")


@cli.command()
@click.argument("servers", nargs=-1, required=True)
@click.option("--dry-run", is_flag=True, help="Show what would be removed without writing")
@click.pass_context
def remove(ctx, servers, dry_run):
    """Remove one or more MCP servers from your harness config."""
    harness = ctx.obj["harness"]
    scope = ctx.obj["scope"]
    cwd = ctx.obj["cwd"]

    if dry_run:
        click.secho("[DRY RUN] Would remove:", fg="yellow")
        for sid in servers:
            click.echo(f"  - {sid}")
        return

    result = remove_servers(harness, list(servers), scope=scope, cwd=cwd)

    if result["removed"]:
        click.secho("Removed servers:", fg="green")
        for sid in result["removed"]:
            click.echo(f"  - {sid}")
        click.echo(f"\nConfig updated: {result['path']}")

    if result["not_found"]:
        click.secho("Not found in config:", fg="yellow")
        for sid in result["not_found"]:
            click.echo(f"  - {sid}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show currently configured MCP servers."""
    harness = ctx.obj["harness"]
    scope = ctx.obj["scope"]
    cwd = ctx.obj["cwd"]

    result = get_status(harness, scope=scope, cwd=cwd)

    click.secho(f"\nHarness: {harness.name}", bold=True, fg="cyan")
    click.secho(f"Scope: {scope}", fg="cyan")
    click.secho("=" * 40, fg="cyan")

    if not result["servers"]:
        click.echo("No MCP servers configured.")
        click.echo("Run 'harness-mcp list' to see available servers.")
        return

    for name, info in sorted(result["servers"].items()):
        status_icon = "[enabled]" if info["enabled"] else "[disabled]"
        status_color = "green" if info["enabled"] else "red"
        click.secho(f"  {name}", fg="bright_white", bold=True, nl=False)
        click.secho(f"  {status_icon}  ({info['type']})", fg=status_color)

    click.echo(f"\nTotal: {result['count']} server(s)")


@cli.command()
@click.argument("query", required=False, default="")
@click.option("--tag", default=None, help="Filter by tag")
@click.pass_context
def search(ctx, query, tag):
    """Search the MCP server catalog."""
    catalog = ctx.obj["catalog"]

    if not query and not tag:
        click.secho("Provide a search query or --tag filter.", fg="yellow")
        return

    results = search_catalog(catalog, query, tag=tag)

    if not results:
        click.echo("No results found.")
        return

    click.secho(f"\nSearch results ({len(results)}):", bold=True, fg="cyan")
    click.secho("=" * 60, fg="cyan")

    for server in results:
        type_color = "green" if server.type == "local" else "yellow"
        click.secho(f"  {server.id}", fg="bright_white", bold=True, nl=False)
        if server.tags:
            click.echo(f"  [{', '.join(server.tags)}]")
        else:
            click.echo()
        click.echo(f"    {server.description}")
        click.secho(f"    type: {server.type}", fg=type_color)
        if server.env_vars:
            required = [e.name for e in server.env_vars if e.required]
            if required:
                click.secho(f"    requires: {', '.join(required)}", fg="yellow")
        click.echo()


@cli.command()
@click.option(
    "--harness",
    default=None,
    help="Harness to target. Auto-detected if not specified.",
)
@click.option(
    "--scope",
    default="project",
    type=click.Choice(["project", "global"]),
    help="Where to write config",
)
@click.pass_context
def init(ctx, harness, scope):
    """Interactive wizard to select and add MCP servers."""
    try:
        import questionary
    except ImportError:
        click.secho(
            "The 'init' command requires the 'questionary' package.\n"
            "Install it with: pip install harness-mcp[interactive]",
            fg="red",
        )
        sys.exit(1)

    catalog = ctx.obj["catalog"]
    h = ctx.obj.get("harness") or get_harness(name=harness, cwd=Path.cwd())

    if h is None:
        click.secho(
            "No harness detected. Use --harness to specify one.",
            fg="red",
        )
        sys.exit(1)

    all_servers = catalog.all()
    if not all_servers:
        click.echo("No MCP servers in catalog.")
        return

    choices = []
    for sid, server in sorted(all_servers.items()):
        tag_str = f" [{', '.join(server.tags)}]" if server.tags else ""
        type_str = "(local)" if server.type == "local" else "(remote)"
        choices.append(
            questionary.Choice(
                title=f"{sid} {type_str}{tag_str} - {server.description[:60]}...",
                value=sid,
            )
        )

    selected = questionary.checkbox(
        "Select MCP servers to add (space to select, enter to confirm):",
        choices=choices,
    ).ask()

    if not selected:
        click.echo("No servers selected.")
        return

    env_overrides = {}
    for sid in selected:
        server = catalog.get(sid)
        if server and server.env_vars:
            click.secho(f"\n{server.name} - Environment Variables:", fg="cyan")
            for ev in server.env_vars:
                label = f"{ev.name}"
                if ev.required:
                    label += " (required)"
                if ev.description:
                    label += f" - {ev.description}"

                value = questionary.text(
                    label,
                    default=ev.default or "",
                ).ask()

                if value:
                    env_overrides[ev.name] = value
                elif ev.required:
                    env_overrides[ev.name] = h.env_var_to_placeholder(ev.name)

    result = add_servers(
        h,
        catalog,
        selected,
        scope=scope,
        cwd=ctx.obj.get("cwd", Path.cwd()),
        env_overrides=env_overrides,
    )

    click.secho("\nDone!", fg="green", bold=True)
    click.echo(f"Added: {', '.join(result['added'])}")
    click.echo(f"Config: {result['path']}")
    if result["skipped"]:
        click.echo(f"Skipped: {', '.join(result['skipped'])}")


def main():
    cli()


if __name__ == "__main__":
    main()
