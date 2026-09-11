"""Small desktop control panel for the reversible FPS package."""
import json
import configparser
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import manage


def find_game():
    manifests = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'Epic/EpicGamesLauncher/Data/Manifests'
    for path in manifests.glob('*.item'):
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if 'endfield' not in data.get('DisplayName', '').lower():
                continue
            root = Path(data['InstallLocation'])
            for candidate in (root, root / 'games/EndField Game'):
                if (candidate / 'Endfield.exe').is_file():
                    return str(candidate)
        except (OSError, ValueError, KeyError):
            continue
    return ''


class Panel:
    def __init__(self, window):
        self.window = window
        window.title('Endfield Enhancer — experimental')
        window.geometry('780x630')
        window.minsize(700, 580)
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.events = queue.Queue()
        self.busy = False
        body = ttk.Frame(window, padding=20)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Endfield Enhancer', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
        ttk.Label(body, text='FPS controls • Reversible installation • Runtime diagnostics').pack(anchor='w', pady=(0, 18))
        ttk.Label(body, text='Game folder (contains Endfield.exe)').pack(anchor='w')
        row = ttk.Frame(body)
        row.pack(fill='x', pady=(4, 14))
        self.game = tk.StringVar(value=find_game())
        ttk.Entry(row, textvariable=self.game).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='Browse…', command=self.browse).pack(side='left', padx=(8, 0))
        controls = ttk.LabelFrame(body, text='FPS profile', padding=12)
        controls.pack(fill='x')
        self.preset = tk.StringVar(value='balanced')
        self.fps = tk.StringVar(value='120')
        self.background = tk.StringVar(value='0')
        self.vsync = tk.StringVar(value='Off')
        ttk.Label(controls, text='Preset').grid(row=0, column=0, sticky='w', padx=(0, 12))
        preset = ttk.Combobox(controls, textvariable=self.preset,
                              values=[*manage.PRESETS, 'custom'], state='readonly', width=18)
        preset.grid(row=0, column=1, sticky='w')
        preset.bind('<<ComboboxSelected>>', self.choose_preset)
        self.fps.trace_add('write', self.update_preset)
        for index, (label, variable) in enumerate((('FPS (−1 = unlimited)', self.fps),
                                                  ('Background FPS (0 = off)', self.background)), 1):
            ttk.Label(controls, text=label).grid(row=index, column=0, sticky='w', pady=7)
            ttk.Entry(controls, textvariable=variable, width=21).grid(row=index, column=1, sticky='w')
        ttk.Label(controls, text='VSync').grid(row=3, column=0, sticky='w')
        ttk.Combobox(controls, textvariable=self.vsync, state='readonly', width=18,
            values=['Game setting', 'Off', 'Every refresh', 'Every 2 refreshes', 'Every 3 refreshes', 'Every 4 refreshes']).grid(row=3, column=1, sticky='w')
        ttk.Label(controls, text='VSync can take priority over your FPS cap.\nApply settings while playing; install or restore with the game closed.',
                  wraplength=340).grid(row=0, column=2, rowspan=4, padx=22, sticky='nw')
        ttk.Label(body, text='Graphics: game defaults. AA, shadows, AO, and render-scale overrides await validation.',
                  wraplength=720).pack(anchor='w', pady=12)
        actions = ttk.Frame(body)
        actions.pack(fill='x')
        self.buttons = []
        for label, action in [('Inspect', 'inspect'), ('Install', 'install'),
                              ('Apply settings', 'configure'), ('Restore original', 'restore'),
                              ('Diagnostics', 'diagnostics')]:
            button = ttk.Button(actions, text=label, command=lambda action=action: self.run(action))
            button.pack(side='left', padx=(0, 6))
            self.buttons.append(button)
        self.status = tk.StringVar(value='Experimental build. Inspect your installation to begin.')
        ttk.Label(body, textvariable=self.status, wraplength=720).pack(anchor='w', pady=10)
        self.output = tk.Text(body, height=10, wrap='word', font=('Consolas', 10), state='disabled')
        self.output.pack(fill='both', expand=True)
        self.load_profile()
        window.after(100, self.poll)

    def choose_preset(self, _):
        if self.preset.get() in manage.PRESETS:
            self.fps.set(str(manage.PRESETS[self.preset.get()]))

    def update_preset(self, *_):
        self.preset.set(next((name for name, value in manage.PRESETS.items()
                             if str(value) == self.fps.get()), 'custom'))

    def close(self):
        if self.busy:
            messagebox.showinfo('Action in progress', 'Wait for the current action to finish before closing.')
        else:
            self.window.destroy()

    def load_profile(self):
        path = Path(self.game.get()) / manage.CONFIG
        if not path.is_file() or path.is_symlink():
            return
        try:
            config = configparser.ConfigParser()
            config.read(path)
            fps = config['FPS'].getint('Target')
            background = config['FPS'].getint('Background')
            vsync = config['FPS'].getint('VSync')
            manage.settings(fps, background, vsync)
            self.fps.set(str(fps))
            self.background.set(str(background))
            self.vsync.set(['Game setting', 'Off', 'Every refresh', 'Every 2 refreshes',
                           'Every 3 refreshes', 'Every 4 refreshes'][vsync + 1])
        except (OSError, ValueError, KeyError, configparser.Error):
            self.status.set('Could not read existing settings; inspect the installation before applying changes.')

    def browse(self):
        selected = filedialog.askdirectory(title='Select Endfield game folder')
        if selected:
            self.game.set(selected)
            self.load_profile()

    def run(self, action):
        if self.busy:
            return
        try:
            game = Path(self.game.get()).resolve(strict=True)
            if not (game / 'Endfield.exe').is_file():
                raise ValueError('Select the folder containing Endfield.exe')
            fps = int(self.fps.get())
            background = int(self.background.get())
            vsync = ['Game setting', 'Off', 'Every refresh', 'Every 2 refreshes',
                     'Every 3 refreshes', 'Every 4 refreshes'].index(self.vsync.get()) - 1
            config = manage.settings(fps, background, vsync)
        except (ValueError, OSError) as error:
            messagebox.showerror('Check settings', str(error))
            return
        self.busy = True
        for button in self.buttons:
            button.configure(state='disabled')
        self.status.set(f'{action.capitalize()} in progress…')
        def worker():
            try:
                with manage.locked(game):
                    if action == 'install':
                        result = manage.install(game, manage.package_directory(), config)
                    elif action == 'restore':
                        result = manage.restore(game)
                    elif action == 'configure':
                        result = manage.configure(game, fps, background, vsync)
                    else:
                        result = manage.diagnostics(game)
                self.events.put((True, json.dumps(result, indent=2)))
            except Exception as error:
                self.events.put((False, str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            success, result = self.events.get_nowait()
            self.busy = False
            for button in self.buttons:
                button.configure(state='normal')
            self.status.set('Finished. See details below.' if success else 'Action stopped. See details below.')
            self.output.configure(state='normal')
            self.output.delete('1.0', 'end')
            self.output.insert('1.0', result)
            self.output.configure(state='disabled')
        except queue.Empty:
            pass
        self.window.after(100, self.poll)


if __name__ == '__main__':
    root = tk.Tk()
    Panel(root)
    root.mainloop()
