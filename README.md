# SynCrypto-remote
SynCrypto-remote - приложение для облачной сихронизации и использованием оконечного шифрования.
[![N|Solid](https://www.python.org/static/community_logos/python-powered-w-140x56.png)](https://www.python.org/)
# Характеристики
  - Сквозное шифрование для пользовательских данных. Никто, кроме обладателя секрета не имеет представления о структуре данных.
  - Шифрование с применением криптографическихпримитивов [cryptography](https://cryptography.io/en/latest/) 
  - Использование транспорта [ZMQ](http://zeromq.org/)
  - Использование [Noise Protocol](http://noiseprotocol.org/) для обеспечения безопасного канала передачи
  - Применение [SQLAlchemy](https://www.sqlalchemy.org/) для работы с данными пользователей на сервере
  - ...

# Установка
Клонируйте репозиторий
```sh
$ git clone https://github.com/dokzlo13/syncrypto-remote.git
```
Установите зависимости
```sh
$ cd syncrypto-remote
$ pip3 install -r requirements.txt
```
Для запуска сервера используйте
```sh
$ python runserver.py
```
При этом в рабочем каталоге создатся база данных sqlite и каталог storage

При первом подключении к серверу необходимо зарегестрировать нового пользователя.
Для этого необходимо запустить клиент с параметром -r
```sh
$ python runclient.py -r -u username -p password
```
После этого необходимо инициализировать каталог для синхронизации
```sh
$ python runclient.py -u username -p password ./dir -i
```
Теперь можно запускать синхронизацию, которая будет происходить в бесконечном цикле
```sh
$ python runclient.py -u username -p password ./dir
```
ЕДиноразовую синхронизацию можно произвести, добавив ключ -o

Данный проект был реализован с применением исходных кодов проекта:
https://github.com/liangqing/syncrypto

