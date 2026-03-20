"""Workspace management for AITerminalTools.

A workspace is an external directory "mounted" into the system. Unlike
traditional IDEs that store config in the target directory, workspace
metadata and brain data are stored centrally in workspace/<hash_id>/.

This avoids filesystem collisions and enables integrated management.
"""
