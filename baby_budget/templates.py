"""Ready-made sample list in Bulgarian and English.

It fills a new list file in the chosen language, as a starting point and a demo.
It is content, not UI text: switching the UI language later does not translate it.

Based on the NHS "What to buy for your newborn baby" guide and Bulgarian and
international newborn checklists (2023-2026). Items those sources advise against
(cot bumpers, pillows, sleep positioners/nests for unsupervised sleep) are
deliberately left out.
"""

from __future__ import annotations

from .model import Item, ShoppingList

# Section names: (bg, en)
SLEEP = ("Сън и детска стая", "Sleep & nursery")
CHANGING = ("Повиване и памперси", "Nappy changing")
BATH = ("Къпане и хигиена", "Bathing & hygiene")
FEEDING = ("Хранене", "Feeding")
LAUNDRY = ("Пране", "Laundry")
HEALTH = ("Здраве и комфорт", "Health & comfort")
MUSLINS = ("Муселинови пелени и одеала", "Muslins & blankets")
CLOTHES = ("Дрехи", "Clothes")
OUT = ("Разходка", "Out & about")
PLAY = ("Игра и занимания", "Play")
GOING_HOME = ("Изписване", "Going home")
MUM = ("За мама", "For mum")
HOSPITAL = ("Чанта за болницата", "Hospital bag")
LATER = ("След 6-ия месец", "After 6 months")

