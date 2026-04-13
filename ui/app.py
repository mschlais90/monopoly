import tkinter as tk
from ui.setup_frame import SetupFrame
from ui.game_frame import GameFrame
from ui.settings import Settings

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Monopoly Simulator')
        self.configure(bg='#1a1a2e')
        self.resizable(True, True)
        self.settings = Settings()
        self._current_frame = None
        self.show_setup()

    def show_setup(self):
        self._swap_frame(SetupFrame(self, on_start=self.start_game,
                                    settings=self.settings))

    def start_game(self, player_configs, starting_money):
        self._swap_frame(
            GameFrame(self, player_configs, starting_money,
                      on_menu=self.show_setup, settings=self.settings)
        )

    def _swap_frame(self, new_frame):
        if self._current_frame:
            self._current_frame.destroy()
        self._current_frame = new_frame
        new_frame.pack(fill='both', expand=True)
        self._fit_window()

    def _fit_window(self):
        self.update_idletasks()
        if isinstance(self._current_frame, GameFrame):
            self.geometry('1280x980')
        else:
            self.geometry('640x620')
        self.minsize(600, 500)