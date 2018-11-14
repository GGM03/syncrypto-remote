#!/usr/bin/python3

import argparse
import os
import shutil

from server import ServerWorker
from server import Controller
from server import ServerLogics
from server import FileLogics
# from server.logics.datamodel import session
from server.logics.datamodel import create_session


parser = argparse.ArgumentParser()
parser.add_argument('-v', '--debug', action='count', default=0)
parser.add_argument('database', nargs='?', default='./server.database')
parser.add_argument('bind', nargs='?', default='tcp://*:5556')
parser.add_argument('storage', nargs='?', default='./storage/')
args = parser.parse_args()

if not os.path.exists(args.storage):
    os.makedirs(os.path.abspath(os.path.normpath(args.storage)))

c = Controller(create_session(args.database))
f = FileLogics(args.storage)
l = ServerLogics(c, f)
s = ServerWorker(l, args.bind, debug=args.debug)
s.main_loop()