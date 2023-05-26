import random
import telebot
from telebot import types
from telebot import util #разбиение текста при слишком длинных запросах
import requests
import json
from dotenv import load_dotenv
from data import *
import os
from datetime import date
import jsonpickle
from text import *
from stickers.sticker import *
from open_ai_mod.turbo3_5 import *
from open_ai_mod.davinci import *
from open_ai_mod.aduio_translate import *
from pydub import AudioSegment #для преобразования из ogg в mp3



load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
VAL_PRICE_URL_ = os.getenv('VAL_PRICE_URL_')
CHANNEL_ID = os.getenv('CHANNEL_ID')

#бд

botUsers = BotUsers('my_database.db')

#создаем объект приложения бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

#функция создания пользователя
def create_user(user_id, message, referrer_candidate, message_history_context=[], refer=0) -> bool:
    try:
        #формируем файл под пользователя и создаем папку
        if not os.path.exists('users'):
            os.mkdir("users")
        filename = str(user_id) + '.json'
        json_object = json.loads(jsonpickle.encode(message))
        with open("users/" + filename, 'w') as f:
            json.dump(json_object, f)
        data_file = read_file("users/" + filename) #считываем файл пользователя для бд

        if len(message_history_context) == 0: #пустой ли контекст пользователя
            message_history_context_file = read_file('first_context.json')
        botUsers.add_user(str(user_id), message.from_user.username, refer, message_history_context_file, False, 1000, str(referrer_candidate), str(date.today()), data_file)
        return True
    except Exception as e:
        error_log('error.txt', e, id)
        return False

#функция создающая json файл с контекстом юзера
def create_user_context_file(user_id: str, dictionary: dict) -> bool:
    if not os.path.exists('users_context'):
        os.mkdir("users_context")
    with open(f'users_context/{user_id}.json', 'w') as f:
        json.dump(dictionary, f)
        return True
    return False

#если не подписан - лови запись подписки)
def not_in_sub_channel(user_id):
    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="Я подписался (-ась)!", callback_data="check_sub")
    keyboard.add(callback_button)
    bot.send_message(user_id, warning_message, reply_markup=keyboard)

#отправка уведомления с кнопкой о переполненности контекста
def clear_context_message(user_id):
    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="Отчистить", callback_data="clear")
    keyboard.add(callback_button)
    bot.send_message(user_id, "Необходимо почистить контекст", reply_markup=keyboard)

#проверка подписки пользователя на основной канал
def check_sub(user_id:str) -> bool:
    try:
        data = bot.get_chat_member(CHANNEL_ID, str(user_id))
        
        if str(data.status) != 'left':
            return True
        else:
            return False
    except:
        return False

#кейбоард при нажатии на кнопку "Скажи привет нейронной сети"
def say_hello_neuro(user_id) -> None:
    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="Скажи привет нейронной сети 👋", callback_data="call_neuro")
    keyboard.add(callback_button)
    bot.send_message(user_id, hello_message, reply_markup=keyboard, parse_mode="HTML") 

#запись ошибок в файл
def error_log(filename, e, id=None):
    with open(filename, 'a') as f:
        f.read(str(date.today()) + '/' + str(id) + '/' + str(e) + '\n')

#функция очищения контекста
def clear_context(user_id:str) -> bool:
    try:
        message_history_context_file = read_file('first_context.json')
        botUsers.update_user_by_id(user_id, message_history_context=message_history_context_file)
        return True
    except Exception as e:
        return False
    
#функция создания контекста для данных из бд (тут я делаю парсинг json и беру именно нужный элемент списков данных из бд)
def create_context_user(data:list, message:str, role='user') -> dict:
    #получаем текущий контекст пользователя
    dict = json.loads(data[0][3])
    new_data = {
        'role': role,
        'content': message
    }
    dict['context'].append(new_data)
    return dict

#функция создания контекста для данных из бд (тут я делаю парсинг json и беру именно 0 и 3 элемент списков данных из бд)
def create_context_assistant(data:list, message:str, role='assistant') -> dict:
    #получаем текущий контекст пользователя
    dict = data
    new_data = {
        'role': role,
        'content': message
    }
    dict['context'].append(new_data)
    return dict

#получения списка данных из словаря контекста 
def get_context_from(data:dict) -> list:
    if isinstance(data, dict):
        return data['context']
    else:
        return []

