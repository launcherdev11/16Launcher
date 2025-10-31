from PyQt5.QtCore import QThread, pyqtSignal

from mod_manager import ModManager


class ModSearchThread(QThread):
    search_finished = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)

    def __init__(
        self, query, version, loader, category, sort_by, project_type=None,
    ):
        super().__init__()
        self.query = query
        self.version = version
        self.loader = loader
        self.category = category
        self.sort_by = sort_by
        self.project_type = project_type

    def run(self):
        try:
            mods = ModManager.cached_search(
                self.query,
                self.version,
                self.loader,
                self.category,
                self.sort_by,
                "modrinth",
                self.project_type,
            )
            self.search_finished.emit(mods, self.query)
        except Exception as e:
            self.error_occurred.emit(str(e))
