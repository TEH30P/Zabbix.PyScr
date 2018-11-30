# Zabbix.PyScr
Python скрипты автоматизации Zabbix.

## DotGraphToMap
Строит карту сети Zabbix из описания на языке [DOT](https://ru.wikipedia.org/wiki/DOT_(%D1%8F%D0%B7%D1%8B%D0%BA)). 

Версия zabbix: `3.4`
Версия python: `3.6`

### Зависимости:
* [PyZabbix](https://github.com/lukecyca/pyzabbix) `0.75`
* [Graphviz](https://graphviz.gitlab.io/)  `2.38`

### Файлы:
* `zbx-dotgraph-to-map.py` - корневой скрипт.
* `zbx-dotgraph-to-map.json` - основные настройки скрипта.

### Установка:
Для запуска скрипта требуется установить необходимые компоненты, указанные в разделе **Зависимости:**.

### Запуск (параметры):
Скрипту требуется заполненый json с настройками. В качестве входного парамера передаётся путь к файлу `*.dot` с описанием графа сети. Так же скрипт будет искать файл с расширением `*.json` и тем же именем что cdp файл переданный в первом параметре.

Формат `zbx-dotgraph-to-map.json`:
* `zbx_host`, `[str]` **обяз** - адрес zabbix сервера для API вызовов.
* `zbx_login`, `[str]` **обяз** - логин на zabbix с правами на создание карт сети и просмотра item'ов и trigger'ов на host'ах которые будут отображены на карте.
* `zbx_password`, `[str]` **обяз** - пароль к логину `zbx_login`.
* `zbx_map_height`, `[str]` **обяз** - высота zabbix map, карта сети будет с указанной высотой и шириной пропорциональной исходной (в dot-файле) диаграмме. При этом если высота диаграммы больше её ширины, то результирующая карта сети  будет повёрнута на 90 градусов.
* `dot_engine`, `[str]` **обяз** - название движка для разбора входного dot файла. Скрипт поддерживает движки из [Graphviz](https://www.graphviz.org/): `sfdp`, `fdp` и `neato`.
* `line_decor`, **обяз** - настройки отображения связей карты сети. См.  [Объект карты сети](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/object)
  * `ok`, **обяз** - настройки связей карты сети без триггеров. Параметр `links` метода zabbix api [map.create](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/create).
    * `color`, `[str]` **!обяз** -  значение свойства `color` объекта [Связь карты](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/object#%D1%81%D0%B2%D1%8F%D0%B7%D1%8C_%D0%BA%D0%B0%D1%80%D1%82%D1%8B) zabbix api
    * `drawtype`, `[str]` **!обяз** - значение свойства `drawtype` объекта [Связь карты](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/object#%D1%81%D0%B2%D1%8F%D0%B7%D1%8C_%D0%BA%D0%B0%D1%80%D1%82%D1%8B) zabbix api
  * `ncl`, **обяз** - настройки триггера связи на карте сети, для триггеров с важностью "не классифицировано". Свойство `linktriggers` параметра `links` метода zabbix api [map.create](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/create).
    * `color`, `[str]` **!обяз** -  значение свойства `color` объекта [Триггера связи на карте](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/object#%D1%82%D1%80%D0%B8%D0%B3%D0%B3%D0%B5%D1%80%D0%B0_%D1%81%D0%B2%D1%8F%D0%B7%D0%B8_%D0%BD%D0%B0_%D0%BA%D0%B0%D1%80%D1%82%D0%B5) zabbix api
    * `drawtype`, `[str]` **!обяз** - значение свойства `drawtype` объекта [Триггера связи на карте](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/object#%D1%82%D1%80%D0%B8%D0%B3%D0%B3%D0%B5%D1%80%D0%B0_%D1%81%D0%B2%D1%8F%D0%B7%D0%B8_%D0%BD%D0%B0_%D0%BA%D0%B0%D1%80%D1%82%D0%B5) zabbix api
  * `inf`, **обяз** - аналогично `ncl` для триггеров с важностью "информационный".
  * `wrn`, **обяз** - аналогично `ncl` для триггеров с важностью "предупреждение".
  * `avg`, **обяз** - аналогично `ncl` для триггеров с важностью "средний".
  * `hgh`, **обяз** - аналогично `ncl` для триггеров с важностью "высокий".
  * `dss`, **обяз** - аналогично `ncl` для триггеров с важностью "чрезвычайный".

Формат входного файла `*.dot`:
* файл должен быть написан на языке [DOT](https://ru.wikipedia.org/wiki/DOT_(%D1%8F%D0%B7%D1%8B%D0%BA)) и успешно разбираться движком [Graphviz](https://www.graphviz.org/).
* Имена узлов диаграмы должны иметь следующий формат:
  * Узлы с менем начинающимся с "`id`" считаются узлами заббикс хостов, при этом строка после "`id`" должна быть равна `hostid` [объекта узла сети](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/host/object) zabbix.
  * Узлы с менем начинающимся с "`unk`" это "неизвестные узлы" на карте, они будут отображаться как "изображение": свойство [элемента карты](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/object#%D1%8D%D0%BB%D0%B5%D0%BC%D0%B5%D0%BD%D1%82_%D0%BA%D0%B0%D1%80%D1%82%D1%8B) `elementtype` = "4 - изображение".

Формат входного файла `*.json`:
* `<имя узла диаграмы>`, `[str]` **?обяз** - доп описание узла диаграмы из `*.dot`
  * `map_icon_off` - имя изображения для свойства [элемента карты](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/map/object#%D1%8D%D0%BB%D0%B5%D0%BC%D0%B5%D0%BD%D1%82_%D0%BA%D0%B0%D1%80%D1%82%D1%8B) `iconid_off`. Скрипт найдёт изображение с именем полностью совпадающем с этим атрибутом.
  * `map_edge`, **?обяз** - настройки поиска триггеров которые должны быть добавлены в связи узла `<имя узла диаграмы>`. Игнорируется для "неизвестных узлов".
    * `<имя соседнего узла диаграммы>`, `[str]` **?обяз** - настройки поиска триггеров которые должны быть добавлены в связь между `<имя соседнего узла диаграммы>` и `<имя узла диаграмы>`. Указывается для каждой связи.
	* `description`, **!обяз** `[list]` - список имён триггеров для поиска, скрипт ищет тригеры стандартным алгоритмом zabbix api [trigger.get
](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/trigger/get) - т.е. все триггеры имеющие вхождение хотябы одной строки будут добавлены на связь.
	* `item`, **!обяз** `[list]` - список ключей [элементов данных](https://www.zabbix.com/documentation/3.4/ru/manual/api/reference/item/object) (св-во `key_`). Все триггеры в которые входит хотябы один из элементов данных, указанных сдесь, будут добавлены на связь.

### Пример запуска скрипта
~~~ bash
python ./zbx-dotgraph-to-map.py ./DotGraphToMap/example/0.dot
~~~
Пример входных файлов dot и json находится в папке `/DotGraphToMap/example`. Пример НЕ РАБОЧИЙ, т.к. указанные там идентификаторы объектов узла сети zabbix являются случайными.

### Совместимость
Скрипт тестировался в "`Python 3.6.4 |Anaconda, Inc.| (default, Jan 16 2018, 10:22:32) [MSC v.1900 64 bit (AMD64)] on win32`" на Windows 10.

## CDPDataToDot
Основываясь на данных cisco-cdp элементов zabbix, формирует входные файлы (*.cdp и *.json) для работы скрипта DotGraphToMap. Поиск хостов и конкретных элементов данных zabbix со значениями cisco-cdp настраивается.

Версия zabbix: `3.4`
Версия python: `3.6`

### Зависимости:
* [PyZabbix](https://github.com/lukecyca/pyzabbix) `0.75`

### Файлы:
* `zbx-cdpdata-to-dot.py` - корневой скрипт.
* `zbx-cdpdata-to-dot.json` - основные настройки скрипта.
* `net-snmp2-cdp.zbxt.xml` - шаблон zabbix для сбора данных cisco-cdp, в котором есть все элементы данных необходимые для работы скрипта.

### Установка:
Для запуска скрипта требуется установить необходимые компоненты, указанные в разделе **Зависимости:**.

### Запуск (параметры):
Скрипту требуется заполненый json с настройками.

Формат `zbx-cdpdata-to-dot.json`:
* `zbx_host`, `[str]` **обяз** - адрес zabbix сервера для API вызовов.
* `zbx_login`, `[str]` **обяз** - логин на zabbix с правами на создание карт сети и просмотра item'ов и trigger'ов на host'ах которые будут отображены на карте.
* `zbx_password`, `[str]` **обяз** - пароль к логину `zbx_login`.

### Пример запуска скрипта
~~~ bash
python ./zbx-cdpdata-to-dot.py
~~~

### Совместимость
Скрипт тестировался в "`Python 3.6.4 |Anaconda, Inc.| (default, Jan 16 2018, 10:22:32) [MSC v.1900 64 bit (AMD64)] on win32`" на Windows 10.
