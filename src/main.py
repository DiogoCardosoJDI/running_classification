import os
import tkinter as tk
from register_running import CronometroApp

if __name__ == "__main__":
    if not os.path.exists("data_charge"):
        try:
            os.makedirs("data_charge")
        except: pass
        
    arquivo_bd = "prova_data.db"
    if os.path.exists(arquivo_bd):
        try:
            os.remove(arquivo_bd)
            print(f"Base de dados anterior '{arquivo_bd}' excluída com sucesso.")
        except PermissionError:
            print(f"AVISO: Não foi possível excluir '{arquivo_bd}'. Ele pode estar aberto.")

    root = tk.Tk()
    app = CronometroApp(root)
    root.mainloop()