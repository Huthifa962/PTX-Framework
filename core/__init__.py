"""
PTX core package.

This package contains every subsystem of the PTX framework. Each module has a
single, well-defined responsibility so the framework stays maintainable and
easy to extend:

    colors      -- centralized color / style palette (professional only)
    banner      -- ASCII art startup banner
    config      -- runtime configuration + filesystem paths
    utils       -- small shared helpers (slugify, which, logging setup, ...)
    renderer    -- all Rich-based output (tables, panels, info cards, ...)
    parser      -- command line tokenizing + per-command -h/--help handling
    history     -- persistent command history
    database    -- dynamic loading of JSON/YAML knowledge base
    navigator   -- the level state machine (paths -> phase -> tools -> tool)
    search      -- fuzzy search across the loaded knowledge base
    installer   -- package-manager aware tool installation
    executor    -- safe launching of the selected tool binary
    workflow    -- roadmap / workflow diagrams
    commands    -- command handlers, wired to the navigator + renderer
    shell       -- the interactive prompt_toolkit REPL
    cli         -- top level application object / entry point glue
"""

__all__ = ["__version__"]

__version__ = "2.0.0"
