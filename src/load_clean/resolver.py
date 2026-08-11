import importlib.util


def resolve_module(module):
    spec = importlib.util.find_spec(module)

    if not spec or not spec.origin:
        raise ModuleNotFoundError(module)

    return spec.origin