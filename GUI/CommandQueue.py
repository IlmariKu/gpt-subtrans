import logging

from PySide6.QtCore import QObject, Signal, QThreadPool, QMutex, QMutexLocker

from GUI.Command import Command
from GUI.ProjectDataModel import ProjectDataModel

class CommandQueue(QObject):
    """
    Execute commands on a background thread
    """
    commandAdded = Signal(object)
    commandExecuted = Signal(object, bool)

    undo_stack = []

    def __init__(self):
        super().__init__()

        self.command_pool = QThreadPool()
        self.mutex = QMutex()

        self.logger = logging.getLogger("CommandQueue")

    def Stop(self):
        """
        Shut the background thread down
        """
        self.command_pool.waitForDone()

    def AddCommand(self, command: Command, datamodel: ProjectDataModel = None, callback=None, undo_callback=None):
        """
        Add a command to the command queue, with optional callbacks for completion/undo events
        """
        if command:
            self.logger.debug(f"Adding a {type(command).__name__} command to the queue")
            with QMutexLocker(self.mutex):
                self._queue_command(command, datamodel, callback, undo_callback)

            self.commandAdded.emit(command)

    def _on_command_executed(self, command: Command, success: bool):
        """
        Handle command callbacks, and queuing further actions
        """
        self.logger.debug(f"A {type(command).__name__} command was completed")
        self.undo_stack.append(command)

        if command.commands_to_queue:
            with QMutexLocker(self.mutex):
                for command in command.commands_to_queue:
                    self._queue_command(command, command.datamodel)

            for command in command.commands_to_queue:
                self.logger.debug(f"Added a {type(command).__name__} command to the queue")
                self.commandAdded.emit(command)

        self.commandExecuted.emit(command, success)

    def _queue_command(self, command: Command, datamodel: ProjectDataModel = None, callback=None, undo_callback=None):
        """
        Add a command to the worker thread queue
        """
        if datamodel:
            command.SetDataModel(datamodel)
        if callback:
            command.SetCallback(callback)
        if undo_callback:
            command.SetUndoCallback(undo_callback)

        command.commandExecuted.connect(self._on_command_executed)

        self.command_pool.start(command)