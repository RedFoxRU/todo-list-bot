import requests
import telebot
from bs4 import BeautifulSoup as BS

# todo: Подключение к телеграм боту
bot = telebot.TeleBot('1130314996:AAGrlYI-Ca8BqfS7jeeMoFPu8FTqwDJekig')


def parseWeather(city):
    html = requests.get('https://www.wunderground.com/weather/ru/'+city,).text
    html = BS(html, features="html.parser")
    el = html.select('.condition-data')
    return round((int(el[0].text.replace("| ", "").split(' ')[1].split('°')[1].replace('\xa0F', ''))-32)*(5/9))


@bot.message_handler(commands=['help', 'start'])
def startMSG(msg):
    bot.send_message(msg.chat.id, """
    Привет, мой друг!\n Если ты хочешь узнать погоду, можешь просто написать город или ввести:\n
    /weather Город
    """)


@bot.message_handler(commands=['weather'])
def weather(msg):
    city = msg.text.replace("/weather", "")
    if city != '' and city != ' ':
        bot.send_message(msg.chat.id, "Подождите, я субираю информацию.")
        print(msg.chat.id, city, msg.from_user.username)
        bot.send_message(msg.chat.id, "По городу {city} в среднем {t}°.".format(
            city=city, t=str(parseWeather(city))))
    else:
        bot.send_message(msg.chat.id, "Вы не ввели город")


@bot.message_handler(content_types=['text'])
def weatherS(msg):
    city = msg.text.replace("/weather", "")
    if city != '' and city != ' ':
        bot.send_message(msg.chat.id, "Подождите, я субираю информацию.")
        print(msg.chat.id, city, msg.from_user.username)
        bot.send_message(msg.chat.id, "По городу {city} в среднем {t}°.".format(
            city=city, t=str(parseWeather(city))))
    else:
        bot.send_message(msg.chat.id, "Вы не ввели город")


bot.infinity_polling()
