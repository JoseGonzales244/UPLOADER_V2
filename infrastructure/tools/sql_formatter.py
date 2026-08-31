import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

class SQLListFormatterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Convertidor de Listas a SQL IN - Interbank")
        self.root.geometry("680x520")
        self.root.minsize(550, 420)
        
        # Estilo visual moderno
        style = ttk.Style()
        style.theme_use('clam')
        
        # Color Palette: Indigo / Interbank Blue
        BG_COLOR = "#F4F6F9"
        PRIMARY_COLOR = "#0039A6"
        BUTTON_COLOR = "#0052CC"
        
        self.root.configure(bg=BG_COLOR)
        
        # Contenedor Principal
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        lbl_title = tk.Label(
            main_frame, 
            text="⚡ Formateador de Listas a Consulta SQL (IN)", 
            font=("Segoe UI", 14, "bold"), 
            bg=BG_COLOR, 
            fg=PRIMARY_COLOR
        )
        lbl_title.pack(anchor="w", pady=(0, 10))
        
        # Opciones de Formato
        opts_frame = tk.Frame(main_frame, bg=BG_COLOR)
        opts_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.var_quote = tk.BooleanVar(value=True)
        chk_quote = tk.Checkbutton(
            opts_frame, 
            text="Agregar Comillas ('val1', 'val2')", 
            variable=self.var_quote, 
            bg=BG_COLOR, 
            font=("Segoe UI", 10),
            command=self.format_text
        )
        chk_quote.pack(side=tk.LEFT, padx=(0, 15))

        self.var_parens = tk.BooleanVar(value=False)
        chk_parens = tk.Checkbutton(
            opts_frame, 
            text="Envolver en Paréntesis ('val1', 'val2')", 
            variable=self.var_parens, 
            bg=BG_COLOR, 
            font=("Segoe UI", 10),
            command=self.format_text
        )
        chk_parens.pack(side=tk.LEFT)

        # Panel Split: Entrada vs Salida
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # Entrada
        lbl_in = tk.Label(text_frame, text="Entrada (Pegue la lista vertical aquí):", font=("Segoe UI", 10, "bold"), bg=BG_COLOR)
        lbl_in.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.txt_in = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 10), width=35, height=12)
        self.txt_in.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.txt_in.bind("<KeyRelease>", lambda e: self.format_text())
        
        # Salida
        lbl_out = tk.Label(text_frame, text="Resultado SQL:", font=("Segoe UI", 10, "bold"), bg=BG_COLOR)
        lbl_out.grid(row=0, column=1, sticky="w", pady=(0, 5))
        
        self.txt_out = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10), width=35, height=12)
        self.txt_out.grid(row=1, column=1, sticky="nsew")

        text_frame.columnconfigure(0, weight=1)
        text_frame.columnconfigure(1, weight=1)
        text_frame.rowconfigure(1, weight=1)

        # Barra de Estado / Conteo
        self.lbl_stats = tk.Label(main_frame, text="Elementos procesados: 0", font=("Segoe UI", 9, "italic"), bg=BG_COLOR, fg="#555555")
        self.lbl_stats.pack(anchor="w", pady=(8, 10))

        # Botones de Acción
        btn_frame = tk.Frame(main_frame, bg=BG_COLOR)
        btn_frame.pack(fill=tk.X)

        btn_copy = tk.Button(
            btn_frame, 
            text="📋 Copiar al Portapapeles", 
            font=("Segoe UI", 10, "bold"), 
            bg=BUTTON_COLOR, 
            fg="white", 
            activebackground=PRIMARY_COLOR, 
            activeforeground="white",
            padx=15, 
            pady=6, 
            bd=0, 
            cursor="hand2",
            command=self.copy_to_clipboard
        )
        btn_copy.pack(side=tk.RIGHT, padx=(10, 0))

        btn_paste = tk.Button(
            btn_frame, 
            text="📥 Pegar desde Portapapeles", 
            font=("Segoe UI", 10), 
            bg="#6C757D", 
            fg="white", 
            activebackground="#5A6268", 
            activeforeground="white",
            padx=15, 
            pady=6, 
            bd=0, 
            cursor="hand2",
            command=self.paste_from_clipboard
        )
        btn_paste.pack(side=tk.RIGHT)

        btn_clear = tk.Button(
            btn_frame, 
            text="🗑️ Limpiar", 
            font=("Segoe UI", 10), 
            bg="#DC3545", 
            fg="white", 
            activebackground="#BD2130", 
            activeforeground="white",
            padx=15, 
            pady=6, 
            bd=0, 
            cursor="hand2",
            command=self.clear_all
        )
        btn_clear.pack(side=tk.LEFT)

        # Cargar portapapeles inicial si tiene texto
        self.root.after(100, self.auto_load_clipboard)

    def auto_load_clipboard(self):
        try:
            clip_text = self.root.clipboard_get()
            if clip_text and ("\n" in clip_text or "\r" in clip_text):
                self.txt_in.insert(tk.END, clip_text)
                self.format_text()
        except Exception:
            pass

    def paste_from_clipboard(self):
        try:
            clip_text = self.root.clipboard_get()
            self.txt_in.delete("1.0", tk.END)
            self.txt_in.insert(tk.END, clip_text)
            self.format_text()
        except Exception as e:
            messagebox.showwarning("Portapapeles", "No se encontró texto en el portapapeles.")

    def format_text(self):
        raw_text = self.txt_in.get("1.0", tk.END)
        # Extraer cada elemento sin espacios y sin líneas vacías
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        # Eliminar comillas previas si las tuviera
        clean_items = []
        for item in lines:
            # quitar comillas dobles o simples si ya existen
            cleaned = item.strip("'\"").strip(",")
            if cleaned:
                clean_items.append(cleaned)

        if not clean_items:
            self.txt_out.delete("1.0", tk.END)
            self.lbl_stats.config(text="Elementos procesados: 0")
            return

        quote = self.var_quote.get()
        parens = self.var_parens.get()

        if quote:
            formatted_elements = [f"'{item}'" for item in clean_items]
        else:
            formatted_elements = clean_items

        result = ",".join(formatted_elements)
        if parens:
            result = f"({result})"

        self.txt_out.delete("1.0", tk.END)
        self.txt_out.insert(tk.END, result)
        self.lbl_stats.config(text=f"Elementos procesados: {len(clean_items)}")

    def copy_to_clipboard(self):
        out_text = self.txt_out.get("1.0", tk.END).strip()
        if out_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(out_text)
            messagebox.showinfo("¡Copiado!", "El resultado formateado fue copiado al portapapeles.")
        else:
            messagebox.showwarning("Atención", "No hay texto formateado para copiar.")

    def clear_all(self):
        self.txt_in.delete("1.0", tk.END)
        self.txt_out.delete("1.0", tk.END)
        self.lbl_stats.config(text="Elementos procesados: 0")

def main():
    root = tk.Tk()
    app = SQLListFormatterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
