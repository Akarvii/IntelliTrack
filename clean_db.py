from database import get_connection, init_db
from ledger import ensure_genesis_block
from seed_data import seed_database

init_db()
conn = get_connection()
c = conn.cursor()
c.execute('DELETE FROM users')
c.execute('DELETE FROM loans')
c.execute('DELETE FROM ledger')
c.execute('DELETE FROM items')
conn.commit()
conn.close()

seed_database()

conn = get_connection()
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM users')
u = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM loans')
l = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM ledger')
g = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM items WHERE status = 'Disponible'")
i_disp = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM items WHERE status = 'No Disponible'")
i_nodisp = c.fetchone()[0]
c.execute("SELECT code, name, stock, status FROM items")
items_list = c.fetchall()
conn.close()

print(f"CLEAN COMPLETE -> Users: {u}, Loans: {l}, Ledger: {g}, Disponibles: {i_disp}, Agotados: {i_nodisp}")
for it in items_list:
    print(f" - [{it['code']}] {it['name']} -> Stock: {it['stock']} ({it['status']})")


