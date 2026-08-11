def render_array(names: list[str]) -> str:
    """
    Render the list of exported names shown below
    %%load_clean output.
    """

    if not names:
        return "[]\n"


    body = "".join(
        f"    {name},\n"
        for name in names
    )

    return (
        "[\n"
        f"{body}"
        "]\n"
    )