#создание глобальной раскладки клавиатуры со всеми кнопками
def create_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('⚛️ Информация')
    button2 = types.KeyboardButton('🚸 Профиль')
    button3 = types.KeyboardButton('↗️ Пригласить')
    button4 = types.KeyboardButton('👑 Премиум подписка')
    button5 = types.KeyboardButton('🧠 Нейронки на все случаи жизни')
    button6 = types.KeyboardButton('Сбросить память')
    markup.add(button1, button2, button6)
    markup.add(button3, button4)
    markup.add(button5)
    return markup
global_markup = create_markup()

#словарь состояний сообщений пользователей
"""
Логика работы словаря проста. Если пользователь отправил запрос нейросети один раз, фиксируем это, пока не получим либо ошибку, либо ответ. Анти-спам
"""
global_state_message = {
    'user_id':{
        'mode': 'turbo', #mode davinci
        'type_request1':{
            "message":True
        }, 
        'type_request2':{
            "message": True
        }

    }
}
   
#обработчик сообщений
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id #int
    print('Зашел пользователь', user_id, type(user_id))
    if not botUsers.get_user_by_id(str(user_id)):
        referrer = None #рефер
        # Проверяем наличие хоть какой-то дополнительной информации из ссылки (в нашем случае пробел)
        if " " in message.text:
            referrer_candidate = message.text.split()[1] #id кто потенциально привел человека в бот
            # Пробуем преобразовать строку в число
            try:
                referrer_candidate = int(referrer_candidate)
                # Проверяем на несоответствие TG ID пользователя TG ID рефера
                # Также проверяем, есть ли такой реферер в базе данных
                if user_id != referrer_candidate and botUsers.get_user_by_id(str(referrer_candidate)) and check_sub(str(referrer_candidate)):
                    try:
                        create_user(user_id, message, referrer_candidate) 
                        try:
                            refer_data = botUsers.get_user_by_id(str(referrer_candidate))
                            refer_data_refer = refer_data[0][2] + 1 #кол-во приглашенных челов увеличилось на 1
                            refer_data_tokens = refer_data[0][5] + 50 #рефер получается 50 токенов за приведенного чела
                            botUsers.update_user_by_id(str(referrer_candidate), refer=refer_data_refer, token=refer_data_tokens) #обновляем у рефа два поля, кол-во приглашений и токены
                        except:
                            error_log('error.txt', e, id=user_id)
                        if not check_sub(str(user_id)): #
                            not_in_sub_channel(user_id)#если он не подписчик канала, отправляем сообщение о необходимости стать подписчиком
                        else:
                            say_hello_neuro(user_id) 
                    except Exception as e:
                        create_user(user_id, message, referrer_candidate='') 
                        not_in_sub_channel(user_id)
                else:
                    create_user(user_id, message, referrer_candidate='') 
                    if not check_sub(str(user_id)):
                        not_in_sub_channel(user_id)
                    else:
                        say_hello_neuro(user_id) 
            except Exception as e:
                print('Ссылка некорректная')
                error_log('error.txt', e, id=user_id)
                create_user(user_id, message, referrer_candidate='')
                if not check_sub(str(user_id)):
                    not_in_sub_channel(user_id)
                else:
                    say_hello_neuro(user_id) 
        else:
            create_user(user_id, message, referrer_candidate='') 
            if not check_sub(str(user_id)):
                not_in_sub_channel(user_id)
            else:
                say_hello_neuro(user_id)   
    else: #если такой пользователь уже есть в бд
        if check_sub(str(user_id)):
            say_hello_neuro(user_id) 
        else:
            not_in_sub_channel(user_id)

