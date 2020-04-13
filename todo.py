import os
import sqlite3

import requests
import telebot
from googletrans import Translator
from telebot import apihelper, types

LINE = "=" * 22

translator = Translator()

token = os.environ.get("BOT_TOKEN")
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

#


def cmds(dest):
    cmd = types.ReplyKeyboardMarkup()
    print(dest)
    cmd.row(
        "📒 " + translator.translate("Создать лист", dest=dest).text,
        "📝 " + translator.translate("Создать задачу", dest=dest).text,
    )
    cmd.row(
        "⇄ " + translator.translate("Сменить выбранный лист", dest=dest).text,
        "✅ " + translator.translate("Отметить задачу выполненой", dest=dest).text,
    )
    cmd.row(
        "📜 " + translator.translate("Просмотреть все задачи", dest=dest).text,
        "💰 " + translator.translate("Поблагодарить", dest=dest).text,
    )
    cmd.row("⚙️ " + translator.translate("Настроить выбранный лист", dest=dest).text)
    return cmd


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
            translator.translate(
                """
        Привет, мой друг!\n Вот вам немного моих команд:\n\n
        "📒 Создать лист" - создает новый список дел.\n
        "✏️ Создать задачу" - создает задачу в списке дел.\n
    """,
                dest=msg.from_user.language_code,
            ).text,
            parse_mode="Markdown",
            reply_markup=cmds(msg.from_user.language_code),
        )
    else:
        bot.send_message(
            msg.chat.id,
            translator.translate(
                "Хей! Почему давно не было новостей от тебя?",
                dest=msg.from_user.language_code,
            ).text,
            parse_mode="Markdown",
            reply_markup=cmds(msg.from_user.language_code),
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
        translator.translate(
            "Лист "
            + msg.text
            + ' был создан успешно.\n Теперь чтобы взаимодействовать с ним, вам необходимо его выбрать.\nДля этого выберите в меню пункт "Сменить выбранный лист"',
            dest=msg.from_user.language_code,
        ).text,
    )


def insertReport(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    id = msg.chat.id
    cursor.execute(
        "INSERT INTO `Reports` (`telegram-id`, `text`) VALUES(?,?);", (id, msg.text)
    )
    conn.commit()
    bot.send_message(
        id,
        translator.translate(
            "Ваш отчет об ошибке был отправлен.", dest=msg.from_user.language_code,
        ).text,
    )


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
            text=translator.translate(
                'Задача **"{}"** была успешно отмечена выполненной.'.format(
                    cursor.fetchone()[0]
                ),
                dest=msg.from_user.language_code,
            ).text,
            parse_mode="Markdown",
        )
    elif msg.data.split("_")[0] == "mainMenu":
        bot.clear_step_handler_by_chat_id(id)
        bot.edit_message_text(
            chat_id=id,
            message_id=msg.message.message_id,
            text=translator.translate(
                "Вы в главном меню.", dest=msg.from_user.language_code,
            ).text,
        )

    elif msg.data.split("_")[0] == "deleteList":
        if msg.data.split("_")[1] == "STEP0":
            cursor.execute(
                "SELECT `id`,`title` FROM `Todo-lists` WHERE `telegram-id`=?", (id,)
            )
            markup = types.InlineKeyboardMarkup()
            tasks = cursor.fetchall()
            markup.row(
                types.InlineKeyboardButton(
                    translator.translate(
                        "Главное меню", dest=msg.from_user.language_code,
                    ).text,
                    callback_data="mainMenu_",
                )
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
                text=translator.translate(
                    "Пожалуйста выберите задачу для удаления или выйдите в главное меню:",
                    dest=msg.from_user.language_code,
                ).text,
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
                text=translator.translate(
                    "Todo-list был удаленн удачно.", dest=msg.from_user.language_code,
                ).text,
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
                text=translator.translate(
                    "Пожалуйста выберите задачу для удаления или выйдите в главное меню:",
                    dest=msg.from_user.language_code,
                ).text,
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
                text=translator.translate(
                    "Задача была удаленна удачно.", dest=msg.from_user.language_code,
                ).text,
            )
    elif msg.data.split("_")[0] == "report":
        bot.edit_message_reply_markup(
            id, message_id=msg.message.message_id, reply_markup=""
        )
        bot.send_message(
            id,
            translator.translate(
                "Отправьте мне ваш отчет об ошибках.🦠",
                dest=msg.from_user.language_code,
            ).text,
        )
        bot.register_next_step_handler_by_chat_id(id, insertReport)


def createTask(msg, prjct):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    if msg.text == "Главное меню":
        bot.send_message(msg.chat.id, "Вы в главном меню!")
        return
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
        translator.translate(
            'Вы успешно создали задачу **"{}"**.'.format(msg.text),
            dest=msg.from_user.language_code,
        ).text,
        parse_mode="Markdown",
    )


