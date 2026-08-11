from pathlib import Path

import ast_comments as ast_c


MAX_BLANK_LINES = 2


class SourceSlicer:
    """
    Extract top-level definitions and assignments from a Python module
    while preserving original formatting.

    Supports:
        - explicit imports:
            from module import foo, bar

        - wildcard imports:
            from module import *
    """

    def __init__(
        self,
        source_path: str | Path,
        targets: dict[str, str] | None = None,
        *,
        mode: str = "default",
        import_all: bool = False,
    ):
        self.source_path = Path(source_path)
        self.mode = mode
        self.targets = targets or {}
        self.import_all = import_all

        self.source = self.source_path.read_text(
            encoding="utf-8"
        )

        self.lines = self.source.splitlines(
            keepends=True
        )

        self.tree = ast_c.parse(
            self.source
        )


    def build(self) -> str:
        nodes = self.selected_nodes()

        if not nodes:
            return ""

        output = []

        for index, node in enumerate(nodes):

            if index:
                output.append(
                    "\n" * self.leading_blank_lines(node)
                )

            if self.mode == "skeleton":
                output.append(
                    self.skeletonize(node)
                )
            else:
                output.append(
                    self.slice(node)
                )

        return "".join(output).rstrip() + "\n"


    def selected_nodes(self):
        if self.import_all:
            return [
                node
                for node in self.tree.body
                if not isinstance(
                    node,
                    (
                        ast_c.Import,
                        ast_c.ImportFrom,
                        ast_c.Comment,
                    ),
                )
            ]


        wanted = set(
            self.targets
        )

        selected = []

        for node in self.tree.body:

            if isinstance(
                node,
                (
                    ast_c.FunctionDef,
                    ast_c.AsyncFunctionDef,
                    ast_c.ClassDef,
                ),
            ):
                if node.name in wanted:
                    selected.append(node)


            elif isinstance(node, ast_c.Assign):

                names = [
                    target.id
                    for target in node.targets
                    if isinstance(
                        target,
                        ast_c.Name,
                    )
                ]

                if wanted.intersection(names):
                    selected.append(node)

        return selected


    def exported_names(self):

        names = []

        for node in self.selected_nodes():

            if isinstance(
                node,
                (
                    ast_c.FunctionDef,
                    ast_c.AsyncFunctionDef,
                    ast_c.ClassDef,
                ),
            ):
                if not node.name.startswith("_"):
                    names.append(node.name)


            elif isinstance(node, ast_c.Assign):

                for target in node.targets:
                    if (
                        isinstance(
                            target,
                            ast_c.Name,
                        )
                        and not target.id.startswith("_")
                    ):
                        names.append(target.id)

        return names


    def slice(self, node):

        start = self.start_line(node)
        end = node.end_lineno

        text = "".join(
            self.lines[start - 1:end]
        )

        if not text.endswith("\n"):
            text += "\n"

        return text


    def skeletonize(self, node):

        if isinstance(
            node,
            (
                ast_c.FunctionDef,
                ast_c.AsyncFunctionDef,
            ),
        ):
            return self.skeleton_function(node)


        if isinstance(node, ast_c.ClassDef):
            return self.skeleton_class(node)


        return self.slice(node)


    def skeleton_function(self, node):

        start = self.start_line(node)

        signature_end = (
            node.body[0].lineno - 1
            if node.body
            else node.end_lineno
        )

        header = "".join(
            self.lines[start - 1:signature_end]
        )

        return (
            header
            + "    # body omitted by load_clean\n"
            + "    pass\n"
        )


    def skeleton_class(self, node):

        start = self.start_line(node)

        end = (
            node.body[0].lineno - 1
            if node.body
            else node.end_lineno
        )

        header = "".join(
            self.lines[start - 1:end]
        )

        body = []

        for member in node.body:

            if isinstance(
                member,
                (
                    ast_c.FunctionDef,
                    ast_c.AsyncFunctionDef,
                ),
            ):
                body.append(
                    self.skeleton_function(member)
                )

            else:
                body.append(
                    self.slice(member)
                )


        return header + "".join(body)


    @staticmethod
    def start_line(node):

        decorators = getattr(
            node,
            "decorator_list",
            None,
        )

        if decorators:
            return decorators[0].lineno

        return node.lineno


    def leading_blank_lines(self, node):

        start = self.start_line(node)

        count = 0
        index = start - 2

        while (
            index >= 0
            and self.lines[index].strip() == ""
            and count < MAX_BLANK_LINES
        ):
            count += 1
            index -= 1

        return count