from __future__ import annotations

import builtins
from typing import Any

import ast_comments as ast_c


_BUILTIN_NAMES = set(
    dir(builtins)
)


class DependencyChecker:
    """
    Performs static dependency analysis on selected AST nodes.

    The checker detects names referenced by loaded definitions that
    are not available from:

    - Python builtins
    - existing notebook namespace
    - previous %%load_clean executions
    - imports in the original module
    - other definitions loaded in the same operation
    """

    def __init__(
        self,
        tree: ast_c.Module,
        nodes: list[ast_c.AST],
        user_ns: dict[str, Any],
        loaded_registry: set[str],
    ) -> None:
        """
        Initialize dependency checker.

        Args:
            tree:
                Parsed module AST.

            nodes:
                Definitions being loaded.

            user_ns:
                Current IPython namespace.

            loaded_registry:
                Previously loaded names.
        """
        self.tree = tree
        self.nodes = nodes
        self.user_ns = user_ns
        self.loaded_registry = loaded_registry


    def check(self) -> list[tuple[str, str]]:
        """
        Find unresolved names.

        Returns:
            List of (owner, missing_name) pairs.
        """
        known = (
            set(self.user_ns)
            | self.loaded_registry
            | _BUILTIN_NAMES
            | self.module_imports()
            | self.selected_names()
        )

        warnings = []

        for node in self.nodes:
            missing = (
                self.free_names(node)
                - known
            )

            for name in sorted(missing):
                if not name.startswith("_"):
                    warnings.append(
                        (
                            getattr(
                                node,
                                "name",
                                "<module>",
                            ),
                            name,
                        )
                    )

        return warnings


    def selected_names(self) -> set[str]:
        """
        Return names defined in current load.

        Returns:
            Local definitions.
        """
        return {
            node.name
            for node in self.nodes
            if hasattr(node, "name")
        }


    def module_imports(self) -> set[str]:
        """
        Extract imported names from module.

        Returns:
            Available imported identifiers.
        """
        names = set()

        for node in ast_c.walk(self.tree):

            if isinstance(node, ast_c.Import):
                for alias in node.names:
                    names.add(
                        alias.asname
                        or alias.name.split(".")[0]
                    )

            elif isinstance(node, ast_c.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        names.add(
                            alias.asname
                            or alias.name
                        )

        return names


    def free_names(
        self,
        node: ast_c.AST,
    ) -> set[str]:
        """
        Extract unresolved names referenced by a node.

        Args:
            node:
                AST definition.

        Returns:
            Names loaded but not locally defined.
        """
        local = set()

        for child in ast_c.walk(node):

            if isinstance(
                child,
                (
                    ast_c.FunctionDef,
                    ast_c.AsyncFunctionDef,
                ),
            ):
                local.update(
                    self._arg_names(
                        child.args
                    )
                )

            elif isinstance(child, ast_c.Name):
                if isinstance(
                    child.ctx,
                    ast_c.Store,
                ):
                    local.add(
                        child.id
                    )

        free = set()

        for child in ast_c.walk(node):
            if (
                isinstance(child, ast_c.Name)
                and isinstance(
                    child.ctx,
                    ast_c.Load,
                )
                and child.id not in local
            ):
                free.add(
                    child.id
                )

        return free


    @staticmethod
    def _arg_names(
        args: ast_c.arguments,
    ) -> set[str]:
        """
        Extract function parameter names.

        Args:
            args:
                Function arguments AST.

        Returns:
            Parameter identifiers.
        """
        names = set()

        for group in (
            args.posonlyargs,
            args.args,
            args.kwonlyargs,
        ):
            names.update(
                arg.arg
                for arg in group
            )

        if args.vararg:
            names.add(
                args.vararg.arg
            )

        if args.kwarg:
            names.add(
                args.kwarg.arg
            )

        return names