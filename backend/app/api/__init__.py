"""API package.

Each capability registers its endpoints as a router module under
``app/api/routers/`` exposing a module-level ``router`` object. The application
auto-discovers them so parallel worktrees add capabilities without editing
shared files.
"""
