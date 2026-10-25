"""Every registered level/argument/option must explain itself before release."""

import shlex
from contextlib import ExitStack

from typer.core import TyperGroup, TyperOption
from typer.main import get_command
from typer.testing import CliRunner

from k_web.cli import app
from k_web.help_text import COMMANDS


def commands(command, prefix=()):
    yield prefix, command
    if isinstance(command, TyperGroup):
        for name, child in command.commands.items():
            yield from commands(child, (*prefix, name))


def test_all_help_levels_have_three_examples_and_every_parameter_is_described():
    runner = CliRunner()
    found = []
    for path, command in commands(get_command(app)):
        found.append(path)
        assert command.help and command.help.count("```sh") >= 3, path
        for parameter in command.params:
            text = getattr(parameter, "help", None)
            assert text and len(text) >= 65, (path, parameter.name, text)
            assert "Example" in text or "example" in text, (path, parameter.name)
            if isinstance(parameter, TyperOption):
                aliases = parameter.opts + parameter.secondary_opts
                assert any(alias.startswith("--") for alias in aliases), (path, aliases)
                assert any(
                    alias.startswith("-") and not alias.startswith("--")
                    for alias in aliases
                ), (path, aliases)
        result = runner.invoke(app, [*path, "--help"], terminal_width=110)
        assert result.exit_code == 0, (path, result.output)
        assert "Examples" in result.stdout
        narrow = runner.invoke(app, [*path, "--help"], terminal_width=80)
        assert "…" not in narrow.stdout, path
    assert ("map", "search") in found and ("map", "request") in found
    assert len(found) == len(COMMANDS)


def test_all_published_examples_are_shell_parseable():
    for name, (_, examples) in COMMANDS.items():
        assert len(examples) >= 3, name
        for example in examples:
            assert shlex.split(example), (name, example)


def test_every_example_parses_through_the_real_cli_without_invoking_callbacks():
    """Validate real option/argument contracts without purging, recording or querying."""
    for key, (_, examples) in COMMANDS.items():
        for example in examples:
            words = shlex.split(example)
            if "web" not in words:
                continue
            words = words[words.index("web") + 1 :]
            for separator in ("|", "&&", ";"):
                if separator in words:
                    words = words[: words.index(separator)]
            current = get_command(app)
            with ExitStack() as stack:
                context = stack.enter_context(current.make_context("web", words))
                while isinstance(current, TyperGroup):
                    name, child, arguments = current.resolve_command(
                        context, [*context._protected_args, *context.args]
                    )
                    assert child is not None, (key, example)
                    context = stack.enter_context(
                        child.make_context(name, arguments, parent=context)
                    )
                    current = child


def test_rendered_doc_and_map_help_include_semantics_not_just_defaults():
    runner = CliRunner()
    doc = runner.invoke(app, ["doc", "--help"], terminal_width=110).stdout
    for phrase in (
        "lexical",
        "disclose",
        "Repeat",
        "OCR",
        "PDF pages",
        "default 3",
        "no cloud",
        "query",
    ):
        assert phrase.lower() in doc.lower()
    place = runner.invoke(app, ["map", "search", "--help"], terminal_width=110).stdout
    for phrase in (
        "geocode",
        "Nominatim",
        "viewbox",
        "address",
        "coordinates",
        "quota",
    ):
        assert phrase.lower() in place.lower()
