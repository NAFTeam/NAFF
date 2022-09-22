from pathlib import Path

from jurigged import watch, CodeFile
from jurigged.live import WatchOperation
from jurigged.codetools import (
    AddOperation,
    DeleteOperation,
    UpdateOperation,
    LineDefinition,
)
from naff import Extension, listen
from naff.client.errors import ExtensionLoadException, ExtensionNotFound
from naff.client.utils.misc_utils import find
from naff.ext.debug_extension.utils import get_all_commands

__all__ = ("DebugJurigged",)


class DebugJurigged(Extension):
    @listen(event_name="on_startup")
    async def jurigged_startup(self) -> None:
        """Jurigged starting utility."""
        self.command_cache = {}
        self.bot.sync_ext = True

        self.bot.logger.debug("Loading jurigged")
        path = Path().resolve()
        self.watcher = watch(f"{path}/[!.]*.py", logger=self.jurigged_log)
        self.watcher.prerun.register(self.jurigged_prerun)
        self.watcher.postrun.register(self.jurigged_postrun)

    def jurigged_log(self, event: WatchOperation | AddOperation | DeleteOperation | UpdateOperation) -> None:
        """
        Log a jurigged event

        Args:
            event: jurigged event
        """
        if isinstance(event, WatchOperation):
            self.bot.logger.debug(f"Watch {event.filename}")
        elif isinstance(event, (Exception, SyntaxError)):
            self.bot.logger.exception("Jurigged encountered an error", exc_info=True)
        else:
            event_str = "{action} {dotpath}:{lineno}{extra}"
            action = None
            lineno = event.defn.stashed.lineno
            dotpath = event.defn.dotpath()
            extra = ""

            if isinstance(event.defn, LineDefinition):
                dotpath = event.defn.parent.dotpath()
                extra = f" | {event.defn.text}"

            if isinstance(event, AddOperation):
                action = "Add"
                if isinstance(event.defn, LineDefinition):
                    action = "Run"
            elif isinstance(event, UpdateOperation):
                action = "Update"
            elif isinstance(event, DeleteOperation):
                action = "Delete"
            if not action:
                self.bot.logger.debug(event)
            else:
                self.bot.logger.debug(event_str.format(action=action, dotpath=dotpath, lineno=lineno, extra=extra))

    def jurigged_prerun(self, _path: str, cf: CodeFile) -> None:
        """
        Jurigged prerun event.

        Args:
            path: Path to file
            cf: File information
        """
        if self.bot.get_ext(cf.module_name):
            self.bot.logger.debug(f"Caching {cf.module_name}")
            self.command_cache = get_all_commands(cf.module)

    def jurigged_postrun(self, _path: str, cf: CodeFile) -> None:
        """
        Jurigged postrun event.

        Args:
            path: Path to file
            cf: File information
        """
        if self.bot.get_ext(cf.module_name):
            self.bot.logger.debug(f"Checking {cf.module_name}")
            commands = get_all_commands(cf.module)

            self.bot.logger.debug("Checking for changes")
            for module, cmds in commands.items():
                # Check if a module was removed
                if module not in commands:
                    self.bot.logger.debug(f"Module {module} removed")
                    self.bot.unload_extension(module)

                # Check if a module is new
                elif module not in self.command_cache:
                    self.bot.logger.debug(f"Module {module} added")
                    try:
                        self.bot.load_extension(module)
                    except ExtensionLoadException:
                        self.bot.logger.warning(f"Failed to load new module {module}")

                # Check if a module has more/less commands
                elif len(self.command_cache[module]) != len(cmds):
                    self.bot.logger.debug("Number of commands changed, reloading")
                    try:
                        self.bot.reload_extension(module)
                    except ExtensionNotFound:
                        try:
                            self.bot.load_extension(module)
                        except ExtensionLoadException:
                            self.bot.logger.warning(f"Failed to update module {module}")
                    except ExtensionLoadException:
                        self.bot.logger.warning(f"Failed to update module {module}")

                # Check each command for differences
                else:
                    for cmd in cmds:
                        old_cmd = find(
                            lambda x, cmd=cmd: x.resolved_name == cmd.resolved_name,
                            self.command_cache[module],
                        )

                        # Extract useful info
                        old_args = old_cmd.options
                        old_arg_names = []
                        new_arg_names = []
                        if old_args:
                            old_arg_names = [x.name.default for x in old_args]
                        new_args = cmd.options
                        if new_args:
                            new_arg_names = [x.name.default for x in new_args]

                        # No changes
                        if not old_args and not new_args:
                            continue

                        # Check if number of args has changed
                        if len(old_arg_names) != len(new_arg_names):
                            self.bot.logger.debug("Number of arguments changed, reloading")
                            try:
                                self.bot.reload_extension(module)
                            except Exception:
                                self.bot.logger.exception(f"Failed to update module {module}", exc_info=True)

                        # Check if arg names have changed
                        elif len(set(old_arg_names) - set(new_arg_names)) > 0:
                            self.bot.logger.debug("Argument names changed, reloading")
                            try:
                                self.bot.reload_extension(module)
                            except Exception:
                                self.bot.logger.exception(f"Failed to update module {module}", exc_info=True)

                        # Check if arg types have changed
                        elif any(new_args[idx].type != x.type for idx, x in enumerate(old_args)):
                            self.bot.logger.debug("Argument types changed, reloading")
                            try:
                                self.bot.reload_extension(module)
                            except Exception:
                                self.bot.logger.exception(f"Failed to update module {module}", exc_info=True)
                        else:
                            self.bot.logger.debug("No changes detected")
            self.command_cache.clear()


def setup(bot) -> None:
    DebugJurigged(bot)
