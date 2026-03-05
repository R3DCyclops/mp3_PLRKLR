#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2026 m0reslav
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import os
import sys
from tkinter import Tk, Toplevel, Frame, Label, Button, Canvas, Scrollbar, END, IntVar, Radiobutton

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class Colors:
    BG_PRIMARY = "#121212"
    BG_SECONDARY = "#1E1E1E"
    BG_TERTIARY = "#252525"
    BG_HOVER = "#2D2D2D"
    ACCENT_PRIMARY = "#7C3AED"
    ACCENT_HOVER = "#8B5CF6"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#A1A1AA"
    TEXT_MUTED = "#71717A"

class StrategyWindow:
    def __init__(self, parent, app_dir, current_strategy=None):
        self.parent = parent
        self.app_dir = app_dir
        self.current_strategy = current_strategy
        self.selected_strategy = None
        self.strategy_files = []
        self.selected_var = IntVar(value=-1)
        self.mousewheel_binding = None
        
        self.window = Toplevel(parent)
        self.window.title("Выбор стратегии")
        self.window.geometry("500x600")
        self.window.resizable(False, False)
        self.window.configure(bg=Colors.BG_SECONDARY)
        self.window.attributes('-topmost', True)
        
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 500) // 2
        y = (self.window.winfo_screenheight() - 600) // 2
        self.window.geometry(f"500x600+{x}+{y}")
        
        self.setup_ui()
        self.load_strategies()
        
        self.window.grab_set()
        self.window.focus_set()
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def get_strat_dir(self):
        if getattr(sys, 'frozen', False):
            return resource_path("strat")
        else:
            return os.path.join(self.app_dir, "strat")
    
    def setup_ui(self):
        header_frame = Frame(self.window, bg=Colors.BG_SECONDARY)
        header_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        Label(
            header_frame,
            text="Стратегии поиска",
            font=('Segoe UI', 14, 'bold'),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_PRIMARY
        ).pack(anchor='w')
        
        Label(
            header_frame,
            text="Выберите одну стратегию для поиска музыки",
            font=('Segoe UI', 9),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_SECONDARY
        ).pack(anchor='w', pady=(5, 0))
        
        canvas_frame = Frame(self.window, bg=Colors.BG_SECONDARY)
        canvas_frame.pack(fill='both', expand=True, padx=20, pady=(10, 20))
        
        self.canvas = Canvas(canvas_frame, bg=Colors.BG_SECONDARY, highlightthickness=0)
        scrollbar = Scrollbar(canvas_frame, command=self.canvas.yview, bg=Colors.BG_TERTIARY)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.strategies_frame = Frame(self.canvas, bg=Colors.BG_SECONDARY)
        self.canvas.create_window((0, 0), window=self.strategies_frame, anchor='nw', width=440)
        
        def _on_mousewheel(event):
            try:
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass
        
        self.mousewheel_binding = self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        btn_frame = Frame(self.window, bg=Colors.BG_SECONDARY)
        btn_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.confirm_btn = Button(
            btn_frame,
            text="Подтвердить",
            command=self.on_confirm,
            bg=Colors.ACCENT_PRIMARY,
            fg=Colors.TEXT_PRIMARY,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=10
        )
        self.confirm_btn.pack(side='right', padx=(10, 0))
        
        Button(
            btn_frame,
            text="Отмена",
            command=self.on_cancel,
            bg=Colors.BG_TERTIARY,
            fg=Colors.TEXT_PRIMARY,
            font=('Segoe UI', 10),
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=10
        ).pack(side='right')
        
        info_label = Label(
            self.window,
            text="In Z we trust.",
            font=('Segoe UI', 8),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_MUTED
        )
        info_label.pack(pady=(0, 10))
    
    def load_strategies(self):
        strat_dir = self.get_strat_dir()
        
        if not os.path.exists(strat_dir):
            Label(
                self.strategies_frame,
                text="Папка strat/ не найдена",
                font=('Segoe UI', 10),
                bg=Colors.BG_SECONDARY,
                fg=Colors.ACCENT_PRIMARY
            ).pack(pady=20)
            return
        
        strategy_files = []
        for filename in os.listdir(strat_dir):
            if filename.startswith('strat') and filename.endswith('.txt'):
                strategy_files.append(filename)
        
        strategy_files.sort()
        
        if not strategy_files:
            Label(
                self.strategies_frame,
                text="Нет доступных стратегий",
                font=('Segoe UI', 10),
                bg=Colors.BG_SECONDARY,
                fg=Colors.TEXT_SECONDARY
            ).pack(pady=20)
            return
        
        self.strategy_files = strategy_files
        
        for i, filename in enumerate(strategy_files):
            filepath = os.path.join(strat_dir, filename)
            strategy_name = self._read_strategy_name(filepath)
            
            frame = Frame(self.strategies_frame, bg=Colors.BG_TERTIARY)
            frame.pack(fill='x', pady=(0, 10), padx=0)
            
            rb = Radiobutton(
                frame,
                text=strategy_name,
                variable=self.selected_var,
                value=i,
                bg=Colors.BG_TERTIARY,
                fg=Colors.TEXT_SECONDARY,
                font=('Segoe UI', 10),
                activebackground=Colors.BG_TERTIARY,
                activeforeground=Colors.TEXT_PRIMARY,
                cursor='hand2',
                selectcolor=Colors.ACCENT_PRIMARY
            )
            rb.pack(anchor='w', padx=15, pady=10)
            
            methods = self._read_strategy_methods(filepath)
            if methods:
                methods_label = Label(
                    frame,
                    text=f"Методы: {methods}",
                    font=('Segoe UI', 8),
                    bg=Colors.BG_TERTIARY,
                    fg=Colors.TEXT_MUTED
                )
                methods_label.pack(anchor='w', padx=15, pady=(0, 10))
        
        self.strategies_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        
        self.strategies_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        
        if self.current_strategy and self.current_strategy in self.strategy_files:
            idx = self.strategy_files.index(self.current_strategy)
            self.selected_var.set(idx)
        elif self.strategy_files:
            self.selected_var.set(0)
    
    def _read_strategy_name(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.readline().strip()
        except:
            return "Неизвестная стратегия"
    
    def _read_strategy_methods(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    return lines[1].strip()
        except:
            pass
        return ""
    
    def _cleanup_mousewheel(self):
        try:
            if self.mousewheel_binding:
                self.canvas.unbind_all("<MouseWheel>")
                self.mousewheel_binding = None
        except:
            pass
    
    def on_confirm(self):
        self._cleanup_mousewheel()
        
        selected_index = self.selected_var.get()
        if selected_index >= 0 and selected_index < len(self.strategy_files):
            self.selected_strategy = self.strategy_files[selected_index]
        else:
            self.selected_strategy = self.current_strategy
        
        self.window.destroy()
    
    def on_cancel(self):
        self._cleanup_mousewheel()
        
        self.selected_strategy = self.current_strategy
        self.window.destroy()
    
    def get_selected_strategy(self):
        return self.selected_strategy


def open_strategy_window(parent, app_dir, current_strategy=None):
    window = StrategyWindow(parent, app_dir, current_strategy)
    parent.wait_window(window.window)
    return window.get_selected_strategy()