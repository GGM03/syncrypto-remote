#!/usr/bin/python

import argparse
import time
import os
import shutil

from client import Syncrypto
from client import ClientWorker
from client import Crypto
from protocol.sockets import secure_user_connection
from protocol.hashing import checksum_chain

def run(args):
    secure = secure_user_connection(args.server, debug=args.debug)
    password = checksum_chain([args.username, args.password])
    u = ClientWorker.from_creds(secure, args.username, password)
    if not u.is_logged:
        print('Error loggin!')
        exit(-1)
    c = Crypto(password)
    s = Syncrypto(u, c, args.folder, debug=args.debug)
    return s

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i',"--init", help="Init syncrypto files for synchronization", action='store_true')
    parser.add_argument('-r',"--register", help="Register user", action='store_true')
    parser.add_argument('-u',"--username", help="Username")
    parser.add_argument('-p',"--password", help="Password")
    parser.add_argument('-v', '--debug', action='count', default=0)
    parser.add_argument('-o',"--once", help="Run sync only once", action='store_true', default=False)
    parser.add_argument('-d',"--delay", help="Delay between syncs", default=5)
    parser.add_argument('-s',"--server", help="Addres of server", default='tcp://127.0.0.1')
    parser.add_argument('folder', nargs='?', default=None)

    args = parser.parse_args()

    if not args.folder and not args.register:
        print('Pleas specify folder to sync!')
        exit(0)

    if not args.username:
        args.username = input('Username: ')

    if not args.password:
        import getpass
        args.password = getpass.getpass(prompt='Password: ')

    if args.register:
        # secure = secure_user_connection(args.server, debug=True if args.debug else False)
        secure = secure_user_connection(args.server, debug=args.debug)
        u = ClientWorker.from_registration(secure, args.username, checksum_chain([args.username, args.password]))
        user_inf = u.get_info()
        # if not u.is_logged:
        #     print('Registration falied!')
        #     exit(-1)
        # else:
        print(user_inf)
        exit()

    if not os.path.exists(os.path.join(args.folder, '.syncrypto')) and not args.init:
        print('Please, initalize folder for synchronization.\n'
              'Run app with key "-i"')
        exit()

    if args.init:
        args.folder =  os.path.normpath(os.path.abspath(args.folder))
        syn_path = os.path.join(args.folder, '.syncrypto')
        if os.path.exists(syn_path):
            remove = input('Folder initalized before! Destroy root? [Yn]')
            if remove in ['N','n','н','Н']:
                exit()
            else:
                shutil.rmtree(syn_path)

        s = run(args)
        s.sync_folder()
        print('Folder initalized!')
        exit()

    else:
        s = run(args)
        if args.once:
            s.sync_folder()
            exit()

        while True:
            s.sync_folder()
            time.sleep(int(args.delay))

            # user = 'zloy'
    # password = 'helloworld'
    #
    # secure = secure_user_connection('tcp://127.0.0.1')
    # u = ClientWorker.from_registration(secure, user, checksum_chain([user, password]))
    # c = Crypto(password)
    # s = Syncrypto(u, c, '/home/zloy/PycharmProjects/syncrypto/tmp/plain', debug=2)
    # s.sync_folder()

    # import time
    # while True:
    #     s.sync_folder()
    # # s.retry_sync_folder(3)
    # time.sleep(2)