#callbacks
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        if call.data == "check_sub":
            if check_sub(str(call.message.chat.id)):
                try:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="<b>🚀🚀🚀 Проверка пройдена успешно! Вы подписались на канал. Можете пользоваться ботом</b>", parse_mode="HTML")
                    keyboard = types.InlineKeyboardMarkup()
                    callback_button = types.InlineKeyboardButton(text="Скажи привет нейронной сети 👋", callback_data="call_neiro")
                    keyboard.add(callback_button)
                    bot.send_message(call.message.chat.id, hello_message, reply_markup=keyboard, parse_mode="HTML")
                except Exception as e:
                    with open('error.txt', 'a') as f:
                        f.write(str(date.today()) + '/' + str(call.message.chat.id) + '/' + str(e) + '\n')
            else:
                try:
                    bot.send_message(call.message.chat.id, "<b>❗ К сожалению подписка пока еще не принята. Ожидайте</b>", parse_mode="HTML")
                    not_in_sub_channel(str(call.message.chat.id))
                except Exception as e:
                    with open('error.txt', 'a') as f:
                        f.write(str(date.today()) + '/' + str(call.message.chat.id) + '/' + str(e) + '\n')
        if call.data == "call_neuro":
                try:
                    data = hello_neuro_message
                    data = "Ответ от 🧿 АI 👇\n" + data
                    #bot.send_message(call.message.chat.id, "Ответ от 🧿 АI 👇",  reply_markup=global_markup)
                    message = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=data)
                except Exception as e:
                    with open('error.txt', 'a') as f:
                        f.write(str(date.today()) + '/' + str(call.message.chat.id) + '/' + str(e) + '\n')
        if call.data == "clear":
            if clear_context(str(call.message.chat.id)):
                bot.send_message(call.message.chat.id, "🧹 Память очищена, можешь дальше пользоваться сетью")
            else:
                bot.send_message(call.message.chat.id, "Ошибка очищения контекста, попробуй позже 👇🏻")
    
