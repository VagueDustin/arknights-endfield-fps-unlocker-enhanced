"""VagueDustin Enterprises live desktop control panel."""
import ctypes
import datetime
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image, ImageColor, ImageTk
import manage
import live_status
import desktop_state
import neural
import reshade_setup
import webbrowser
from desktop_legacy import Panel as Actions, find_game

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)) / 'assets'
PRODUCT = json.loads((ASSETS / 'identity/product.json').read_text(encoding='utf-8-sig'))
TOKENS = json.loads((ASSETS / 'brand.json').read_text(encoding='utf-8-sig'))
def color(role):
    group, name = role.split('.')
    return TOKENS[group][name]

def register_fonts():
    if os.name == 'nt':
        for font in (ASSETS / 'fonts').glob('*.ttf'):
            ctypes.windll.gdi32.AddFontResourceExW(str(font), 0x10, 0)

class CanvasLabel:
    def __init__(self,canvas,x,y,text,size,role):
        self.canvas=canvas; self.y=y
        self.item=canvas.create_text(x,y,text=text,anchor='e',fill=color(role),font=('Inter',-size))
    def configure(self,text=None,text_color=None):
        if text is not None:self.canvas.itemconfigure(self.item,text=text)
        if text_color is not None:self.canvas.itemconfigure(self.item,fill=text_color)
    def move(self,x):self.canvas.coords(self.item,x,self.y)

