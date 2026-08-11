from __future__ import annotations

from pathlib import Path
from typing import Any

from IPython import get_ipython
from IPython.core.magic import Magics, cell_magic, magics_class

from .dependency import DependencyChecker
from .parser import VALID_MODES, parse_import, parse_line
from .renderer import render_array
from .resolver import resolve_module
from .slicer import SourceSlicer


class LoadCleanState:
    """
    Stores session state shared between %%load_clean executions.

    Attributes:
        loaded_registry:
            Names successfully loaded by previous cells.
    """

    def __init__(self) -> None:
        """Initialize an empty load registry."""
        self.loaded_registry: set[str] = set()


@magics_class
class LoadCleanMagics(Magics):
    """
    Implements the %%load_clean IPython cell magic.

    Modes:

        default:
            Execute the module import normally.

        inline:
            Replace import with extracted source.

        skeleton:
            Replace import with definitions containing empty bodies.
    """

    def __init__(self, shell: Any) -> None:
        """
        Initialize magic state.

        Args:
            shell:
                Active IPython shell instance.
        """
        super().__init__(shell)
        self.state = LoadCleanState()


    @cell_magic
    def load_clean(
        self,
        line: str,
        cell: str = "",
    ) -> None:
        """
        Load Python definitions from a module.

        Example:

            %%load_clean inline
            import src.sorters.insertion_sort

        Args:
            line:
                Magic arguments.

            cell:
                Cell contents containing the import statement.
        """
        mode, import_line = parse_line(line, cell)

        if mode not in VALID_MODES:
            print(
                f"Unknown mode {mode!r}. "
                f"Expected {sorted(VALID_MODES)}"
            )
            return

        try:
            (
                module,
                targets,
                import_all,
                normalized_import,
            ) = parse_import(import_line)

        except ValueError as exc:
            print(exc)
            return

        filepath = resolve_module(module)

        if filepath is None:
            print(f"Module not found: {module}")
            return

        if mode == "default":
            imported_names = self._execute_import(
                normalized_import
            )

            self.state.loaded_registry.update(
                imported_names
            )

            self._rewrite_cell(
                mode,
                normalized_import,
                render_array(imported_names),
            )

            return


        slicer = SourceSlicer(
            filepath,
            targets,
            mode=mode,
            import_all=import_all,
        )

        source = slicer.build()

        if not source:
            print(
                f"No definitions found in {module}"
            )
            return


        self._check_dependencies(slicer)

        self._execute(source, filepath)

        self._update_registry(slicer)

        output = source

        if mode == "inline":
            output += "\n"

        output += render_array(
            slicer.exported_names()
        )

        self._rewrite_cell(
            mode,
            normalized_import,
            output,
        )

    def _execute_import(
            self,
            import_statement: str,
    ) -> list[str]:
        """
        Execute an import in an isolated namespace,
        then copy imported names into IPython.

        Args:
            import_statement:
                Normalized import statement.

        Returns:
            Names imported.
        """

        user_ns = get_ipython().user_ns

        temp_ns = {}

        exec(
            import_statement,
            temp_ns,
        )

        imported = [
            name
            for name in temp_ns
            if not name.startswith("__")
        ]

        user_ns.update(
            {
                name: temp_ns[name]
                for name in imported
            }
        )

        return sorted(imported)


    def _execute(
        self,
        source: str,
        filepath: Path,
    ) -> None:
        """
        Execute generated source code.

        Args:
            source:
                Generated Python source.

            filepath:
                Source filename for traceback reporting.
        """
        exec(
            compile(
                source,
                str(filepath),
                "exec",
            ),
            get_ipython().user_ns,
        )


    def _check_dependencies(
        self,
        slicer: SourceSlicer,
    ) -> None:
        """
        Run dependency analysis on extracted definitions.

        Missing dependencies are reported as warnings.

        Args:
            slicer:
                SourceSlicer containing parsed source.
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
                f"'{owner}' references undefined name "
                f"'{missing}'"
            )


    def _update_registry(
        self,
        slicer: SourceSlicer,
    ) -> None:
        """
        Store exported names for future dependency checks.

        Args:
            slicer:
                Loaded source slicer.
        """
        self.state.loaded_registry.update(
            slicer.exported_names()
        )

    def _rewrite_cell(
        self,
        mode: str,
        import_line: str,
        output: str,
    ) -> None:
        """
        Replace current cell with normalized output.

        Args:
            mode:
                Current load mode.

            import_line:
                Normalized import.

            output:
                Generated source.
        """
        rewritten = (
            f"%%load_clean {mode}\n"
            f"{import_line}\n\n"
            f"{output}"
        )

        get_ipython().set_next_input(
            rewritten,
            replace=True,
        )


def load_ipython_extension(
    ipython: Any,
) -> None:
    """
    Register %%load_clean with IPython.

    Args:
        ipython:
            Active IPython shell.
    """
    ipython.register_magics(
        LoadCleanMagics
    )