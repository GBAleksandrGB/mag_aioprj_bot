from sqlite3 import connect
from typing import Any, List, LiteralString, Optional


class DatabaseManager:
    """ 
    Менеджер базы данных.
    Инициализирует подключение к БД по заданному пути
    и опеспечивает выполнение операций с БД.
    """

    def __init__(self, path: str):
        self.conn = connect(path)
        self.conn.execute('pragma foreign_keys = on')
        self.conn.commit()
        self.cur = self.conn.cursor()

    def create_tables(self) -> None:
        self.query(
            'CREATE TABLE IF NOT EXISTS products (idx text, title text, '
            'body text, photo blob, price int, tag text)')
        self.query(
            'CREATE TABLE IF NOT EXISTS orders (cid int, usr_name text, '
            'usr_address text, products text)')
        self.query(
            'CREATE TABLE IF NOT EXISTS cart (cid int, idx text, '
            'quantity int)')
        self.query(
            'CREATE TABLE IF NOT EXISTS categories (idx text, title text)')
        self.query('CREATE TABLE IF NOT EXISTS wallet (cid int, balance real)')
        self.query(
            'CREATE TABLE IF NOT EXISTS questions (cid int, question text)')

    def query(self, arg: LiteralString, values: Optional[str] = None) -> None:
        if values is None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        self.conn.commit()

    def fetchone(self, arg: LiteralString, values: Optional[str] = None) -> Any:
        if values is None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        return self.cur.fetchone()

    def fetchall(self, arg: LiteralString, values: Optional[str] = None) -> List[Any]:
        if values is None:
            self.cur.execute(arg)
        else:
            self.cur.execute(arg, values)
        return self.cur.fetchall()

    def __del__(self) -> None:
        self.conn.close()
