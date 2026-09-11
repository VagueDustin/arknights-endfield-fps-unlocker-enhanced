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
import desktop_state


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
        window.geometry('860x810')
        window.minsize(820, 740)
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
        graphics = ttk.LabelFrame(body, text='Graphics — experimental', padding=12)
        graphics.pack(fill='x', pady=12)
        self.graphics_preset = tk.StringVar(value='game')
        ttk.Label(graphics, text='Profile').grid(row=0, column=0, sticky='w')
        graphics_preset = ttk.Combobox(graphics, textvariable=self.graphics_preset,
            values=[*manage.GRAPHICS_PRESETS, 'custom'], state='readonly', width=18)
        graphics_preset.grid(row=0, column=1, sticky='w', pady=(0, 8))
        graphics_preset.bind('<<ComboboxSelected>>', self.choose_graphics_preset)
        self.graphics_vars = {key: tk.StringVar(value='Game') for key in manage.GRAPHICS_DEFAULTS}
        self.graphics_choices = {
            'Anisotropic': ['Game', 'Off', 'Per texture', 'Force on'],
            'ShadowResolution': ['Game', '512', '1024', '2048', '4096'],
            'AmbientOcclusion': ['Game', 'Off', 'On'], 'TemporalAA': ['Game', 'Off', 'On'],
        }
        for index, (key, label) in enumerate((('Anisotropic', 'Anisotropic filtering'),
                ('Sharpening', 'Sharpening (%)'), ('RenderScale', 'Render scale (%)'),
                ('ShadowResolution', 'Shadow maps (px)'), ('AmbientOcclusion', 'Ambient occlusion'),
                ('TemporalAA', 'Temporal AA (TAAU)'))):
            row, column = 1 + index // 2, (index % 2) * 2
            ttk.Label(graphics, text=label).grid(row=row, column=column, sticky='w', padx=(0, 8), pady=4)
            if key in self.graphics_choices:
                widget = ttk.Combobox(graphics, textvariable=self.graphics_vars[key],
                    values=self.graphics_choices[key], state='readonly', width=18)
            else:
                widget = ttk.Entry(graphics, textvariable=self.graphics_vars[key], width=21)
            widget.grid(row=row, column=column + 1, sticky='w', padx=(0, 18))
            self.graphics_vars[key].trace_add('write', self.update_graphics_preset)
        ttk.Label(graphics, text='Game releases the override. Apply one control at a time; diagnostics show accepted values.\nTAAU controls the game’s temporal AA, not DLSS/FSR. Render scale and shadows can increase GPU load.',
            wraplength=770).grid(row=4, column=0, columnspan=4, sticky='w', pady=(8, 0))
        actions = ttk.Frame(body)
        actions.pack(fill='x')
        self.buttons = []
        for label, action in [('Inspect', 'inspect'), ('Install/update', 'install'),
                              ('Apply settings', 'configure'), ('Reset graphics', 'reset_graphics'),
                              ('Previous build', 'rollback'), ('Uninstall', 'restore'), ('Diagnostics', 'diagnostics')]:
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

    def graphics_values(self):
        result = {}
        for key, variable in self.graphics_vars.items():
            text = variable.get().strip()
            if text.lower() == 'game':
                result[key] = -1
            elif key in ('Anisotropic', 'AmbientOcclusion', 'TemporalAA'):
                result[key] = self.graphics_choices[key].index(text) - 1
            else:
                result[key] = int(text)
        return result

    def show_graphics(self, values):
        for key, value in values.items():
            text = 'Game' if value == -1 else str(value)
            if value >= 0 and key in ('Anisotropic', 'AmbientOcclusion', 'TemporalAA'):
                text = self.graphics_choices[key][value + 1]
            self.graphics_vars[key].set(text)

    def choose_graphics_preset(self, _):
        values = manage.GRAPHICS_PRESETS.get(self.graphics_preset.get())
        if values is not None:
            self.show_graphics(values)

    def update_graphics_preset(self, *_):
        try:
            current = self.graphics_values()
            self.graphics_preset.set(next((name for name, values in manage.GRAPHICS_PRESETS.items()
                                           if current == values), 'custom'))
        except ValueError:
            self.graphics_preset.set('custom')

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
            graphics = {key: config.getint('Graphics', key, fallback=-1) for key in manage.GRAPHICS_DEFAULTS}
            manage.settings(fps, background, vsync, graphics)
            self.fps.set(str(fps))
            self.background.set(str(background))
            self.vsync.set(['Game setting', 'Off', 'Every refresh', 'Every 2 refreshes',
                           'Every 3 refreshes', 'Every 4 refreshes'][vsync + 1])
            self.show_graphics(graphics)
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
            if action in ('install', 'configure'):
                fps = int(self.fps.get())
                background = int(self.background.get())
                vsync = ['Game setting', 'Off', 'Every refresh', 'Every 2 refreshes',
                         'Every 3 refreshes', 'Every 4 refreshes'].index(self.vsync.get()) - 1
                graphics_values = self.graphics_values()
                config = manage.settings(fps, background, vsync, graphics_values)
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
                        desktop_state.remember(game)
                        function = manage.upgrade if manage.state_path(game).exists() else manage.install
                        result = function(game, manage.package_directory(), config)
                    elif action == 'restore':
                        result = manage.restore(game)
                    elif action == 'configure':
                        result = manage.configure(game, fps, background, vsync, graphics_values)
                    elif action == 'reset_graphics':
                        result = manage.configure(game, graphics=manage.GRAPHICS_DEFAULTS)
                    elif action == 'rollback':
                        result = manage.rollback(game)
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
            if success:
                self.load_profile()
        except queue.Empty:
            pass
        self.window.after(100, self.poll)


if __name__ == '__main__':
    root = tk.Tk()
    Panel(root)
    root.mainloop()