class Panel(Actions):
    def __init__(self, window):
        self.window = window
        self.preview = '--preview' in sys.argv or '--smoke-test' in sys.argv
        window.title(f"{PRODUCT['name']} - {PRODUCT['subtitle']}")
        if os.name == 'nt':
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(PRODUCT['app_user_model_id'])
        icon_path = str(ASSETS / 'identity/fate-engine.ico')
        window.iconbitmap(icon_path)
        window.after(250, lambda: window.iconbitmap(icon_path))
        window.geometry('1160x850')
        window.minsize(1040, 760)
        window.configure(fg_color=color('surface.base'))
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.events = queue.Queue()
        self.live_events = queue.Queue()
        self.busy = False
        self.game_running = False
        self.closed = threading.Event()
        self.buttons = []
        self.runtime_warned = False
        self.status = tk.StringVar(value='Local design preview - game files are unchanged.' if self.preview else 'Ready. Apply settings while the game is running.')
        self.game = tk.StringVar(value=desktop_state.selected() or find_game())
        self.fps = tk.StringVar(value='144')
        self.background = tk.StringVar(value='30')
        self.vsync = tk.StringVar(value='Off')
        self.preset = tk.StringVar(value='high-refresh')
        self.graphics_preset = tk.StringVar(value='game')
        self.graphics_vars = {key: tk.StringVar(value='Game') for key in manage.GRAPHICS_DEFAULTS}
        self.graphics_choices = {'Anisotropic': ['Game', 'Off', 'Per texture', 'Force on'],
                                 'AmbientOcclusion': ['Game', 'Off', 'On'], 'TemporalAA': ['Game', 'Off', 'On']}
        self.header = tk.Canvas(window, bg=color('surface.base'), height=135, highlightthickness=0)
        self.header.pack(fill='x')
        # A static radial depth wash, derived entirely from the house semantic roles.
        base = ImageColor.getrgb(color('surface.base'))
        blue = ImageColor.getrgb(color('surface.highest'))
        gold = ImageColor.getrgb(color('accent.default'))
        wash = Image.new('RGB', (1800, 135))
        pixels = wash.load()
        for y in range(135):
            for x in range(1800):
                a = max(0, 1-((x-170)/900)**2-((y+10)/220)**2)*0.6
                b = max(0, 1-((x-950)/550)**2-((y+50)/230)**2)*0.07
                pixels[x,y] = tuple(int(base[i]*(1-a-b)+blue[i]*a+gold[i]*b) for i in range(3))
        self.wash = ImageTk.PhotoImage(wash)
        self.header.create_image(0,0,image=self.wash,anchor='nw')
        self.brand_icon = ImageTk.PhotoImage(Image.open(ASSETS / 'identity/fate-icon-source.png').resize((78,78),Image.Resampling.LANCZOS))
        self.header.create_image(28,28,image=self.brand_icon,anchor='nw')
        self.header.create_text(122,32,text=PRODUCT['publisher'].upper(),anchor='w',fill=color('accent.default'),font=('Inter',-11,'bold'))
        self.header.create_text(120,66,text=PRODUCT['name'],anchor='w',fill=color('text.primary'),font=('Inter',-34,'bold'))
        self.header.create_text(122,103,text=PRODUCT['subtitle'],anchor='w',fill=color('text.muted'),font=('Inter',-14))
        self.live_badge = CanvasLabel(self.header,1070,30,'WAITING FOR GAME',12,'text.muted')
        self.cap_badge = CanvasLabel(self.header,1070,65,'Applied cap -',20,'text.primary')
        self.callback_badge = CanvasLabel(self.header,1070,104,'Waiting for runtime',12,'text.muted')
        self.header.bind('<Configure>',lambda event: [badge.move(event.width-30) for badge in (self.live_badge,self.cap_badge,self.callback_badge)])
        pathrow = ctk.CTkFrame(window, fg_color='transparent')
        pathrow.pack(fill='x', padx=30, pady=(10,14))
        self.entry(pathrow, self.game).pack(side='left',fill='x',expand=True,padx=(0,10))
        self.button(pathrow,'Game folder…',self.browse,False).pack(side='right')
        workspace=ctk.CTkFrame(window,fg_color='transparent')
        workspace.pack(fill='both',expand=True,padx=24)
        rail=ctk.CTkFrame(workspace,width=180,fg_color=color('surface.base'),corner_radius=0)
        rail.pack(side='left',fill='y',padx=(0,24));rail.pack_propagate(False)
        self.label(rail,'CONTROL CENTER',11,'text.faint').pack(anchor='w',pady=(16,18))
        content=ctk.CTkFrame(workspace,fg_color='transparent');content.pack(side='left',fill='both',expand=True)
        self.pages={name:ctk.CTkFrame(content,fg_color='transparent') for name in ('Performance','Graphics','DLSS 5','Recovery')}
        self.navigation={}
        for name in self.pages:
            button=self.button(rail,name,lambda name=name:self.show_page(name),False)
            button.configure(anchor='w',height=46,width=170,border_width=0)
            button.pack(fill='x',pady=4);self.navigation[name]=button
        self.label(rail,'VERSION '+PRODUCT['version']+'\nEXPERIMENTAL',11,'text.faint',justify='left').pack(side='bottom',anchor='w',pady=22)
        self.label(rail,'Live settings\nLocal control\nReversible changes',12,'text.muted',justify='left').pack(side='bottom',anchor='w',pady=12)
        performance=self.pages['Performance'];graphics_tab=self.pages['Graphics'];recovery=self.pages['Recovery']
        nr=ctk.CTkScrollableFrame(self.pages['DLSS 5'],fg_color=color('surface.base'))
        nr.pack(fill='both',expand=True)
        self.section(nr,'DLSS 5 with ReShade','Install once, then adjust the picture inside Endfield.')
        self.section(nr,'1. Install ReShade','Close Endfield. The setup wizard will target Endfield.exe using Vulkan.')
        self.reshade_button=self.button(nr,'Open ReShade setup',self.reshade_action)
        self.reshade_button.pack(anchor='w',pady=6)
        self.section(nr,'2. Install neural rendering','Install the tested addon, Vulkan bridge, and NVIDIA runtime after ReShade setup finishes.')
        self.nr_setup_button=self.button(nr,'Install DLSS components',lambda:self.neural_action('install'))
        self.nr_setup_button.pack(anchor='w',pady=6)
        self.section(nr,'3. Launch through Epic','Enable DLSS in Endfield. Neural rendering starts off on a fresh setup.')
        self.label(nr,'Insert - toggle neural rendering on or off\nHome - open ReShade, finish or skip the tutorial, then find the RenoDX DLSS 5 controls\nChoose styles and presets in that overlay. Press Home again to return to the game.',13,'text.muted',justify='left',wraplength=690).pack(anchor='w',pady=6)
        self.label(nr,'NR can substantially reduce FPS. Compare the same scene with Insert before choosing a preset.',12,'text.muted',wraplength=690,justify='left').pack(anchor='w',pady=6)
        row=ctk.CTkFrame(nr,fg_color='transparent');row.pack(fill='x',pady=8)
        self.button(row,'Check setup',lambda:self.neural_action('inspect'),False).pack(side='left',padx=(0,8))
        self.button(row,'Setup guide',self.neural_instructions,False).pack(side='left')
        self.nr_output=ctk.CTkTextbox(nr,height=155,fg_color=color('surface.sunken'),font=('Inter',12))
        self.nr_output.pack(fill='x',pady=8)
        self.nr_output.insert('1.0','Choose Check setup to inspect installed components.');self.nr_output.configure(state='disabled')
        maintenance=ctk.CTkFrame(nr,fg_color='transparent')
        self.disclosure(nr,'repair and removal',maintenance).pack(anchor='w',pady=6)
        anchor=ctk.CTkFrame(nr,height=1,fg_color='transparent');anchor.pack(fill='x');maintenance._pack_anchor=anchor
        self.nr_write_buttons=[self.reshade_button,self.nr_setup_button]
        for label,action in [('Set toggle to Insert','insert'),('Remove DLSS components','restore')]:
            button=self.button(maintenance,label,lambda action=action:self.neural_action(action),False)
            button.pack(anchor='w',pady=4);self.nr_write_buttons.append(button)
        self.label(maintenance,'Close the game before setup, repair, or removal. ReShade itself is managed by its setup wizard. Removing components preserves your edited ReShade settings.',12,'text.muted',wraplength=690,justify='left').pack(anchor='w',pady=6)
        self.show_page('Performance')
        graphics=ctk.CTkScrollableFrame(graphics_tab,fg_color=color('surface.base'));graphics.pack(fill='both',expand=True)
        self.section(performance,'Performance','Step 1: choose Set up FPS unlocker (bottom right) with Endfield closed. Step 2: pick a frame-rate profile and save it.')
        presets=ctk.CTkFrame(performance,fg_color='transparent'); presets.pack(fill='x',pady=16)
        for text,value in [('120 FPS','120'),('144 FPS','144'),('240 FPS','240'),('Unlimited','-1')]:
            self.button(presets,text,lambda value=value:self.fps.set(value),False).pack(side='left',padx=(0,10),expand=True,fill='x')
        self.field(performance,'Target FPS','−1 removes the cap', self.fps)
        self.field(performance,'Background FPS','Lower the cap when you switch away; 0 disables this limit',self.background)
        self.field(performance,'VSync','Choose how frames synchronize with your display', self.vsync,
                   ['Game setting','Off','Every refresh','Every 2 refreshes','Every 3 refreshes','Every 4 refreshes'])
        self.label(performance,'The applied cap is reported by the runtime. It is not a measured FPS counter.',12,'text.muted').pack(anchor='w',pady=18)
        self.section(graphics,'Graphics','Requires FPS unlocker setup. Choose Game to keep Endfield\'s own setting.')
        profiles=ctk.CTkFrame(graphics,fg_color='transparent');profiles.pack(fill='x',pady=(4,8))
        for label,name in [('Game defaults','game'),('Crisp','crisp'),('Sharper (125%)','supersample')]:
            self.button(profiles,label,lambda name=name:self.show_graphics(manage.GRAPHICS_PRESETS[name]),False).pack(side='left',padx=(0,10))
        for key,title,hint,values in [
            ('Anisotropic','Anisotropic filtering','Texture filtering mode',self.graphics_choices['Anisotropic']),
            ('Sharpening','Sharpening','Game or 0-100 percent',None),
            ('RenderScale','Render scale','Game or 50-200 percent; higher values increase GPU load',None),
            ('ShadowResolution','Shadow resolution','Maximum tile resolution',['Game','512','1024','2048','4096']),
            ('AmbientOcclusion','Ambient occlusion','Screen-space contact shading',self.graphics_choices['AmbientOcclusion']),
            ('TemporalAA','Temporal anti-aliasing','Controls TAAU; does not select DLSS or FSR',self.graphics_choices['TemporalAA'])]:
            self.field(graphics,title,hint,self.graphics_vars[key],values)
        self.button(graphics,'Reset graphics to game settings',lambda:self.run('reset_graphics'),False).pack(anchor='w',pady=10)
        self.section(recovery,'FPS recovery & diagnostics','Restore the FPS unlocker files or return to a previous FPS build.')
        self.label(recovery,'Manage neural rendering separately on the DLSS 5 page.',12,'text.muted').pack(anchor='w',pady=6)
        recoveryrow=ctk.CTkFrame(recovery,fg_color='transparent'); recoveryrow.pack(fill='x',pady=16)
        for label,action in [('Inspect installation','inspect'),('Export diagnostics','export_diagnostics'),('Previous build','rollback'),('Remove FPS unlocker','restore')]:
            self.button(recoveryrow,label,lambda action=action:self.run(action),False).pack(side='left',padx=(0,10))
        self.output=ctk.CTkTextbox(recovery,fg_color=color('surface.sunken'),text_color=color('text.muted'),font=('Inter',12),height=220)
        self.output.pack(fill='both',expand=True)
        self.output.insert('1.0','Select Inspect installation to check the FPS unlocker and its recovery files.')
        self.output.configure(state='disabled')
        self.runtime_output=ctk.CTkTextbox(recovery,fg_color=color('surface.sunken'),text_color=color('text.muted'),font=('Inter',11),height=120)
        self.runtime_output.pack(fill='x',pady=(8,0)); self.runtime_output.configure(state='disabled')
        self.bottom=bottom=ctk.CTkFrame(window,fg_color=color('surface.raised'),corner_radius=0)
        bottom.pack(fill='x',pady=(10,0))
        self.label(bottom,'',12,'text.muted',textvariable=self.status,wraplength=590).pack(side='left',padx=24,pady=16)
        self.game_apply=self.button(bottom,'Apply game settings',lambda:self.run('configure'))
        self.game_apply.pack(side='right',padx=(8,24),pady=16)
        self.game_setup=self.button(bottom,'Set up FPS unlocker',lambda:self.run('install'),False)
        self.game_setup.pack(side='right',pady=16)
        self.label(window,f"Provided by VagueDustin Enterprises™ · © {datetime.date.today().year} {PRODUCT['name']}. All rights reserved.",11,'text.faint').pack(pady=10)
        self.load_profile()
        if not self.preview and manage.state_path(Path(self.game.get())).exists():
            desktop_state.remember(Path(self.game.get()))
        window.after(100,self.poll)
        window.after(500,lambda:self.neural_action('inspect') if not self.busy else None)
        threading.Thread(target=self.watch,daemon=True).start()
    def disclosure(self,parent,title,frame):
        frame._title=title
        frame._toggle_button=self.button(parent,'Show '+title,lambda:self.toggle_section(frame),False)
        return frame._toggle_button
    def toggle_section(self,frame):
        if frame.winfo_manager():
            frame.pack_forget();frame._toggle_button.configure(text='Show '+frame._title)
        else:
            frame.pack(fill='x',before=frame._pack_anchor,pady=6);frame._toggle_button.configure(text='Hide '+frame._title)
    def show_page(self,name):
        self.active_page=name
        if hasattr(self,'bottom'):
            self.game_apply.pack_forget();self.game_setup.pack_forget()
            if name in ('Performance','Graphics'):
                self.game_apply.pack(side='right',padx=(8,24),pady=16)
                self.game_setup.pack(side='right',pady=16)
        for page in self.pages.values():page.pack_forget()
        self.pages[name].pack(fill='both',expand=True)
        for key,button in self.navigation.items():
            button.configure(fg_color=color('surface.highest' if key==name else 'surface.base'),
                             text_color=color('accent.default' if key==name else 'text.muted'))
    def run(self,action):
        if self.preview and action not in ('inspect','diagnostics','export_diagnostics'):
            self.status.set('Design preview only. Applying or installing is disabled in this preview.')
            return
        super().run(action)
    def neural_action(self,action):
        if self.busy:
            return
        if self.preview and action != 'inspect':
            self.status.set('Design preview: DLSS writes are disabled.')
            return
        game=self.game.get()
        source=None
        if action=='install':
            source=reshade_setup.component_folder()
            if source is None:source=filedialog.askdirectory(title='Folder containing the three tested DLSS components')
            if not source:
                return
        self.busy=True
        for button in self.buttons:button.configure(state='disabled')
        self.status.set('Checking DLSS...' if action=='inspect' else 'Updating DLSS files...')
        def worker():
            try:
                if action=='install':
                    # Record before mutation so an interrupted install remains recoverable.
                    desktop_state.remember(neural.game_path(game))
                    result=neural.install(game,source)
                elif action=='restore':result=neural.restore(game)
                elif action=='inspect':result=neural.inspect(game)
                else:result=neural.configure(game,enabled={'enable':True,'disable':False}.get(action),insert=action=='insert')
                if action!='inspect':result['status']=neural.inspect(game)
                self.events.put((True,neural.summary(result),'neural'))
            except Exception as error:
                self.events.put((False,str(error),'neural'))
        threading.Thread(target=worker,daemon=True).start()
    def reshade_action(self):
        if self.busy or self.preview:return
        try:
            result=reshade_setup.launch(self.game.get())
            self.status.set(result)
        except Exception as error:messagebox.showerror('ReShade setup',str(error))
    def neural_instructions(self):
        messagebox.showinfo('DLSS 5 setup guide',
            '1. Close Endfield and select Open ReShade setup. Use the full addon build and Vulkan. Complete the official wizard; extra shader packs are optional.\n\n'
            '2. Return here and select Install DLSS components. The bundled release includes the tested files. Source-only builds ask you to select your downloaded components.\n\n'
            '3. Launch through Epic and enable DLSS in Endfield. Press Home to finish or skip the ReShade tutorial. Find the RenoDX DLSS 5 controls for styles, presets, and strength.\n\n'
            '4. Press Home to close the overlay. Insert toggles NR. On a fresh setup NR starts off. The overlay may lower FPS while open.\n\n'
            'To remove: close Endfield, remove DLSS components here, then run ReShade setup for the same game and choose Uninstall.\n\n'
            'Fate Engine checks files and saved settings; it does not measure whether neural rendering is active.')
    def label(self,parent,text,size=14,role='text.primary',display=False,**kw):
        return ctk.CTkLabel(parent,text=text,text_color=color(role),font=('Inter',size,'bold' if display else 'normal'),**kw)
    def button(self,parent,text,command,primary=True):
        button=ctk.CTkButton(parent,text=text,command=command,height=38,corner_radius=7,font=('Inter',13),
            width=max(140,min(270,len(text)*7+28)),text_color_disabled=color('text.muted'),
            fg_color=color('accent.default' if primary else 'surface.highest'),hover_color=color('accent.hover' if primary else 'surface.overlay'),
            text_color=color('text.inverse' if primary else 'text.primary'),border_width=0 if primary else 1,border_color=color('border.default'))
        self.buttons.append(button); return button
    def entry(self,parent,variable):
        return ctk.CTkEntry(parent,textvariable=variable,height=38,fg_color=color('surface.sunken'),text_color=color('text.primary'),border_color=color('border.default'),font=('Inter',13))
    def section(self,parent,title,subtitle):
        self.label(parent,title,22,display=True).pack(anchor='w',pady=(12,4))
        self.label(parent,subtitle,13,'text.muted').pack(anchor='w',pady=(0,8))
    def field(self,parent,title,hint,variable,values=None):
        row=ctk.CTkFrame(parent,fg_color=color('surface.raised'),corner_radius=8)
        row.pack(fill='x',pady=4)
        left=ctk.CTkFrame(row,fg_color='transparent');left.pack(side='left',padx=16,pady=9)
        self.label(left,title,14).pack(anchor='w'); self.label(left,hint,12,'text.muted',wraplength=435,justify='left').pack(anchor='w')
        if values:
            widget=ctk.CTkOptionMenu(row,variable=variable,values=values,width=185,height=34,font=('Inter',12),
                fg_color=color('surface.highest'),button_color=color('surface.highest'),button_hover_color=color('accent.pressed'),
                text_color=color('text.primary'),dropdown_fg_color=color('surface.raised'),dropdown_text_color=color('text.primary'),dropdown_hover_color=color('surface.highest'))
        else: widget=self.entry(row,variable)
        widget.pack(side='right',padx=16,pady=9)
    def update_nr_availability(self):
        for button in self.nr_write_buttons:
            button.configure(state='disabled' if self.busy or self.game_running or self.preview else 'normal')
        fps_installed=manage.state_path(Path(self.game.get())).exists()
        self.game_setup.configure(text='Update FPS unlocker' if fps_installed else 'Set up FPS unlocker',state='disabled' if self.busy or self.game_running or self.preview else 'normal')
        self.game_apply.configure(text='Apply game settings' if self.game_running else 'Save game settings',state='normal' if fps_installed and not self.busy and not self.preview else 'disabled')
        for button in (self.nr_setup_button,self.game_apply):
            button.configure(fg_color=color('surface.highest' if button.cget('state')=='disabled' else 'accent.default'))
    def watch(self):
        while not self.closed.is_set():
            try:
                data=live_status.snapshot()
                self.live_events.put(data)
                if data.get('running') and not self.preview:live_status.record_session(data)
            except Exception as error: self.live_events.put({'error':str(error)})
            self.closed.wait(2)
    FPS_MESSAGES={
        'install':('FPS unlocker installed. Launch Endfield; the header reports the applied cap once the runtime starts.','FPS unlocker setup stopped.'),
        'configure':('Game settings saved. A running game picks them up within about a second.','Game settings were not saved.'),
        'reset_graphics':('Graphics overrides released.','Graphics reset stopped.'),
        'restore':('FPS unlocker removed and the original compiler restored.','FPS unlocker removal stopped.'),
        'rollback':('Previous FPS build restored.','The previous build could not be restored.'),
        'inspect':('Installation inspected.','Inspection failed.'),
        'diagnostics':('Diagnostics collected.','Diagnostics failed.'),
        'export_diagnostics':('Diagnostics report saved.','The diagnostics report could not be saved.')}
    def poll(self):
        # One failing callback must never stop the event loop; the panel would look frozen.
        try:self.process_events()
        except Exception as error:self.report_failure(error)
        self.window.after(150,self.poll)
    def process_events(self):
        try:
            event=self.events.get_nowait();success,result=event[:2];self.busy=False
            for button in self.buttons:button.configure(state='normal')
            kind=event[2] if len(event)>2 else None
            if kind=='neural':
                self.status.set('DLSS setup checked.' if success else 'Could not complete the DLSS action. Details are on the DLSS 5 page.')
                self.nr_output.configure(state='normal');self.nr_output.delete('1.0','end');self.nr_output.insert('1.0',result);self.nr_output.configure(state='disabled')
            else:
                done,failed=self.FPS_MESSAGES.get(kind,('Finished.','Action stopped.'))
                self.status.set(done if success else failed+' Details are on the Recovery page.')
                self.output.configure(state='normal');self.output.delete('1.0','end');self.output.insert('1.0',result);self.output.configure(state='disabled')
                if success:self.load_profile()
                self.announce(kind,success,result)
        except queue.Empty:pass
        try:
            data=self.live_events.get_nowait()
            if 'error' in data:self.callback_badge.configure(text='Runtime status unavailable')
            else:
                running=data['running']
                self.live_badge.configure(text=f"● GAME RUNNING  ·  {data['pid']}" if running else 'WAITING FOR GAME',text_color=color('status.live' if running else 'text.muted'))
                self.game_running=running
                cap=data['cap'];self.cap_badge.configure(text='Applied cap -' if cap is None else ('Uncapped' if cap==-1 else f'{cap} FPS applied cap'))
                runtime=data.get('runtime','idle')
                if runtime=='missing':
                    self.callback_badge.configure(text='Runtime not detected',text_color=color('status.warning'))
                    if not self.runtime_warned:
                        self.runtime_warned=True
                        self.status.set('Endfield is running but the FPS runtime has not reported. Open Recovery, choose Inspect installation, then Export diagnostics.')
                elif runtime=='stopped':
                    self.callback_badge.configure(text='Runtime stopped - see Recovery log',text_color=color('status.warning'))
                else:
                    self.callback_badge.configure(text=data['graphics'],text_color=color('text.muted'))
                if not running:self.runtime_warned=False
                self.runtime_output.configure(state='normal');self.runtime_output.delete('1.0','end');self.runtime_output.insert('1.0','\n'.join(data['lines']));self.runtime_output.configure(state='disabled');self.runtime_output.see('end')
        except queue.Empty:pass
        self.update_nr_availability()
    def announce(self,kind,success,result):
        """Surface outcomes where the user is; the JSON detail stays on the Recovery page."""
        if kind in ('inspect','diagnostics',None):return
        if not success:
            if result.startswith('Windows denied write access'):
                if messagebox.askyesno('Administrator rights needed',result+'\n\nRestart Fate Engine as administrator now?'):self.relaunch_elevated()
            elif self.active_page!='Recovery':messagebox.showerror('Fate Engine',result)
            return
        if kind=='export_diagnostics':
            path=json.loads(result).get('path','')
            if path and os.name=='nt':subprocess.Popen(['explorer','/select,',path])
            messagebox.showinfo('Diagnostics saved','Report saved to:\n'+path+'\n\nAttach this file when reporting a problem.')
        elif kind in ('install','restore','rollback') and self.active_page!='Recovery':
            messagebox.showinfo('Fate Engine',self.FPS_MESSAGES[kind][0])
    def relaunch_elevated(self):
        if os.name!='nt':return
        if getattr(sys,'frozen',False):target,params=sys.executable,''
        else:target,params=sys.executable,subprocess.list2cmdline([str(Path(__file__).resolve())])
        if ctypes.windll.shell32.ShellExecuteW(None,'runas',target,params,None,1)>32:self.close()
        else:self.status.set('Administrator restart was cancelled. Grant write access to the game folder, then retry.')
    def report_failure(self,error):
        try:
            folder=Path(os.environ['LOCALAPPDATA'])/'EndfieldEnhancer';folder.mkdir(parents=True,exist_ok=True)
            with (folder/'desktop.log').open('a',encoding='utf-8') as log:
                log.write(datetime.datetime.now().isoformat(timespec='seconds')+' '+''.join(traceback.format_exception(error)))
        except Exception:pass
        self.busy=False
        for button in self.buttons:button.configure(state='normal')
        self.status.set('An unexpected error was written to desktop.log in the EndfieldEnhancer folder. The panel keeps running.')
    def close(self):
        if self.busy:messagebox.showinfo('Action in progress','Wait for the current action to finish before closing.')
        else:self.closed.set();self.window.destroy()

if __name__=='__main__':
    register_fonts();ctk.set_appearance_mode('dark');root=ctk.CTk();panel=Panel(root)
    if '--smoke-test' in sys.argv:
        root.withdraw();root.update();panel.close()
    else:root.mainloop()
