import sqlite3
import os
import requests
import telebot
from telebot import types
from telebot import apihelper

LINE = "=" * 22

tocken = os.environ.get("BOT_TOKEN")
SELECT = "SELECT {cl} FROM {tb} WHERE {wCL}={wVL};"
INSERT = "INSERT INTO {tb} ({cls}) VALUES ({vls})"
UPDATE = "UPDATE {tb} SET {st}=? WHERE {wCL}={wVL}"


conn = sqlite3.connect("todo.db")

cursor = conn.cursor()

cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS `Users` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            `telegram-id` intenger NOT NULL,
            `name` varchar(255) NOT NULL,
            `thisPrjct` varchar(255) ,
            `todo-lists` text
        );
"""
)

cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS `Todo-lists` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            `telegram-id` intenger NOT NULL,
            `members-id` intenger,
            `title` varchar(255) NOT NULL,
            `tasks` text
        );
"""
)


cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS `Tasks` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            `Todo-list-id` intenger NOT NULL,
            `title` varchar(255) NOT NULL,
            `description` text,
            `checked` bool NOT NULL
        );
"""
)

cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS `Reports` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            `telegram-id` intenger NOT NULL,
            `text` text NOT NULL
        );
"""
)

conn.commit()

bot = telebot.TeleBot(token)

cmds = telebot.types.ReplyKeyboardMarkup()
cmds.row("📒 Создать лист", "📝 Создать задачу")
cmds.row("⇄ Сменить выбранный лист", "✅ Отметить задачу выполненой")
cmds.row("📜 Просмотреть все задачи", "💰 Поблагодарить")
cmds.row("⚙️ Настроить выбранный лист")


