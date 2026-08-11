from __future__ import annotations

from IPython import get_ipython
from IPython.core.magic import Magics, cell_magic, magics_class

from .dependency import DependencyChecker
from .parser import VALID_MODES, parse_import, parse_line
from .renderer import render_array
from .resolver import resolve_module
from .slicer import SourceSlicer


class LoadCleanState:
    """
    Stores session-level state for %%load_clean.

    The registry tracks names imported by previous %%load_clean
    executions so dependency checking can resolve references
    across notebook cells.
    """

    def __init__(self) -> None:
        """Initialize an empty loaded-name registry."""
        self.loaded_registry: set[str] = set()


@magics_class
class LoadCleanMagics(Magics):
    """
    IPython magic implementation for loading clean source fragments.

    Supports:

        %%load_clean
        import module

    which is normalized into:

        from module import *

    Modes:

        default:
            Load full source and display exported names.

        skeleton:
            Load definitions with bodies replaced by pass.

        inline:
            Load full source without rendering export list.
    """

    def __init__(self, shell) -> None:
        """
        Initialize the magic extension.

        Args:
            shell:
                Active IPython shell instance.
        """
        super().__init__(shell)
        self.state = LoadCleanState()


    @cell_magic
    def load_clean(self, line: str, cell: str = "") -> None:
        """
        Load selected source from a Python module.

        The first import statement in the cell determines
        which module and objects are loaded.

        Example:

            %%load_clean

            import src.sorters.insertion_sort

        Automatically becomes:

            from src.sorters.insertion_sort import *

        Args:
            line:
                Magic arguments such as skeleton/default/inline.

            cell:
                Cell body containing the import statement.
        """
        mode, import_line = parse_line(line, cell)

        if mode not in VALID_MODES:
            print(f"Unknown mode {mode!r}. Expected {sorted(VALID_MODES)}")
            return

        try:
            (
                module,
                targets,
                import_all,
                normalized_import,
            ) = parse_import(import_line)

        except ValueError as exc:
            print(f"Invalid import: {exc}")
            return

        filepath = resolve_module(module)

        if filepath is None:
            print(f"Module not found: {module}")
            return

        slicer = SourceSlicer(
            filepath,
            targets,
            mode=mode,
            import_all=import_all,
        )

        source = slicer.build()

        if not source:
            print(f"No matching definitions found in {module}")
            return

        self._check_dependencies(slicer)

        self._execute(source, filepath)

        self._update_registry(slicer)

        output = source

        if mode == "default":
            output += "\n" + render_array(slicer.exported_names())

        self._rewrite_cell(mode, normalized_import, output)


    def _check_dependencies(self, slicer: SourceSlicer) -> None:
        """
        Run static dependency analysis and print warnings.

        Missing names are warnings only. They do not prevent execution.

        Args:
            slicer:
                SourceSlicer containing parsed module AST.
        """
        checker = DependencyChecker(
            slicer.tree,
            slicer.selected_nodes(),
            get_ipython().user_ns,
            self.state.loaded_registry,
        )

        for owner, missing in checker.check():
            print(
                f"[load_clean] warning: "
                f"'{owner}' references undefined name '{missing}'"
            )


    def _execute(self, source: str, filepath: str) -> None:
        """
        Execute generated source inside the IPython namespace.

        Args:
            source:
                Rendered Python source code.

            filepath:
                Original module path used for traceback display.
        """
        exec(
            compile(source, filepath, "exec"),
            get_ipython().user_ns,
        )


    def _update_registry(self, slicer: SourceSlicer) -> None:
        """
        Register names exported by the current load.

        Args:
            slicer:
                SourceSlicer containing loaded definitions.
        """
        self.state.loaded_registry.update(
            slicer.exported_names()
        )


    def _rewrite_cell(
        self,
        mode: str,
        import_line: str,
        source: str,
    ) -> None:
        """
        Replace the executed cell with normalized output.

        This allows rerunning the notebook cell without
        retyping the normalized import.

        Args:
            mode:
                Current %%load_clean mode.

            import_line:
                Normalized import statement.

            source:
                Generated source code.
        """
        rewritten = (
            f"%%load_clean {mode}\n"
            f"{import_line}\n\n"
            f"{source}"
        )

        get_ipython().set_next_input(
            rewritten,
            replace=True,
        )


def load_ipython_extension(ipython) -> None:
    """
    Register %%load_clean with IPython.

    Called automatically by:

        %load_ext load_clean

    Args:
        ipython:
            Active IPython shell instance.
    """
    ipython.register_magics(LoadCleanMagics)