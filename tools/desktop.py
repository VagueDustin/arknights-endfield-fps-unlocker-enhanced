"""VagueDustin Enterprises live desktop control panel."""
import ctypes
import datetime
import json
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageColor, ImageTk
import manage
import live_status
import desktop_state
from desktop_legacy import Panel as Actions, find_game

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)) / 'assets'
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
        window.title('Arknights Endfield FPS Unlocker • Enhanced')
        window.geometry('1100x860')
        window.minsize(960, 740)
        window.configure(fg_color=color('surface.base'))
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.events = queue.Queue()
        self.live_events = queue.Queue()
        self.busy = False
        self.closed = threading.Event()
        self.buttons = []
        self.status = tk.StringVar(value='Ready. Changes apply while the game is running.')
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
        wash = Image.new('RGB', (1100, 135))
        pixels = wash.load()
        for y in range(135):
            for x in range(1100):
                a = max(0, 1-((x-170)/900)**2-((y+10)/220)**2)*0.6
                b = max(0, 1-((x-950)/550)**2-((y+50)/230)**2)*0.07
                pixels[x,y] = tuple(int(base[i]*(1-a-b)+blue[i]*a+gold[i]*b) for i in range(3))
        self.wash = ImageTk.PhotoImage(wash)
        self.header.create_image(0,0,image=self.wash,anchor='nw')
        self.header.create_text(30,25,text='V A G U E D U S T I N   E N T E R P R I S E S',anchor='w',fill=color('accent.default'),font=('Inter',-11))
        self.header.create_text(28,62,text='ENDFIELD',anchor='w',fill=color('text.primary'),font=('Cinzel',-32))
        self.header.create_text(30,102,text='FPS UNLOCKER  /  ENHANCED',anchor='w',fill=color('text.muted'),font=('Inter',-13))
        self.live_badge = CanvasLabel(self.header,1070,30,'WAITING FOR GAME',12,'text.muted')
        self.cap_badge = CanvasLabel(self.header,1070,65,'Applied cap —',20,'text.primary')
        self.callback_badge = CanvasLabel(self.header,1070,104,'Waiting for runtime',12,'text.muted')
        self.header.bind('<Configure>',lambda event: [badge.move(event.width-30) for badge in (self.live_badge,self.cap_badge,self.callback_badge)])
        pathrow = ctk.CTkFrame(window, fg_color='transparent')
        pathrow.pack(fill='x', padx=30, pady=(10,14))
        self.entry(pathrow, self.game).pack(side='left',fill='x',expand=True,padx=(0,10))
        self.button(pathrow,'Game folder…',self.browse,False).pack(side='right')
        tabs = ctk.CTkTabview(window, fg_color=color('surface.base'),
            segmented_button_fg_color=color('surface.raised'), segmented_button_selected_color=color('surface.highest'),
            segmented_button_selected_hover_color=color('surface.highest'), segmented_button_unselected_color=color('surface.raised'),
            segmented_button_unselected_hover_color=color('surface.highest'), text_color=color('text.primary'))
        tabs.pack(fill='both',expand=True,padx=20)
        performance=tabs.add('Performance'); graphics_tab=tabs.add('Graphics'); recovery=tabs.add('Recovery & logs')
        graphics=ctk.CTkScrollableFrame(graphics_tab,fg_color=color('surface.base'));graphics.pack(fill='both',expand=True)
        self.section(performance,'Your refresh rate. Your rules.','Set your target, keep the game running, and apply changes instantly.')
        presets=ctk.CTkFrame(performance,fg_color='transparent'); presets.pack(fill='x',pady=16)
        for text,value in [('120 FPS','120'),('144 FPS','144'),('240 FPS','240'),('Unlimited','-1')]:
            self.button(presets,text,lambda value=value:self.fps.set(value),False).pack(side='left',padx=(0,10),expand=True,fill='x')
        self.field(performance,'Target FPS','−1 removes the cap', self.fps)
        self.field(performance,'Background FPS','Lower the cap when you switch away; 0 disables this limit',self.background)
        self.field(performance,'VSync','Choose how frames synchronize with your display', self.vsync,
                   ['Game setting','Off','Every refresh','Every 2 refreshes','Every 3 refreshes','Every 4 refreshes'])
        self.label(performance,'The applied cap is reported by the runtime. It is not a measured FPS counter.',12,'text.muted').pack(anchor='w',pady=18)
        self.section(graphics,'Tune the view.','Experimental controls. Game leaves each option under the game’s control.')
        for key,title,hint,values in [
            ('Anisotropic','Anisotropic filtering','Texture filtering mode',self.graphics_choices['Anisotropic']),
            ('Sharpening','Sharpening','Game or 0–100 percent',None),
            ('RenderScale','Render scale','Game or 50–200 percent; higher values increase GPU load',None),
            ('ShadowResolution','Shadow resolution','Maximum tile resolution',['Game','512','1024','2048','4096']),
            ('AmbientOcclusion','Ambient occlusion','Screen-space contact shading',self.graphics_choices['AmbientOcclusion']),
            ('TemporalAA','Temporal anti-aliasing','Controls TAAU; does not select DLSS or FSR',self.graphics_choices['TemporalAA'])]:
            self.field(graphics,title,hint,self.graphics_vars[key],values)
        self.button(graphics,'Reset graphics to game settings',lambda:self.run('reset_graphics'),False).pack(anchor='w',pady=10)
        self.section(recovery,'Keep a way back.','Upgrade, restore the original game files, or return to the previous build.')
        recoveryrow=ctk.CTkFrame(recovery,fg_color='transparent'); recoveryrow.pack(fill='x',pady=16)
        for label,action in [('Inspect installation','inspect'),('Previous build','rollback'),('Restore game files','restore')]:
            self.button(recoveryrow,label,lambda action=action:self.run(action),False).pack(side='left',padx=(0,10))
        self.output=ctk.CTkTextbox(recovery,fg_color=color('surface.sunken'),text_color=color('text.muted'),font=('Inter',12),height=220)
        self.output.pack(fill='both',expand=True); self.output.configure(state='disabled')
        self.runtime_output=ctk.CTkTextbox(recovery,fg_color=color('surface.sunken'),text_color=color('text.muted'),font=('Inter',11),height=120)
        self.runtime_output.pack(fill='x',pady=(8,0)); self.runtime_output.configure(state='disabled')
        bottom=ctk.CTkFrame(window,fg_color=color('surface.raised'),corner_radius=0)
        bottom.pack(fill='x',pady=(10,0))
        self.label(bottom,'',12,'text.muted',textvariable=self.status,wraplength=610).pack(side='left',padx=24,pady=16)
        self.button(bottom,'Apply live settings',lambda:self.run('configure')).pack(side='right',padx=(8,24),pady=16)
        self.button(bottom,'Install / update',lambda:self.run('install'),False).pack(side='right',pady=16)
        self.label(window,f'Provided by VagueDustin Enterprises™ · © {datetime.date.today().year} Endfield Enhancer. All rights reserved.',11,'text.faint').pack(pady=10)
        self.load_profile()
        if manage.state_path(Path(self.game.get())).exists():
            desktop_state.remember(Path(self.game.get()))
        window.after(100,self.poll)
        threading.Thread(target=self.watch,daemon=True).start()
    def label(self,parent,text,size=14,role='text.primary',display=False,**kw):
        return ctk.CTkLabel(parent,text=text,text_color=color(role),font=('Cinzel' if display else 'Inter',size),**kw)
    def button(self,parent,text,command,primary=True):
        button=ctk.CTkButton(parent,text=text,command=command,height=38,corner_radius=7,font=('Inter',13),
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
        self.label(left,title,14).pack(anchor='w'); self.label(left,hint,11,'text.muted').pack(anchor='w')
        if values:
            widget=ctk.CTkOptionMenu(row,variable=variable,values=values,width=185,height=34,font=('Inter',12),
                fg_color=color('surface.highest'),button_color=color('surface.highest'),button_hover_color=color('accent.pressed'),
                text_color=color('text.primary'),dropdown_fg_color=color('surface.raised'),dropdown_text_color=color('text.primary'),dropdown_hover_color=color('surface.highest'))
        else: widget=self.entry(row,variable)
        widget.pack(side='right',padx=16,pady=9)
    def watch(self):
        while not self.closed.is_set():
            try: self.live_events.put(live_status.snapshot())
            except Exception as error: self.live_events.put({'error':str(error)})
            self.closed.wait(2)
    def poll(self):
        try:
            success,result=self.events.get_nowait();self.busy=False
            for button in self.buttons:button.configure(state='normal')
            self.status.set('Settings saved. Check runtime status for confirmation.' if success else 'Action stopped. Details are in Recovery & logs.')
            self.output.configure(state='normal');self.output.delete('1.0','end');self.output.insert('1.0',result);self.output.configure(state='disabled')
            if success:self.load_profile()
        except queue.Empty:pass
        try:
            data=self.live_events.get_nowait()
            if 'error' in data:self.callback_badge.configure(text='Runtime status unavailable')
            else:
                self.live_badge.configure(text=f"● GAME RUNNING  ·  {data['pid']}" if data['running'] else 'WAITING FOR GAME',text_color=color('status.live' if data['running'] else 'text.muted'))
                cap=data['cap'];self.cap_badge.configure(text='Applied cap —' if cap is None else ('Uncapped' if cap==-1 else f'{cap} FPS applied cap'))
                self.callback_badge.configure(text=data['graphics'])
                self.runtime_output.configure(state='normal');self.runtime_output.delete('1.0','end');self.runtime_output.insert('1.0','\n'.join(data['lines']));self.runtime_output.configure(state='disabled');self.runtime_output.see('end')
        except queue.Empty:pass
        self.window.after(150,self.poll)
    def close(self):
        if self.busy:messagebox.showinfo('Action in progress','Wait for the current action to finish before closing.')
        else:self.closed.set();self.window.destroy()

if __name__=='__main__':
    register_fonts();ctk.set_appearance_mode('dark');root=ctk.CTk();panel=Panel(root)
    if '--smoke-test' in sys.argv:
        root.withdraw();root.update();panel.close()
    else:root.mainloop()
