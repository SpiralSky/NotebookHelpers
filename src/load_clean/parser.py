import ast


VALID_MODES = {
    "default",
    "skeleton",
    "inline",
}


def parse_line(line: str, cell: str):
    """
    Parse:

        %%load_clean skeleton
        from foo import bar

    or:

        %%load_clean
        import foo.bar
    """

    mode = "default"
    import_line = ""

    line = line.strip()

    if line:
        parts = line.split(None, 1)

        if parts[0] in VALID_MODES:
            mode = parts[0]

            if len(parts) > 1:
                import_line = parts[1]

        else:
            import_line = line


    if not import_line:
        import_line = cell.splitlines()[0].strip()


    return mode, import_line



def parse_import(import_line: str):
    """
    Returns:

        module_path,
        targets,
        import_all,
        normalized_import
    """

    tree = ast.parse(
        import_line,
        mode="exec",
    )

    node = tree.body[0]


    # import foo.bar
    if isinstance(node, ast.Import):

        module = node.names[0].name

        return (
            module,
            {},
            True,
            f"from {module} import *",
        )


    # from foo import *
    if isinstance(node, ast.ImportFrom):

        module = node.module

        if any(
            alias.name == "*"
            for alias in node.names
        ):
            return (
                module,
                {},
                True,
                import_line,
            )


        targets = {
            alias.name:
            alias.asname or alias.name
            for alias in node.names
        }

        return (
            module,
            targets,
            False,
            import_line,
        )


    raise ValueError(
        f"Unsupported import: {import_line}"
    )