@bot.message_handler(commands=["help", "start"])
def startMSG(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()

    if msg.from_user.username != None:
        name = str(msg.from_user.username)
    else:
        name = str(msg.from_user.first_name) + " " + str(msg.from_user.last_name)
    cursor.execute(
        """
                select * from `Users` where `telegram-id`={0}
    """.format(
            msg.from_user.id
        )
    )
    if cursor.fetchone() == None:
        cursor.execute(
            """
                INSERT INTO `Users` (`telegram-id`,`name`) VALUES (?,?);
        """,
            (msg.from_user.id, name),
        )
        conn.commit()
        bot.send_message(
            msg.chat.id,
            """
        Привет, мой друг!\n Вот вам немного моих команд:\n\n
        "📒 Создать лист" - создает новый список дел.\n
        "✏️ Создать задачу" - создает задачу в списке дел.\n
    """,
            parse_mode="Markdown",
            reply_markup=cmds,
        )
    else:
        bot.send_message(
            msg.chat.id,
            "Хей! Почему давно не было новостей от тебя?",
            parse_mode="Markdown",
            reply_markup=cmds,
        )


def createList(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()

    cursor.execute(
        INSERT.format(tb="`Todo-lists`", cls="`telegram-id`,`title`", vls="?,?"),
        (msg.chat.id, msg.text),
    )
    conn.commit()
    cursor.execute(
        "SELECT `id` FROM `Todo-lists` WHERE `telegram-id`=?", (msg.chat.id,),
    )

    ids = cursor.fetchall()
    ids = [str(id[0]) for id in ids]
    ids = ";".join(ids)
    cursor.execute(
        "UPDATE `Users` SET `todo-lists`=? WHERE `telegram-id`=?", (ids, msg.chat.id)
    )
    conn.commit()
    bot.send_message(
        msg.chat.id,
        "Лист "
        + msg.text
        + ' был создан успешно.\n Теперь чтобы взаимодействовать с ним, вам необходимо его выбрать.\nДля этого выберите в меню пункт "Сменить выбранный лист"',
    )


def insertReport(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    id = msg.chat.id
    cursor.execute(
        "INSERT INTO `Reports` (`telegram-id`, `text`) VALUES(?,?);", (id, msg.text)
    )
    conn.commit()
    bot.send_message(id, "Ваш отчет об ошибке был отправлен.")


@bot.callback_query_handler(func=lambda msg: True)
def queryHandler(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    id = msg.message.chat.id
    if msg.data.split("_")[0] == "checkedTask":
        bot.edit_message_reply_markup(
            id, message_id=msg.message.message_id, reply_markup=""
        )  # удаляем кнопки у последнего сообщения
        task = msg.data.split("_")
        cursor.execute(
            "UPDATE `Tasks` SET `checked`=? WHERE `id`=?", (True, int(task[1])),
        )
        conn.commit()
        cursor.execute("SELECT `title` FROM `Tasks` WHERE `id`=?", (task[1],))
        bot.edit_message_text(
            chat_id=id,
            message_id=msg.message.message_id,
            text='Задача **"{}"** была успешно отмечена выполненной.'.format(
                cursor.fetchone()[0]
            ),
            parse_mode="Markdown",
        )
    elif msg.data.split("_")[0] == "mainMenu":
        bot.edit_message_text(
            chat_id=id, message_id=msg.message.message_id, text="Вы в главном меню."
        )

    elif msg.data.split("_")[0] == "deleteList":
        if msg.data.split("_")[1] == "STEP0":
            cursor.execute(
                "SELECT `id`,`title` FROM `Todo-lists` WHERE `telegram-id`=?", (id,)
            )
            markup = types.InlineKeyboardMarkup()
            tasks = cursor.fetchall()
            markup.row(
                types.InlineKeyboardButton("Главное меню", callback_data="mainMenu_")
            )
            for task in tasks:
                markup.row(
                    types.InlineKeyboardButton(
                        str(task[1]), callback_data="deleteList_STEP1_" + str(task[0]),
                    )
                )
            bot.edit_message_text(
                chat_id=id,
                message_id=msg.message.message_id,
                text="Пожалуйста выберите задачу для удаления или выйдите в главное меню:",
            )
            bot.edit_message_reply_markup(
                id, message_id=msg.message.message_id, reply_markup=markup
            )
        elif msg.data.split("_")[1] == "STEP1":
            tid = msg.data.split("_")[2]
            cursor.execute("DELETE FROM `Todo-lists` WHERE `id`=?", (tid,))
            cursor.execute("DELETE FROM `Tasks` WHERE `Todo-list-id`=?", (tid,))
            conn.commit()
            bot.edit_message_reply_markup(
                id, message_id=msg.message.message_id, reply_markup=""
            )
            bot.edit_message_text(
                chat_id=id,
                message_id=msg.message.message_id,
                text="Todo-list был удаленн удачно.",
            )
    elif msg.data.split("_")[0] == "deleteTask":
        if msg.data.split("_")[1] == "STEP0":
            cursor.execute(
                "SELECT `thisPrjct` FROM `Users` WHERE `telegram-id`=?", (id,)
            )
            cursor.execute(
                "SELECT `id`,`title`, `checked` FROM `Tasks` WHERE `Todo-list-id`=?",
                cursor.fetchone(),
            )
            markup = types.InlineKeyboardMarkup()
            tasks = cursor.fetchall()
            markup.row(
                types.InlineKeyboardButton("Главное меню", callback_data="mainMenu_")
            )
            for task in tasks:
                if task[2]:
                    markup.row(
                        types.InlineKeyboardButton(
                            "✅" + str(task[1]),
                            callback_data="deleteTask_STEP1_" + str(task[0]),
                        )
                    )
                else:
                    markup.row(
                        types.InlineKeyboardButton(
                            "❌" + str(task[1]),
                            callback_data="deleteTask_STEP1_" + str(task[0]),
                        )
                    )
            bot.edit_message_text(
                chat_id=id,
                message_id=msg.message.message_id,
                text="Пожалуйста выберите задачу для удаления или выйдите в главное меню:",
            )
            bot.edit_message_reply_markup(
                id, message_id=msg.message.message_id, reply_markup=markup
            )
        elif msg.data.split("_")[1] == "STEP1":
            tid = msg.data.split("_")[2]
            cursor.execute("DELETE FROM `Tasks` WHERE `id`=?", (tid,))
            conn.commit()
            bot.edit_message_reply_markup(
                id, message_id=msg.message.message_id, reply_markup=""
            )
            bot.edit_message_text(
                chat_id=id,
                message_id=msg.message.message_id,
                text="Задача была удаленна удачно.",
            )
    elif msg.data.split("_")[0] == "report":
        bot.edit_message_reply_markup(
            id, message_id=msg.message.message_id, reply_markup=""
        )
        bot.send_message(id, "Отправьте мне ваш отчет об ошибках.🦠")
        bot.register_next_step_handler_by_chat_id(id, insertReport)


def createTask(msg, prjct):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO `Tasks` (`Todo-list-id`, `title`, `checked`) VALUES (?,?,?)",
        (prjct, msg.text, False),
    )
    conn.commit()
    cursor.execute("SELECT `id` FROM `Tasks` WHERE `Todo-list-id`=?", (prjct,))
    ids = cursor.fetchall()
    ids = [str(id[0]) for id in ids]
    ids = ";".join(ids)
    cursor.execute("UPDATE `Todo-lists` SET `tasks`=? WHERE `id`=?", (ids, prjct))
    conn.commit()
    bot.send_message(
        msg.chat.id,
        'Вы успешно создали задачу **"{}"**.'.format(msg.text),
        parse_mode="Markdown",
    )


def changeList(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE `Users` SET `thisPrjct`=? WHERE `telegram-id`=?",
        (msg.text.split(" ")[0], msg.chat.id),
    )
    conn.commit()
    bot.send_message(
        msg.chat.id, "Вы успешно выбрали проект " + msg.text + ".", reply_markup=cmds
    )


@bot.message_handler(content_types=["text"])
def text(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()

    cmd = msg.text

    if cmd == "📒 Создать лист":
        bot.send_message(msg.chat.id, "Пожалуйста отправь мне название списка.")
        bot.register_next_step_handler_by_chat_id(
            msg.chat.id, lambda msg: createList(msg)
        )
    elif cmd == "⇄ Сменить выбранный лист":
        try:
            prjcts = telebot.types.ReplyKeyboardMarkup()
            cursor.execute(
                "SELECT `todo-lists` FROM `Users` WHERE `telegram-id`=?", (msg.chat.id,)
            )
            projects = cursor.fetchone()[0].split(";")
            allprjcts = []

            for project in projects:
                cursor.execute(
                    "SELECT `title` FROM `Todo-lists` WHERE `id`=?", (project,)
                )
                allprjcts.append([project, cursor.fetchone()[0]])

            tmp = []
            i = 0
            for prjct in allprjcts:

                if i != 3:
                    tmp.append(" ".join(prjct))
                    i += 1
                else:
                    tmp.append(" ".join(prjct))
                    prjcts.row(*tmp)
                    tmp = []
                    i = 0
            else:
                prjcts.row(*tmp)
            bot.send_message(
                msg.chat.id, "Пожалуйста выберите лист.", reply_markup=prjcts
            )
            bot.register_next_step_handler_by_chat_id(
                msg.chat.id, lambda msg: changeList(msg)
            )
        except:
            bot.send_message(msg.chat.id, "У вас нет Todo-list.")
    elif cmd == "📝 Создать задачу":
        try:
            cursor.execute(
                "SELECT `thisPrjct` FROM `Users` WHERE `telegram-id`=?", (msg.chat.id,)
            )
            prjct = cursor.fetchone()
            cursor.execute("SELECT `title` FROM `Todo-lists` WHERE `id`=?", prjct)

            bot.send_message(
                msg.chat.id,
                'Задача будет создана в списке "{pj}"'.format(pj=cursor.fetchone()[0]),
            )
            bot.register_next_step_handler_by_chat_id(
                msg.chat.id, lambda msg: createTask(msg, prjct[0])
            )
        except:
            bot.send_message(
                msg.chat.id,
                "Либо в этом списке нет задач, либо вы не выбрали нужный список.",
            )
    elif cmd == "✅ Отметить задачу выполненной":
        try:
            cursor.execute(
                "SELECT `thisPrjct` FROM `Users` WHERE `telegram-id`=?", (msg.chat.id,)
            )
            cursor.execute(
                "SELECT `id`, `title`, `checked` FROM `Tasks` WHERE `Todo-list-id` = ?",
                cursor.fetchone(),
            )
            markup = types.InlineKeyboardMarkup()
            tasks = cursor.fetchall()

            tmp = []
            i = 0
            for task in tasks:
                if task[2] == False:
                    markup.row(
                        types.InlineKeyboardButton(
                            text="❌" + task[1],
                            callback_data="checkedTask_" + str(task[0]),
                        )
                    )
                else:
                    markup.row
                    (types.InlineKeyboardButton(text="✅" + task[1]))
            bot.send_message(
                msg.chat.id, "Пожалуйста выберите задачу.", reply_markup=markup
            )
        except:
            bot.send_message(
                msg.chat.id,
                "Либо в этом списке нет задач, либо вы не выбрали нужный список.",
            )

    elif cmd == "📜 Просмотреть все задачи":
        try:
            cursor.execute(
                "SELECT `thisPrjct` FROM `Users` WHERE `telegram-id`=?", (msg.chat.id,)
            )
            cursor.execute(
                "SELECT `title`, `checked` FROM `Tasks` WHERE `Todo-list-id`=?",
                cursor.fetchone(),
            )
            text = ""
            tasks = cursor.fetchall()
            t = 0
            f = 0
            for task in tasks:
                if task[1]:
                    t += 1
                    text += "✅ " + str(task[0]) + "\r\n"
                else:
                    f += 1
                    text += "❌ " + str(task[0]) + "\r\n"
            if t > f and f == 0:
                text = (
                    "🎉Хей!🎉\n\rПоздравляем ты выполнил все задачи в этом списке!\n"
                    + text
                )
            bot.send_message(msg.chat.id, text)
        except:
            bot.send_message(
                msg.chat.id,
                "Либо в этом списке нет задач, либо вы не выбрали нужный список.",
            )

    elif cmd == "💰 Поблагодарить":
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton(
                text="Поддержать", url="https://www.donationalerts.com/r/redfoxbotmaker"
            )
        )
        bot.send_message(msg.chat.id, "Вот ссылка", reply_markup=markup)
    elif cmd == "⚙️ Настроить выбранный лист":

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("Главное меню", callback_data="mainMenu_")
        )
        markup.row(
            types.InlineKeyboardButton(
                "Удалить задачу", callback_data="deleteTask_STEP0"
            )
        )

        markup.row(
            types.InlineKeyboardButton(
                "Удалить список", callback_data="deleteList_STEP0"
            )
        )
        markup.row(
            types.InlineKeyboardButton("Отправить отзыв", callback_data="report_")
        )
        bot.send_message(msg.chat.id, "Все настройки:", reply_markup=markup)
    else:
        bot.send_message(
            msg.chat.id,
            "📣Хей!📣\nБрат, я не знаю такой команды, чтобы узнать список команд введи /help",
        )


print(LINE)
print("Bot have been started!")
print(LINE)

bot.polling()