#Рассылки пользователям
@bot.message_handler(commands=["rassylka"])
def message(message):
    user_id = message.from_user.id
    if str(user_id) == "711246255": 
        """
            Позиция символа вопроса в строке запроса. После вопроса идет код действия
            1 - реклама с фото и кнопкой
            2 - реклама с фото без кнопкой
            3 - реклама без фото с кнопкой
            4 - Реклама без фото и кнопки
            5 - Новости канала с фото и кнопкой
            6 - Новости канала с фото без кнопки
            7 - Новости канала без фото с кнопкой
            8 - Новости канала без фото и без кнопки

            9 - реклама с видео и кнопкой
            10 - реклама с видео без кнопки
            11 - новости видео и кнопка
            12 - новости без видео и без кнопки

            Как выглядит запрос: /rassylka ?code=4&url=google.com&btn=Перейти
        """
        pos = message.text.find("?") 
        request = message.text[pos+1: ] #получаем запрос
        req_data = request.split("&")
        dict_req = {}
        for req in req_data:
            a = req.split('=')
            dict_req[a[0]]=a[1]
        
        #готовим файлы для рассылки рекламы
        extensions_allowed = ['.png', '.jpg']
        pictures_adverts = os.listdir('./mailing/advertisement') 
        files_adverts = []
        #готовим файлы для новостей
        pictures_news = os.listdir('./mailing/news') 
        files_news= []
        for extension in extensions_allowed:
            for picture in pictures_adverts:
                if picture.endswith(extension):
                    files_adverts.append(picture)
            for news in pictures_news:
                if news.endswith(extension):
                    files_news.append(news)

        all_users_tuple = botUsers.get_all_users("telegram_id")
        all_users_list = []
        for data in all_users_tuple:
            all_users_list.append(int(data[0]))

        #если в параметрах запроса были переданы url 
        if 'url' in dict_req:
            keyboard = types.InlineKeyboardMarkup()
            callback_button = types.InlineKeyboardButton(text=f"{dict_req['btn']} ↗", url=f"{dict_req['url']}")
            keyboard.add(callback_button)
        if dict_req['code'] == '1':
            with open("./mailing/advertisement/advertisement.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                if len(files_adverts) > 0:
                    photo = open(f'./mailing/advertisement/{files_adverts[0]}', 'rb')
                    for user_id in all_users_list:
                        bot.send_photo(user_id, photo, caption=text, parse_mode="HTML", reply_markup=keyboard)
                else:
                    for user_id in all_users_list:
                        bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)
        elif dict_req['code'] == '2':
            with open("./mailing/advertisement/advertisement.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                if len(files_adverts) > 0:
                    photo = open(f'./mailing/advertisement/{files_adverts[0]}', 'rb')
                    for user_id in all_users_list:
                        bot.send_photo(user_id, photo, caption=text, parse_mode="HTML")
                else:
                    for user_id in all_users_list:
                        bot.send_message(user_id, text, parse_mode="HTML")
        elif dict_req['code'] == '3':
            with open("./mailing/advertisement/advertisement.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                for user_id in all_users_list:
                    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)
        elif dict_req['code'] == '4':
            with open("./mailing/advertisement/advertisement.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                for user_id in all_users_list:
                    bot.send_message(user_id, text, parse_mode="HTML")
        if dict_req['code'] == '5':
            with open("./mailing/news/news.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                if len(files_news) > 0:
                    photo = open(f'./mailing/news/{files_news[0]}', 'rb')
                    for user_id in all_users_list:
                        bot.send_photo(user_id, photo, caption=text, parse_mode="HTML", reply_markup=keyboard)
                else:
                    for user_id in all_users_list:
                        bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)
        elif dict_req['code'] == '6':
            with open("./mailing/news/news.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                if len(files_news) > 0:
                    photo = open(f'./mailing/news/{files_news[0]}', 'rb')
                    for user_id in all_users_list:
                        bot.send_photo(user_id, photo, caption=text, parse_mode="HTML")
                else:   
                    for user_id in all_users_list:
                        bot.send_message(user_id, text, parse_mode="HTML")
        elif dict_req['code'] == '7':
            with open("./mailing/news/news.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                for user_id in all_users_list:
                    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)
        elif dict_req['code'] == '8':
            with open("./mailing/news/news.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                for user_id in all_users_list:
                    bot.send_message(user_id, text, parse_mode="HTML")
        elif dict_req['code'] == '9':
            with open("./mailing/advertisement/advertisement.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                bot.send_video(user_id, open('./mailing/advertisement/videos/1.mp4', 'rb'), caption=text, parse_mode="HTML", reply_markup=keyboard)
        elif dict_req['code'] == '10':
            with open("./mailing/advertisement/advertisement.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                bot.send_video(user_id, open('./mailing/advertisement/videos/1.mp4', 'rb'), caption=text, parse_mode="HTML")
        elif dict_req['code'] == '11':
            with open("./mailing/news/news.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                bot.send_video(user_id, open('./mailing/news/videos/1.mp4', 'rb'), caption=text, parse_mode="HTML")
        elif dict_req['code'] == '12':
            with open("./mailing/news/news.txt", 'r', encoding='utf-8') as file:
                text = file.read()
                bot.send_video(user_id, open('./mailing/news/videos/1.mp4', 'rb'), caption=text, parse_mode="HTML")
        else:
            pass

def create_message_from_sound(message):
    user_id = message.from_user.id
    file_info = bot.get_file(message.voice.file_id)
    file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(TELEGRAM_TOKEN, file_info.file_path))
    with open(f'./sounds/{user_id}.ogg','wb') as f:
        f.write(file.content)
    try:
        s = AudioSegment.from_ogg(f'./sounds/{user_id}.ogg')
        s.export(f'sounds/{user_id}.mp3', format="mp3")
        res = create_text_from_audio(f'./sounds/{user_id}.mp3')
        return res
    except:
        bot.send_message(user_id,"Ошибка распознавания файла")
    try:
        os.remove(f'./sounds/{user_id}.ogg')
        os.remove(f'./sounds/{user_id}.mp3')
    except:
        pass

@bot.message_handler(content_types=['text', 'voice'])
def get_text_message(message):
    user_id = message.from_user.id #int
    if not check_sub(str(user_id)):
        not_in_sub_channel(user_id)
    else:
        if message.text == '/photo':
            print("!")
            file = open("videos/1.mp4", 'rb')
            bot.send_video(message.chat.id, file)
        elif message.text == '/invite' or message.text == "↗️ Пригласить":
            try:
                result_text = f"🚀 Поделитесь этой ссылкой с другом, чтобы получить дополнительны токены запросов \n <code>https://t.me/Proba778_bot?start={message.from_user.id}</code>" + " \n"
                bot.send_message(message.from_user.id, result_text, parse_mode="HTML", reply_markup=global_markup)
            except Exception as e:
                with open('error.txt', 'a') as f:
                    f.write(str(date.today()) + '/' + str(user_id) + '/' + str(e) + '\n')
        elif message.text == '/info' or message.text == "⚛️ Информация":
            try:
                result_text = hello_message
                bot.send_message(message.from_user.id, result_text, parse_mode="HTML", reply_markup=global_markup)
            except Exception as e:
                with open('error.txt', 'a') as f:
                    f.write(str(date.today()) + '/' + str(user_id) + '/' + str(e) + '\n')
        elif message.text == '/profile' or message.text == "🚸 Профиль":
            try:
                user_data = botUsers.get_user_by_id(str(user_id))
                result_text = f"<b>🚸Профиль пользователя @{user_data[0][1]}</b>\n\n"
                result_text += f"▪️ Ваш telegram-ID: <code>{user_data[0][0]}</code> \n\n"
                result_text += f'▪️ Кол-во приглашенных пользователей: <b>{user_data[0][2]}</b>\n\n'
                #result_text += f"▪️ Активировали ли вы premium аккаунт: {'<b>Пока нет</b>' if user_data[0][2] == 0 else '<b>Уже да👑</b>'} \n\n"
                result_text += f"▪️ Доступное количество запросов на вашем счету - <b>{user_data[0][5]}</b> \n\n"
                if user_data[0][6] != '':
                    result_text += f"▪️ Вас привел пользователь с ID - <b>{user_data[0][6]}</b>\n\n"
                result_text += f"▪️ Вы зарегистрировались: <b>{user_data[0][8]}</b>\n\n"
                result_text += f"▪️ Кол-во сделанных запросов вами за все время <b>{user_data[0][7]}</b> "
            except Exception as e:
                result_text = '▪️ Ошибка запроса к базе данных. Попробуйте повторить попытку позже 🙆‍♂️'
            try:
                bot.send_message(message.from_user.id, result_text, parse_mode="HTML", reply_markup=global_markup)
            except Exception as e:
                with open('error.txt', 'a') as f:
                    f.write(str(date.today()) + '/' + str(user_id) + '/' + str(e) + '\n')
        elif message.text == '/premium' or message.text == "👑 Премиум подписка":
            try:
                result_text = '▪️ Для получения премиум подписки пиши @Pavel_Potapov'
                bot.send_message(message.from_user.id, result_text, parse_mode="HTML", reply_markup=global_markup)
            except Exception as e:
                with open('error.txt', 'a') as f:
                    f.write(str(date.today()) + '/' + str(user_id) + '/' + str(e) + '\n')
        elif message.text == '/neuro' or message.text == "🧠 Нейронки на все случаи жизни":
            try:
                result_text = '▪️ <a href="https://progrramingforchild.notion.site/6f8a89c6a8cd44a4857a5ca5e4172b69">Здесь</a> полный список, пользуйся, изучай 😉'
                bot.send_message(message.from_user.id, result_text, parse_mode="HTML", reply_markup=global_markup)
            except Exception as e:
                with open('error.txt', 'a') as f:
                    f.write(str(date.today()) + '/' + str(user_id) + '/' + str(e) + '\n')
        elif message.text == 'Сбросить память':
            if clear_context(str(user_id)):
                bot.send_message(user_id, "🧹 Память очищена, можешь дальше пользоваться сетью 👇🏻")
            else:
                bot.send_message(user_id, "Ошибка очищения контекста, попробуй позже")
        else:
            result_text = ''
            if message.content_type == 'voice':
                try:
                    message.text = create_message_from_sound(message)
                    bot.send_message(user_id, f"Ващ запрос:\n{message.text}")
                except:
                    message.text = ""
            #основная логика запроса к нейронной сети 
            if len(message.text) > 0:
                try:
                    data = botUsers.get_user_by_id(str(user_id)) #получаем данные пользователя
                    context_user_data = create_context_user(data, message.text, role='user') #создаю в контексте сообщение от пользователя, чтобы оно добавилось в запрос в будущем
                    tokens = data[0][5] #доступные токены юзера
                    requests = data[0][7] #сколько запросов было сделано пользователем
                    if tokens > 0:
                        tokens -= 1
                        requests += 1
                        try:
                            botUsers.update_user_by_id(str(user_id), token=tokens, request=requests) #обновляю изера по запросам и токенам
                        except Exception as e:
                            bot.send_message(message.from_user.id, "▪️ Ошибка на стороне базы данных. Попробуйте повторить попытку позже 🙆‍♂️")  

                        #если ранее пользователь не делал запрос к чату
                        if not str(user_id) in global_state_message:
                            global_state_message[str(user_id)] = {}
                        if not "turbo3_5" in global_state_message[str(user_id)]:
                            global_state_message[str(user_id)]['turbo3_5'] = False
                        if not "davinci" in global_state_message[str(user_id)]:
                            global_state_message[str(user_id)]['davinci'] = False
                    
                        #если пользователь есть в глобальном словаре запросов и у него нет активного запроса к сети
                        if str(user_id) in global_state_message and global_state_message[str(user_id)]['turbo3_5'] == False:
                            global_state_message[str(user_id)]['turbo3_5'] = True #у пользователя фиксируем запрос к турбо3.5 версии
                            message1 = bot.send_message(message.from_user.id, "Ваш запрос обрабатывается. Время ожидания зависит от сложности запроса и может доходить до <b>3 минут</b> ⏱️", parse_mode="HTML")

                            #делаем рандомный стикер
                            random_sticker_number = random.randint(0, len(stickers_id))
                            sticker_hash = ''
                            for val in stickers_id[random_sticker_number].values():
                                sticker_hash = val
                            message2 = bot.send_sticker(message.from_user.id, sticker_hash)
                            #ОСНОВНОЙ ЗАПРОС К НЕЙРОСЕТИ
                            
                            #получение контекста для запроса
                            context_user_data_list = get_context_from(context_user_data)
                            result_text = chatgpt_response_turbo35(message.text, context_user_data_list)
                            #переполнили контекст
                            if result_text == 1:
                                clear_context_message(message.chat.id)
                                global_state_message[str(user_id)]['turbo3_5'] = False 
                            #много запросов
                            elif result_text == 2:
                                global_state_message[str(user_id)]['davinci'] = True #у пользователя фиксируем запрос к давинчи версии
                                bot.send_message(message.from_user.id, 'Много запросов в рамках чата. Перевожу запрос на общий чат')
                                bot.delete_message(message.chat.id, message1.message_id)
                                bot.delete_message(message.chat.id, message2.message_id)
                                result_text = (message.text, context_user_data_list)
                                result_text = chatgpt_response_davinci(message.text)
                                if result_text == 1:
                                    bot.send_message(message.from_user.id, 'Слишком длинный зарос, много букв!')
                                    global_state_message[str(user_id)]['davinci'] = False
                                elif result_text == 2:
                                    bot.send_message(message.from_user.id, 'Слишком много запросов, ожидайте!')
                                    global_state_message[str(user_id)]['davinci'] = False
                                else:
                                    try:
                                        bot.edit_message_text('Ответ от 🧿 АI 👇', message.chat.id, message1.message_id)
                                        bot.delete_message(message.chat.id, message2.message_id)
                                    except:
                                        pass
                                    for msg in util.split_string(result_text, 3000): #разбиваем запрос на 3к символов, чтобы не словить ошибку телеграмма о длинном сообщении
                                        bot.send_message(message.from_user.id, msg)
                                    global_state_message[str(user_id)]['davinci'] = False
                            else:
                                new_context_user_data_dict = create_context_assistant(context_user_data, result_text, role='assistant') 
                                if create_user_context_file(str(user_id), new_context_user_data_dict): #формируем временный файл контекста юзера
                                    try:
                                        data_file = read_file(f"users_context/{user_id}.json") #формируем бинарник из временного файла
                                        botUsers.update_user_by_id(user_id=str(user_id), message_history_context=data_file) #добавляем новый бинарник в бд
                                    except Exception as e:
                                        error_log('error.txt', e, user_id)
                                bot.edit_message_text('Ответ от 🧿 АI 👇', message.chat.id, message1.message_id)
                                bot.delete_message(message.chat.id, message2.message_id)
                                for msg in util.split_string(result_text, 3000): #разбиваем запрос на 3к символов, чтобы не словить ошибку телеграмма о длинном сообщении
                                    bot.send_message(message.from_user.id, msg)
                                global_state_message[str(user_id)]['davinci'] = False
                                global_state_message[str(user_id)]['turbo3_5'] = False
                    else: #нет токенов
                        bot.send_message(message.from_user.id, "▪️ У вас закончили бесплатные запросы 🙆‍♂️ Xочешь <b>ещё</b>? Тогда <b>пиши</b> @Pavel_Potapov", parse_mode="HTML", reply_markup=global_markup)
                        global_state_message[str(user_id)]['davinci'] = False
                        global_state_message[str(user_id)]['turbo3_5'] = False
                except Exception as e:
                    result_text = '▪️ Сейчас наблюдаем некоторые проблемы на стороне AI. Очень много запросов, попробуйте повторить попытку позже 🙆‍♂️'
                    bot.send_message(message.from_user.id, result_text, reply_markup=global_markup)
                    global_state_message[str(user_id)]['davinci'] = False
                    global_state_message[str(user_id)]['turbo3_5'] = False

print('бот работает')
bot.polling(non_stop=True, interval=0)