def changeList(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    if msg.text == "Главное меню":
        bot.send_message(msg.chat.id, "Вы в главном меню!")
        return
    cursor.execute(
        "UPDATE `Users` SET `thisPrjct`=? WHERE `telegram-id`=?",
        (msg.text.split(" ")[0], msg.chat.id),
    )
    conn.commit()
    bot.send_message(
        msg.chat.id,
        translator.translate(
            "Вы успешно выбрали проект " + msg.text + ".",
            dest=msg.from_user.language_code,
        ).text,
        reply_markup=cmds(msg.from_user.language_code),
    )


@bot.message_handler(content_types=["text"])
def text(msg):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()

    cmd = msg.text

    if (
        cmd
        == "📒 "
        + translator.translate("Создать лист", dest=msg.from_user.language_code,).text
    ):
        bot.send_message(
            msg.chat.id,
            translator.translate(
                "Пожалуйста отправь мне название списка.",
                dest=msg.from_user.language_code,
            ).text,
        )
        bot.register_next_step_handler_by_chat_id(
            msg.chat.id, lambda msg: createList(msg)
        )
    elif (
        cmd
        == "⇄ "
        + translator.translate(
            "Сменить выбранный лист", dest=msg.from_user.language_code,
        ).text
    ):
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
            prjcts.row("Главное меню")
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

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton(
                    translator.translate(
                        "Главное меню", dest=msg.from_user.language_code,
                    ).text,
                    callback_data="mainMenu_",
                )
            )
            bot.send_message(
                msg.chat.id,
                translator.translate(
                    "Пожалуйста выберите лист.", dest=msg.from_user.language_code,
                ).text,
                reply_markup=prjcts,
            )
            bot.register_next_step_handler_by_chat_id(
                msg.chat.id, lambda msg: changeList(msg)
            )
        except:
            bot.send_message(
                msg.chat.id,
                translator.translate(
                    "У вас нет Todo-list.", dest=msg.from_user.language_code,
                ).text,
            )
    elif (
        cmd
        == "📝 "
        + translator.translate("Создать задачу", dest=msg.from_user.language_code,).text
    ):
        try:
            cursor.execute(
                "SELECT `thisPrjct` FROM `Users` WHERE `telegram-id`=?", (msg.chat.id,)
            )
            prjct = cursor.fetchone()
            cursor.execute("SELECT `title` FROM `Todo-lists` WHERE `id`=?", prjct)

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton(
                    translator.translate(
                        "Главное меню", dest=msg.from_user.language_code,
                    ).text,
                    callback_data="mainMenu_",
                )
            )

            bot.send_message(
                msg.chat.id,
                translator.translate(
                    'Задача будет создана в списке "{pj}"'.format(
                        pj=cursor.fetchone()[0]
                    ),
                    dest=msg.from_user.language_code,
                ).text,
                reply_markup=markup,
            )
            bot.register_next_step_handler_by_chat_id(
                msg.chat.id, lambda msg: createTask(msg, prjct[0])
            )
        except:
            bot.send_message(
                msg.chat.id,
                translator.translate(
                    "Либо в этом списке нет задач, либо вы не выбрали нужный список.",
                    dest=msg.from_user.language_code,
                ).text,
            )
    elif (
        cmd
        == "✅ "
        + translator.translate(
            "Отметить задачу выполненной", dest=msg.from_user.language_code,
        ).text
    ):
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
                msg.chat.id,
                translator.translate(
                    "Пожалуйста выберите задачу.", dest=msg.from_user.language_code,
                ).text,
                reply_markup=markup,
            )
        except:
            bot.send_message(
                msg.chat.id,
                translator.translate(
                    "Либо в этом списке нет задач, либо вы не выбрали нужный список.",
                    dest=msg.from_user.language_code,
                ).text,
            )

    elif (
        cmd
        == "📜 "
        + translator.translate(
            "Просмотреть все задачи", dest=msg.from_user.language_code,
        ).text
    ):
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
                text = translator.translate(
                    "🎉Хей!🎉\n\rПоздравляем ты выполнил все задачи в этом списке!\n"
                    + text,
                    dest=msg.from_user.language_code,
                ).text
            bot.send_message(msg.chat.id, text)
        except:
            bot.send_message(
                msg.chat.id,
                translator.translate(
                    "Либо в этом списке нет задач, либо вы не выбрали нужный список.",
                    dest=msg.from_user.language_code,
                ).text,
            )

    elif (
        cmd
        == "💰 "
        + translator.translate("Поблагодарить", dest=msg.from_user.language_code,).text
    ):
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton(
                text=translator.translate(
                    "Поддержать", dest=msg.from_user.language_code,
                ).text,
                url="https://www.donationalerts.com/r/redfoxbotmaker",
            )
        )
        bot.send_message(
            msg.chat.id,
            translator.translate("Вот ссылка", dest=msg.from_user.language_code,).text,
            reply_markup=markup,
        )
    elif (
        cmd
        == "⚙️ "
        + translator.translate(
            "Настроить выбранный лист", dest=msg.from_user.language_code,
        ).text
    ):

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton(
                translator.translate(
                    "Главное меню", dest=msg.from_user.language_code,
                ).text,
                callback_data="mainMenu_",
            )
        )
        markup.row(
            types.InlineKeyboardButton(
                translator.translate(
                    "Удалить задачу", dest=msg.from_user.language_code,
                ).text,
                callback_data="deleteTask_STEP0",
            )
        )

        markup.row(
            types.InlineKeyboardButton(
                translator.translate(
                    "Удалить список", dest=msg.from_user.language_code,
                ).text,
                callback_data="deleteList_STEP0",
            )
        )
        markup.row(
            types.InlineKeyboardButton(
                translator.translate(
                    "Отправить отзыв", dest=msg.from_user.language_code,
                ).text,
                callback_data="report_",
            )
        )
        bot.send_message(
            msg.chat.id,
            translator.translate(
                "Все настройки:", dest=msg.from_user.language_code,
            ).text,
            reply_markup=markup,
        )
    else:
        bot.send_message(
            msg.chat.id,
            translator.translate(
                "📣Хей!📣\nБрат, я не знаю такой команды, чтобы узнать список команд введи /help",
                dest=msg.from_user.language_code,
            ).text,
        )


print(LINE)
print("Bot have been started!")
print(LINE)

bot.polling()
