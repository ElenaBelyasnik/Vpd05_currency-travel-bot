import sqlite3
import logging
from typing import Optional, List, Tuple, Any, Dict
from contextlib import contextmanager
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Database:
    """
    Класс для работы с базой данных SQLite3.

    Предоставляет методы для подключения, выполнения запросов,
    чтения, вставки, обновления и удаления данных с использованием
    контекстных менеджеров для безопасной работы с соединениями.
    """

    def __init__(self, db_path: str):
        """
        Инициализация подключения к базе данных.

        Args:
            db_path: Путь к файлу базы данных SQLite.
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        logger.info(f"Инициализация подключения к БД: {db_path}")

    def connect(self) -> None:
        """
        Установить соединение с базой данных.

        Создает постоянное соединение, которое можно использовать
        для выполнения запросов. Рекомендуется использовать
        контекстный менеджер connect() для автоматического управления.
        """
        try:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            logger.info("Соединение с БД установлено")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при подключении к БД: {e}")
            raise

    def disconnect(self) -> None:
        """
        Закрыть соединение с базой данных.

        Безопасно закрывает активное соединение, если оно существует.
        """
        if self._connection:
            try:
                self._connection.close()
                logger.info("Соединение с БД закрыто")
            except sqlite3.Error as e:
                logger.error(f"Ошибка при закрытии соединения: {e}")
            finally:
                self._connection = None

    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для получения соединения с БД.

        Автоматически открывает и закрывает соединение.

        Yields:
            sqlite3.Connection: Объект соединения с базой данных.

        Example:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            logger.debug("Получено временное соединение с БД")
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении соединения: {e}")
            raise
        finally:
            if conn:
                conn.close()
                logger.debug("Временное соединение закрыто")

    @contextmanager
    def get_cursor(self, commit: bool = False):
        """
        Контекстный менеджер для получения курсора с опциональной коммитом.

        Автоматически управляет соединением, курсором и транзакциями.

        Args:
            commit: Если True, автоматически подтверждает изменения.

        Yields:
            sqlite3.Cursor: Объект курсора для выполнения запросов.

        Example:
            with db.get_cursor(commit=True) as cursor:
                cursor.execute("INSERT INTO users VALUES (?, ?)", (1, "Alice"))
        """
        conn = None
        cursor = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            logger.debug("Курсор получен")
            yield cursor
            if commit:
                conn.commit()
                logger.debug("Транзакция подтверждена")
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
                logger.warning("Транзакция откатлена из-за ошибки")
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Ресурсы освобождены")

    # ==================== ЧТЕНИЕ ДАННЫХ ====================

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Выполнить SELECT запрос и вернуть одну запись.

        Args:
            query: SQL запрос SELECT.
            params: Параметры для подстановки в запрос (tuple).

        Returns:
            Словарь с данными первой найденной записи или None, если запись не найдена.

        Example:
            user = db.fetch_one("SELECT * FROM users WHERE id = ?", (1,))
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    logger.debug(f"Запись получена: {result.get('id', 'N/A')}")
                    return result
                logger.debug("Запись не найдена")
                return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка при чтении одной записи: {e}")
            raise

    def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """
        Выполнить SELECT запрос и вернуть все найденные записи.

        Args:
            query: SQL запрос SELECT.
            params: Параметры для подстановки в запрос (tuple).

        Returns:
            Список словарей с данными записей.

        Example:
            users = db.fetch_all("SELECT * FROM users WHERE age > ?", (18,))
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
                logger.info(f"Получено {len(result)} записей")
                return result
        except sqlite3.Error as e:
            logger.error(f"Ошибка при чтении записей: {e}")
            raise

    def fetch_many(self, query: str, params: Tuple = (), size: int = 100) -> List[Dict[str, Any]]:
        """
        Выполнить SELECT запрос и вернуть ограниченное количество записей.

        Args:
            query: SQL запрос SELECT.
            params: Параметры для подстановки в запрос (tuple).
            size: Максимальное количество записей для возврата.

        Returns:
            Список словарей с данными записей (не более size).

        Example:
            users = db.fetch_many("SELECT * FROM users", (), 50)
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchmany(size)
                result = [dict(row) for row in rows]
                logger.debug(f"Получено {len(result)} записей (макс: {size})")
                return result
        except sqlite3.Error as e:
            logger.error(f"Ошибка при чтении ограниченного набора: {e}")
            raise

    def get_count(self, query: str, params: Tuple = ()) -> int:
        """
        Получить количество записей по запросу.

        Args:
            query: SQL запрос COUNT (должен возвращать одно число).
            params: Параметры для подстановки в запрос (tuple).

        Returns:
            Количество записей.

        Example:
            count = db.get_count("SELECT COUNT(*) FROM users WHERE active = ?", (1,))
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()[0]
                logger.debug(f"Количество записей: {result}")
                return result
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении количества записей: {e}")
            raise

    # ==================== ВСТАВКА ДАННЫХ ====================

    def insert_one(self, table: str, data: Dict[str, Any]) -> int:
        """
        Вставить одну запись в таблицу.

        Args:
            table: Имя таблицы.
            data: Словарь с данными для вставки (ключ = колонка, значение = значение).

        Returns:
            ID вставленной записи (lastrowid).

        Example:
            user_id = db.insert_one("users", {"name": "Alice", "age": 30})
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        params = tuple(data.values())

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.execute(query, params)
                row_id = cursor.lastrowid
                logger.info(f"Запись вставлена в таблицу {table}, ID: {row_id}")
                return row_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка при вставке записей в {table}: {e}")
            raise

    def insert_many(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """
        Вставить множество записей в таблицу одной транзакцией.

        Args:
            table: Имя таблицы.
            data_list: Список словарей с данными для вставки.

        Returns:
            Количество вставленных записей.

        Example:
            count = db.insert_many("users", [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ])
        """
        if not data_list:
            logger.warning("Пустой список данных для вставки")
            return 0

        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['?' for _ in data_list[0]])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        params_list = [tuple(data.values()) for data in data_list]

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.executemany(query, params_list)
                count = cursor.rowcount
                logger.info(f"Вставлено {count} записей в таблицу {table}")
                return count
        except sqlite3.Error as e:
            logger.error(f"Ошибка при массовой вставке в {table}: {e}")
            raise

    # ==================== ОБНОВЛЕНИЕ ДАННЫХ ====================

    def update_one(
        self,
        table: str,
        data: Dict[str, Any],
        where_clause: str,
        where_params: Tuple = ()
    ) -> int:
        """
        Обновить одну или несколько записей по условию.

        Args:
            table: Имя таблицы.
            data: Словарь с новыми данными (ключ = колонка, значение = новое значение).
            where_clause: Условие WHERE (без ключевого слова WHERE).
            where_params: Параметры для условия WHERE.

        Returns:
            Количество обновленных записей.

        Example:
            count = db.update_one("users", {"age": 31}, "id = ?", (1,))
        """
        set_clause = ', '.join([f"{col} = ?" for col in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = tuple(data.values()) + where_params

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.execute(query, params)
                count = cursor.rowcount
                logger.info(f"Обновлено {count} записей в таблице {table}")
                return count
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении записей в {table}: {e}")
            raise

    def update_many(
        self,
        table: str,
        data_list: List[Dict[str, Any]],
        where_clause: str,
        where_params: Tuple = ()
    ) -> int:
        """
        Обновить множество записей с разными данными по условию.

        Args:
            table: Имя таблицы.
            data_list: Список словарей с данными для обновления.
            where_clause: Условие WHERE (без ключевого слова WHERE).
            where_params: Параметры для условия WHERE.

        Returns:
            Количество обновленных записей.

        Example:
            count = db.update_many("users", [
                {"age": 31},
                {"age": 26}
            ], "id IN (?, ?)", (1, 2))
        """
        if not data_list:
            logger.warning("Пустой список данных для обновления")
            return 0

        columns = list(data_list[0].keys())
        set_clause = ', '.join([f"{col} = ?" for col in columns])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        # Добавляем where_params к каждому набору данных
        params_list = [tuple(data.values()) + where_params for data in data_list]

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.executemany(query, params_list)
                count = cursor.rowcount
                logger.info(f"Обновлено {count} записей в таблице {table}")
                return count
        except sqlite3.Error as e:
            logger.error(f"Ошибка при массовом обновлении в {table}: {e}")
            raise

    # ==================== УДАЛЕНИЕ ДАННЫХ ====================

    def delete_one(
        self,
        table: str,
        where_clause: str,
        where_params: Tuple = ()
    ) -> int:
        """
        Удалить одну запись по условию.

        Args:
            table: Имя таблицы.
            where_clause: Условие WHERE (без ключевого слова WHERE).
            where_params: Параметры для условия WHERE.

        Returns:
            Количество удаленных записей (0 или 1).

        Example:
            count = db.delete_one("users", "id = ?", (1,))
        """
        query = f"DELETE FROM {table} WHERE {where_clause}"

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.execute(query, where_params)
                count = cursor.rowcount
                logger.info(f"Удалено {count} записей из таблицы {table}")
                return count
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении записей из {table}: {e}")
            raise

    def delete_many(
        self,
        table: str,
        where_clause: str,
        where_params: Tuple = ()
    ) -> int:
        """
        Удалить множество записей по условию.

        Args:
            table: Имя таблицы.
            where_clause: Условие WHERE (без ключевого слова WHERE).
            where_params: Параметры для условия WHERE.

        Returns:
            Количество удаленных записей.

        Example:
            count = db.delete_many("users", "age < ?", (18,))
        """
        query = f"DELETE FROM {table} WHERE {where_clause}"

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.execute(query, where_params)
                count = cursor.rowcount
                logger.info(f"Удалено {count} записей из таблицы {table}")
                return count
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении записей из {table}: {e}")
            raise

    def delete_all(self, table: str) -> int:
        """
        Удалить все записи из таблицы.

        Внимание! Это действие необратимо.

        Args:
            table: Имя таблицы.

        Returns:
            Количество удаленных записей.

        Example:
            count = db.delete_all("logs")
        """
        query = f"DELETE FROM {table}"

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.execute(query)
                count = cursor.rowcount
                logger.warning(f"Удалено {count} записей из таблицы {table} (DELETE ALL)")
                return count
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении всех записей из {table}: {e}")
            raise

    # ==================== РАБОТА С СХЕМОЙ БД ====================

    def execute(self, query: str, params: Tuple = (), commit: bool = False) -> int:
        """
        Выполнить произвольный SQL запрос.

        Универсальный метод для выполнения любых SQL команд.

        Args:
            query: SQL запрос.
            params: Параметры для подстановки в запрос (tuple).
            commit: Если True, автоматически подтверждает изменения.

        Returns:
            Количество затронутых записей.

        Example:
            rows_affected = db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        """
        try:
            with self.get_cursor(commit=commit) as cursor:
                cursor.execute(query, params)
                count = cursor.rowcount
                logger.debug(f"Запрос выполнен, затронуто записей: {count}")
                return count
        except sqlite3.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise

    def executemany(self, query: str, params_list: List[Tuple], commit: bool = False) -> int:
        """
        Выполнить произвольный SQL запрос с множеством параметров.

        Args:
            query: SQL запрос.
            params_list: Список кортежей с параметрами.
            commit: Если True, автоматически подтверждает изменения.

        Returns:
            Количество затронутых записей.

        Example:
            rows_affected = db.executemany(
                "INSERT INTO users (name, age) VALUES (?, ?)",
                [("Alice", 30), ("Bob", 25)]
            )
        """
        try:
            with self.get_cursor(commit=commit) as cursor:
                cursor.executemany(query, params_list)
                count = cursor.rowcount
                logger.debug(f"Массовый запрос выполнен, затронуто записей: {count}")
                return count
        except sqlite3.Error as e:
            logger.error(f"Ошибка при выполнении массового запроса: {e}")
            raise

    def create_table(self, table_name: str, columns: str) -> None:
        """
        Создать таблицу с указанными колонками.

        Args:
            table_name: Имя таблицы.
            columns: Определение колонок в формате SQL.

        Example:
            db.create_table("users", "id INTEGER PRIMARY KEY, name TEXT NOT NULL")
        """
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.execute(query)
                logger.info(f"Создана таблица: {table_name}")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании таблицы {table_name}: {e}")
            raise

    def drop_table(self, table_name: str) -> None:
        """
        Удалить таблицу из базы данных.

        Внимание! Это действие необратимо.

        Args:
            table_name: Имя таблицы.

        Example:
            db.drop_table("users")
        """
        query = f"DROP TABLE IF EXISTS {table_name}"

        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.execute(query)
                logger.warning(f"Таблица удалена: {table_name}")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении таблицы {table_name}: {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """
        Проверить существование таблицы в базе данных.

        Args:
            table_name: Имя таблицы.

        Returns:
            True если таблица существует, False иначе.

        Example:
            if db.table_exists("users"):
                print("Таблица существует")
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (table_name,))
                result = cursor.fetchone()
                exists = result is not None
                logger.debug(f"Проверка таблицы {table_name}: {exists}")
                return exists
        except sqlite3.Error as e:
            logger.error(f"Ошибка при проверке существования таблицы {table_name}: {e}")
            raise

    def get_tables(self) -> List[str]:
        """
        Получить список всех таблиц в базе данных.

        Returns:
            Список имен таблиц.

        Example:
            tables = db.get_tables()
            for table in tables:
                print(table)
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query)
                tables = [row[0] for row in cursor.fetchall()]
                logger.info(f"Найдено таблиц: {len(tables)}")
                return tables
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении списка таблиц: {e}")
            raise

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Получить информацию о структуре таблицы.

        Args:
            table_name: Имя таблицы.

        Returns:
            Список словарей с информацией о колонках (id, name, type, notnull, dflt_value, pk).

        Example:
            info = db.get_table_info("users")
            for col in info:
                print(col['name'], col['type'])
        """
        query = f"PRAGMA table_info({table_name})"

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                info = [
                    {
                        'id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'notnull': row[3],
                        'default_value': row[4],
                        'primary_key': row[5]
                    }
                    for row in rows
                ]
                logger.debug(f"Получена информация о {len(info)} колонках таблицы {table_name}")
                return info
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении информации о таблице {table_name}: {e}")
            raise

    # ==================== ТРАНЗАКЦИИ ====================

    def begin_transaction(self) -> None:
        """
        Начать транзакцию.

        Явно начинает транзакцию. Необходимо завершить commit() или rollback().

        Warning:
            При использовании этого метода необходимо вручную управлять
            завершением транзакции. Рекомендуется использовать get_cursor(commit=True)
            вместо этого метода.
        """
        if self._connection:
            try:
                self._connection.execute("BEGIN")
                logger.info("Транзакция начата")
            except sqlite3.Error as e:
                logger.error(f"Ошибка при начале транзакции: {e}")
                raise

    def commit(self) -> None:
        """
        Подтвердить текущую транзакцию.

        Сохраняет все изменения, сделанные в текущей транзакции.
        """
        if self._connection:
            try:
                self._connection.commit()
                logger.info("Транзакция подтверждена")
            except sqlite3.Error as e:
                logger.error(f"Ошибка при подтверждении транзакции: {e}")
                raise

    def rollback(self) -> None:
        """
        Откатить текущую транзакцию.

        Отменяет все изменения, сделанные в текущей транзакции.
        """
        if self._connection:
            try:
                self._connection.rollback()
                logger.warning("Транзакция откатлена")
            except sqlite3.Error as e:
                logger.error(f"Ошибка при откате транзакции: {e}")
                raise

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def get_last_insert_id(self) -> int:
        """
        Получить ID последней вставленной записи.

        Returns:
            ID последней вставленной записи.

        Example:
            last_id = db.get_last_insert_id()
        """
        if self._connection:
            return self._connection.lastrowid
        return 0

    def vacuum(self) -> None:
        """
        Оптимизировать базу данных.

        Сжимает файл базы данных и устраняет фрагментацию.
        Выполняется команда VACUUM.
        """
        try:
            with self.get_cursor(commit=True) as cursor:
                cursor.execute("VACUUM")
                logger.info("База данных оптимизирована (VACUUM)")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при оптимизации БД: {e}")
            raise

    def integrity_check(self) -> bool:
        """
        Проверить целостность базы данных.

        Returns:
            True если целостность не нарушена, False иначе.

        Example:
            if db.integrity_check():
                print("БД в порядке")
        """
        query = "PRAGMA integrity_check"

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()[0]
                is_ok = result == "ok"
                logger.info(f"Проверка целостности: {'OK' if is_ok else result}")
                return is_ok
        except sqlite3.Error as e:
            logger.error(f"Ошибка при проверке целостности БД: {e}")
            raise

    def __enter__(self) -> 'Database':
        """
        Метод контекстного менеджера для входа.

        Возвращает объект Database.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Метод контекстного менеджера для выхода.

        Закрывает соединение независимо от возникновения исключения.
        """
        self.disconnect()
        if exc_type is not None:
            logger.warning("Контекст завершен с исключением")

    def __del__(self) -> None:
        """
        Деструктор класса.

        Гарантирует закрытие соединения при удалении объекта.
        """
        if self._connection:
            self.disconnect()