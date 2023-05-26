import sqlite3

#функция чтения json файла в бинарном виде
def read_file(filename:str) -> bytes|bool:
    try:
        # Открываем файл для чтения
        file = open(filename, 'rb')
        data_file = file.read()
        return data_file
    except Exception as e:
        print(e)
        return False
     
class BotUsers():

    def __init__(self, db_name):
        self.db_name = db_name
    
    #создание таблицы
    def create_table_botusers(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_name)
            curs = conn.cursor()
            """
                telegram_id - id пользователя по сути (почему строка? вдруг в будущем id у телеги будет хешем)00 )
                refer - количество приглашенных пользователей
                message_history_context - храним историю контекста сообщений (можно сбрасывать)
                data_file - полная информация о usere, когда он подключается к чату в объекте message все это есть (на всякий случай храним всю инфу о пользователей в виде файла)
                refers_id - кто пригласил пользователя
            """
            curs.execute("""CREATE TABLE botusers (
                telegram_id VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                refer INTEGER DEFAULT 0,
                message_history_context BLOB,
                is_premium BOOLEAN DEFAULT 0,
                token INTEGER,
                refers_id VARCHAR(255),
                request INTEGER DEFAULT 0,
                date_reg VARCHAR(255), 
                data_file BLOB)""")
            conn.close()
            return True
        except Exception as e:
            print(e)
            return False
        
    # Добавляем пользователя в базу данных в таблицу botusers
    def add_user(self, telegram_id:str, name:str, refer: int, message_history_context: bytes,  is_premium: bool, token: int, refers_id: str, date_reg: str, data_file: bytes) -> bool:
        try:
            conn = sqlite3.connect(self.db_name)
            curs = conn.cursor()
            curs.execute("INSERT INTO botusers (telegram_id, name, refer, message_history_context, is_premium, token, refers_id, date_reg, data_file) VALUES (?,?,?,?,?,?,?,?,?)", (telegram_id,name, refer, message_history_context,  is_premium, token, refers_id, date_reg, data_file))
            # Сохраняем изменения
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(e)
            return False
    
    #Получаем пользователя по id
    def get_user_by_id(self, user_id:str) -> tuple | bool:
        try:
            conn = sqlite3.connect(self.db_name)
            curs = conn.cursor()
            curs.execute("SELECT * FROM botusers WHERE telegram_id=?", [user_id])
            data = curs.fetchall()
            conn.close()
            return data
        except Exception as e:
            print(e)
            return False
    """
    Обновляем данные пользователя по id
    Можно указать какие столбцы обновить передав их в виде ключ(название столбца)=значение
    """
    def update_user_by_id(self, user_id:str, **kwargs) -> True:
        try:
            conn = sqlite3.connect(self.db_name)
            curs = conn.cursor()
            script_text = "UPDATE botusers SET "
            param_text = ""
            placeholder = []
            for key, value in kwargs.items():
                placeholder.append(value)
                param_text += key.lower()+'=?, '
            if len(param_text) > 0 and len(placeholder) > 0:
                param_text = param_text[0:-2] #вырезаем последний пробел и запятую
                script_text = script_text + param_text + " WHERE telegram_id=?"
                placeholder.append(user_id)
                curs.execute(script_text, placeholder)
                conn.commit()
                conn.close()
                return True
            conn.close()
            return False
        except Exception as e:
            print(e)
            return False

    """
    Получение всех пользователей 
    Мы можем передать через запятую строки - названия столбцов, которые хотим отобразить
    """
    def get_all_users(self, *args) -> tuple | bool:
        try:
            conn = sqlite3.connect(self.db_name)
            curs = conn.cursor()
            param_text = ''
            for key in args:
                param_text += key + ',' + " " 
            if len(param_text) > 0:
                param_text = param_text[0:-2] #избавляемся от последней запятой
            curs.execute(f"SELECT {param_text if len(param_text) > 0 else '*'} FROM botusers")
            data = curs.fetchall()
            conn.close()
            return data
        
        except Exception as e:
            print(e)
            return False


