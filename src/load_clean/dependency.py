import builtins
import ast_comments as ast_c


_BUILTIN_NAMES = set(dir(builtins))


class DependencyChecker:

    def __init__(
        self,
        tree,
        nodes,
        user_ns,
        loaded_registry,
    ):
        self.tree = tree
        self.nodes = nodes
        self.user_ns = user_ns
        self.loaded_registry = loaded_registry


    def check(self):

        known = (
            set(self.user_ns)
            | set(self.loaded_registry)
            | _BUILTIN_NAMES
            | self.module_imports()
        )

        warnings = []

        for node in self.nodes:

            missing = (
                self.free_names(node)
                - known
            )

            missing = {
                x
                for x in missing
                if not x.startswith("_")
            }

            for name in sorted(missing):
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


    def module_imports(self):

        names = set()

        for node in ast_c.walk(self.tree):

            if isinstance(
                node,
                ast_c.Import,
            ):
                for alias in node.names:
                    names.add(
                        alias.asname
                        or alias.name.split(".")[0]
                    )


            elif isinstance(
                node,
                ast_c.ImportFrom,
            ):
                for alias in node.names:
                    if alias.name != "*":
                        names.add(
                            alias.asname
                            or alias.name
                        )

        return names


    def free_names(self,node):

        local = set()

        for child in ast_c.walk(node):

            if isinstance(
                child,
                ast_c.Name,
            ):

                if isinstance(
                    child.ctx,
                    ast_c.Store,
                ):
                    local.add(
                        child.id
                    )

            elif isinstance(
                child,
                (
                    ast_c.FunctionDef,
                    ast_c.ClassDef,
                ),
            ):
                local.add(
                    child.name
                )


        free = set()

        for child in ast_c.walk(node):

            if (
                isinstance(child, ast_c.Name)
                and isinstance(
                    child.ctx,
                    ast_c.Load,
                )
            ):
                if child.id not in local:
                    free.add(
                        child.id
                    )

        return free