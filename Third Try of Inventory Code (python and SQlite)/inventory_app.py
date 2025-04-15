# inventory_app.py
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

DB_FILE = "inventory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT UNIQUE NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS inventory (
        item_id INTEGER,
        location_id INTEGER,
        quantity INTEGER,
        PRIMARY KEY (item_id, location_id),
        FOREIGN KEY (item_id) REFERENCES items(id),
        FOREIGN KEY (location_id) REFERENCES locations(id)
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        from_location_id INTEGER,
        to_location_id INTEGER,
        quantity INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    cursor.execute("SELECT COUNT(*) FROM locations")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO locations (name) VALUES (?)", [
            ("Storage Lockers",), ("Fridge",), ("Chemical Lockers",), ("Black Office Cabinet",)
        ])
    conn.commit()
    conn.close()

class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Tracker")
        self.geometry("800x600")
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        self.create_inventory_tab()
        self.create_add_item_tab()
        self.create_move_stock_tab()

    def create_inventory_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Inventory")

        self.tree = ttk.Treeview(frame, columns=("Item ID", "Item", "Location", "Qty"), show='headings')
        for col in self.tree['columns']:
            self.tree.heading(col, text=col)
        self.tree.pack(fill='both', expand=True)

        self.tree.bind("<Double-1>", self.on_double_click_inventory)

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=5)

        refresh_btn = ttk.Button(button_frame, text="Refresh", command=self.refresh_inventory)
        refresh_btn.pack(side='left', padx=5)

        delete_btn = ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_item)
        delete_btn.pack(side='left', padx=5)

        self.refresh_inventory()

    def refresh_inventory(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT items.id AS item_id, items.name AS item_name, locations.name AS location_name, inventory.quantity
            FROM inventory
            JOIN items ON inventory.item_id = items.id
            JOIN locations ON inventory.location_id = locations.id
            WHERE inventory.quantity > 0
        ''')
        for row in cursor.fetchall():
            self.tree.insert('', 'end', values=(row["item_id"], row["item_name"], row["location_name"], row["quantity"]))
        conn.close()

    def on_double_click_inventory(self, event):
        item = self.tree.selection()[0]
        values = self.tree.item(item, 'values')
        item_id, item_name, location_name, quantity = int(values[0]), values[1], values[2], int(values[3])

        action = simpledialog.askstring("Edit Field", "Enter 'name' to edit item name or 'quantity' to edit quantity:", initialvalue="quantity")
        if not action:
            return

        if action.lower() == 'quantity':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM locations WHERE name = ?", (location_name,))
            location_id = cursor.fetchone()[0]
            conn.close()

            new_qty = simpledialog.askinteger("Edit Quantity", f"Enter new quantity for {item_name} in {location_name}", initialvalue=quantity)
            if new_qty is not None:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE inventory SET quantity = ? WHERE item_id = ? AND location_id = ?", (new_qty, item_id, location_id))
                conn.commit()
                conn.close()
                self.refresh_inventory()

        elif action.lower() == 'name':
            new_name = simpledialog.askstring("Edit Item Name", f"Enter new name for item ID {item_id}", initialvalue=item_name)
            if new_name:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, item_id))
                conn.commit()
                conn.close()
                self.refresh_inventory()

    def delete_selected_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an item to delete.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete the selected item from this location?")
        if not confirm:
            return

        values = self.tree.item(selected[0], 'values')
        item_id, location_name = int(values[0]), values[2]

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM locations WHERE name = ?", (location_name,))
        location_id = cursor.fetchone()[0]
        cursor.execute("DELETE FROM inventory WHERE item_id = ? AND location_id = ?", (item_id, location_id))
        conn.commit()
        conn.close()

        self.refresh_inventory()

    def create_add_item_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Add Item")

        ttk.Label(frame, text="Item Name").grid(row=0, column=0, sticky="e")
        name_entry = ttk.Entry(frame)
        name_entry.grid(row=0, column=1)

        ttk.Label(frame, text="SKU").grid(row=1, column=0, sticky="e")
        sku_entry = ttk.Entry(frame)
        sku_entry.grid(row=1, column=1)

        ttk.Label(frame, text="Description").grid(row=2, column=0, sticky="e")
        desc_entry = ttk.Entry(frame)
        desc_entry.grid(row=2, column=1)

        ttk.Label(frame, text="Default Location ID").grid(row=3, column=0, sticky="e")
        location_entry = ttk.Entry(frame)
        location_entry.grid(row=3, column=1)

        ttk.Label(frame, text="Initial Quantity").grid(row=4, column=0, sticky="e")
        quantity_entry = ttk.Entry(frame)
        quantity_entry.grid(row=4, column=1)
        quantity_entry.insert(0, "0")

        def add():
            name = name_entry.get()
            sku = sku_entry.get()
            desc = desc_entry.get()
            loc_id = location_entry.get()
            qty = quantity_entry.get()
            if not (name and sku and loc_id):
                messagebox.showerror("Input Error", "Name, SKU, and Location ID are required")
                return
            try:
                qty = int(qty) if qty else 0
                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO items (name, sku, description) VALUES (?, ?, ?)", (name, sku, desc))
                    item_id = cursor.lastrowid
                    cursor.execute("INSERT INTO inventory (item_id, location_id, quantity) VALUES (?, ?, ?) ON CONFLICT(item_id, location_id) DO UPDATE SET quantity = quantity + ?", (item_id, int(loc_id), qty, qty))
                    conn.commit()
                messagebox.showinfo("Success", "Item added")
                self.refresh_inventory()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(frame, text="Add Item", command=add).grid(row=5, column=0, columnspan=2, pady=10)

    def create_move_stock_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Move Stock")

        entries = {}
        for idx, label in enumerate(["Item ID", "From Location ID", "To Location ID", "Quantity"]):
            ttk.Label(frame, text=label).grid(row=idx, column=0)
            entry = ttk.Entry(frame)
            entry.grid(row=idx, column=1)
            entries[label] = entry

        def move():
            try:
                item_id = int(entries["Item ID"].get())
                from_id = int(entries["From Location ID"].get())
                to_id = int(entries["To Location ID"].get())
                qty = int(entries["Quantity"].get())
            except ValueError:
                messagebox.showerror("Input Error", "All fields must be numbers")
                return
            try:
                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT quantity FROM inventory WHERE item_id = ? AND location_id = ?", (item_id, from_id))
                    result = cursor.fetchone()
                    if not result or result[0] < qty:
                        messagebox.showerror("Error", "Insufficient stock")
                        return
                    cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_id = ? AND location_id = ?", (qty, item_id, from_id))
                    cursor.execute("INSERT INTO inventory (item_id, location_id, quantity) VALUES (?, ?, ?) ON CONFLICT(item_id, location_id) DO UPDATE SET quantity = quantity + ?", (item_id, to_id, qty, qty))
                    cursor.execute("DELETE FROM inventory WHERE item_id = ? AND location_id = ? AND quantity <= 0", (item_id, from_id))
                    cursor.execute("INSERT INTO transactions (item_id, from_location_id, to_location_id, quantity) VALUES (?, ?, ?, ?)", (item_id, from_id, to_id, qty))
                    conn.commit()
                messagebox.showinfo("Success", "Stock moved")
                self.refresh_inventory()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(frame, text="Transfer", command=move).grid(row=4, column=0, columnspan=2, pady=10)

if __name__ == '__main__':
    init_db()
    app = InventoryApp()
    app.mainloop()
    