# (section, (name bg, name en), quantity, priority, (note bg, note en))
NO_NOTE = ("", "")
DEFAULT_ITEMS = [
    (SLEEP, ("Креватче / кошара", "Cot / crib"), 1, "must",
     ("Може и бебешко легло до вашето за първите месеци", "A bedside crib works for the first months")),
    (SLEEP, ("Матрак", "Mattress"), 1, "must",
     ("Само нов, твърд и плътно прилягащ към леглото", "New only, firm and fitting the cot with no gaps")),
    (SLEEP, ("Непромокаем протектор за матрак", "Waterproof mattress protector"), 2, "must", NO_NOTE),
    (SLEEP, ("Чаршафи с ластик", "Fitted sheets"), 4, "must", NO_NOTE),
    (SLEEP, ("Спален чувал", "Baby sleeping bag"), 2, "must",
     ("Вместо одеяло; без възглавници и обиколник в леглото",
      "Instead of a blanket; no pillows or bumpers in the cot")),
    (SLEEP, ("Пелена за повиване", "Swaddle"), 2, "nice", NO_NOTE),
    (SLEEP, ("Скрин / шкаф за дрехи", "Chest of drawers"), 1, "nice",
     ("Скрин с повивалник отгоре замества отделния повивалник",
      "One with a changing top replaces a separate changing table")),
    (SLEEP, ("Бебефон", "Baby monitor"), 1, "nice", NO_NOTE),
    (SLEEP, ("Нощна лампа", "Night light"), 1, "nice", NO_NOTE),
    (SLEEP, ("Термометър за стаята", "Room thermometer"), 1, "nice",
     ("Около 18–22 °C", "About 18–22 °C")),
    (CHANGING, ("Повивалник", "Changing mat"), 1, "must", NO_NOTE),
    (CHANGING, ("Памперси за новородено (пакет)", "Newborn nappies (pack)"), 2, "must",
     ("Отначало малко – бебето бързо израства", "Start small – babies outgrow sizes quickly")),
    (CHANGING, ("Мокри кърпички без аромат (пакет)", "Fragrance-free wipes (pack)"), 5, "must",
     ("Без аромат и без алкохол", "No fragrance, no alcohol")),
    (CHANGING, ("Крем против подсичане", "Nappy rash cream"), 1, "must", NO_NOTE),
    (CHANGING, ("Кофа за памперси", "Nappy bin"), 1, "nice", NO_NOTE),
    (BATH, ("Вана", "Baby bath"), 1, "must", NO_NOTE),
    (BATH, ("Хавлия с качулка", "Hooded towel"), 2, "must", NO_NOTE),
    (BATH, ("Термометър за вода", "Bath thermometer"), 1, "nice", NO_NOTE),
    (BATH, ("Бебешки шампоан / душ гел", "Baby wash"), 1, "must", NO_NOTE),
    (BATH, ("Крем за тяло", "Baby moisturiser"), 1, "nice", NO_NOTE),
    (BATH, ("Аспиратор за нос", "Nasal aspirator"), 1, "must", NO_NOTE),
    (BATH, ("Ножичка / пила за нокти", "Baby nail clippers / file"), 1, "must", NO_NOTE),
    (BATH, ("Мека четка за коса", "Soft hairbrush"), 1, "nice", NO_NOTE),
    (FEEDING, ("Шишета", "Bottles"), 3, "must",
     ("Няколко вида, за да видите кое ще хареса бебето", "A few kinds, to see which the baby likes")),
    (FEEDING, ("Резервни биберони", "Spare teats"), 2, "nice", NO_NOTE),
    (FEEDING, ("Залъгалки", "Dummies"), 2, "nice", NO_NOTE),
    (FEEDING, ("Четка за шишета", "Bottle brush"), 1, "must", NO_NOTE),
    (FEEDING, ("Препарат за бебешки съдове", "Baby-safe washing-up liquid"), 1, "must", NO_NOTE),
    (FEEDING, ("Стерилизатор", "Steriliser"), 1, "must", NO_NOTE),
    (FEEDING, ("Адаптирано мляко (резерва)", "Formula (a backup tin)"), 1, "nice",
     ("Марката – с педиатъра", "Ask your health visitor which one")),
    (FEEDING, ("Лигавници", "Bibs"), 3, "nice", NO_NOTE),
    (FEEDING, ("Термос", "Flask"), 1, "nice", ("За нощни хранения и разходки", "For night feeds and trips")),
    (FEEDING, ("Уред за затопляне на шишета", "Bottle warmer"), 1, "later",
     ("Източниците спорят – топла вода върши същото", "Sources disagree – warm water does the same")),
    (LAUNDRY, ("Прах за пране за бебе", "Baby laundry detergent"), 1, "must", NO_NOTE),
    (HEALTH, ("Термометър", "Digital thermometer"), 1, "must", NO_NOTE),
    (HEALTH, ("Средство за пъпчето", "Umbilical cord care"), 1, "must", NO_NOTE),
    (HEALTH, ("Физиологичен разтвор", "Saline drops"), 1, "must", NO_NOTE),
    (HEALTH, ("Бебешка аптечка", "Baby first-aid kit"), 1, "nice",
     ("Съдържанието – с педиатъра", "Check the contents with your doctor")),
    (MUSLINS, ("Муселинови пелени", "Muslin squares"), 6, "must", NO_NOTE),
    (MUSLINS, ("Одеяло за разходка", "Pram blanket"), 1, "must", NO_NOTE),
    (CLOTHES, ("Бодита", "Bodysuits / vests"), 6, "must", ("Размер 50–56", "Newborn size")),
    (CLOTHES, ("Гащеризончета / пижамки с цип", "Sleepsuits"), 6, "must", NO_NOTE),
    (CLOTHES, ("Жилетки", "Cardigans"), 2, "must", NO_NOTE),
    (CLOTHES, ("Шапки", "Hats"), 2, "must", ("Тънка и зимна", "A thin one and a warm one")),
    (CLOTHES, ("Чорапи", "Socks"), 4, "must", NO_NOTE),
    (CLOTHES, ("Ръкавички против драскане", "Scratch mittens"), 2, "must", NO_NOTE),
    (CLOTHES, ("Зимен гащеризон", "Snowsuit"), 1, "nice", ("Ако бебето се ражда наесен/зимата",
                                                         "If the baby arrives in autumn or winter")),
    (OUT, ("Количка", "Pram / pushchair"), 1, "must",
     ("За новородено – да може да лежи напълно", "Must let a newborn lie flat")),
    (OUT, ("Столче за кола", "Infant car seat"), 1, "must",
     ("Само ново, обърнато назад; проверете ISOFIX", "New only, rear-facing; check for ISOFIX")),
    (OUT, ("Дъждобран и мрежа против комари", "Rain cover and insect net"), 1, "nice",
     ("Ако не идват с количката", "If not included with the pram")),
    (OUT, ("Чанта за количката", "Changing bag"), 1, "must", NO_NOTE),
    (OUT, ("Огледало за задната седалка", "Back-seat mirror"), 1, "nice", NO_NOTE),
    (OUT, ("Слинг / кенгуру", "Sling / carrier"), 1, "nice", NO_NOTE),
    (PLAY, ("Активна гимнастика", "Play gym"), 1, "nice", NO_NOTE),
    (PLAY, ("Дрънкалки и меки играчки", "Rattles and soft toys"), 1, "nice", NO_NOTE),
    (PLAY, ("Шезлонг", "Bouncer"), 1, "later",
     ("Някои бебета го обичат, други не – може да изчака", "Some babies love it, some don't – it can wait")),
    (GOING_HOME, ("Комплект за изписване", "Going-home outfit"), 1, "must", NO_NOTE),
    (MUM, ("Сутиени за кърмене", "Nursing bras"), 2, "must",
     ("Мерки около 36–38 седмица", "Get measured at about 36–38 weeks")),
    (MUM, ("Подплънки за кърмене", "Breast pads"), 1, "must", NO_NOTE),
    (MUM, ("Крем за зърна", "Nipple cream"), 1, "must", NO_NOTE),
    (MUM, ("Възглавница за кърмене", "Nursing pillow"), 1, "nice", NO_NOTE),
    (MUM, ("Помпа за кърма", "Breast pump"), 1, "later",
     ("Когато стане ясно дали трябва", "Once you know you need one")),
    (MUM, ("Пликове за кърма", "Breast-milk storage bags"), 1, "later", NO_NOTE),
    (HOSPITAL, ("Следродилни превръзки (пакет)", "Maternity pads (pack)"), 2, "must", NO_NOTE),
    (HOSPITAL, ("Мрежести бикини за еднократна употреба", "Disposable maternity knickers"), 1, "must",
     NO_NOTE),
    (HOSPITAL, ("Нощници с предно закопчаване", "Front-opening nightdresses"), 2, "must", NO_NOTE),
    (HOSPITAL, ("Халат и чехли", "Dressing gown and slippers"), 1, "nice", NO_NOTE),
    (HOSPITAL, ("Дълъг кабел за зареждане", "Long phone charging cable"), 1, "nice", NO_NOTE),
    (LATER, ("Столче за хранене", "High chair"), 1, "later", NO_NOTE),
    (LATER, ("Кошара за игра", "Playpen"), 1, "later", NO_NOTE),
    (LATER, ("Протектори за контакти и ъгли", "Socket covers and corner guards"), 1, "later", NO_NOTE),
    (LATER, ("Бариера за стълби", "Stair gate"), 1, "later", NO_NOTE),
]

_INDEX = {"bg": 0, "en": 1}


def default_list(language: str = "bg") -> ShoppingList:
    i = _INDEX[language]
    return ShoppingList(
        items=[
            Item(name=names[i], section=section[i], quantity=qty, priority=priority, notes=note[i])
            for section, names, qty, priority, note in DEFAULT_ITEMS
        ],
        language=language,
    )
