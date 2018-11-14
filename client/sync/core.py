#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015 Qing Liang (https://github.com/liangqing)
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from io import open
import os
import sys
import os.path
import shutil
import json
from datetime import datetime
# from time import sleep, time
# from lockfile.mkdirlockfile import MkdirLockFile as LockFile
# from random import randint
from stat import S_IWUSR, S_IRUSR


from client.sync.crypto import Crypto, DecryptError
from client.sync.filetree import FileTree, FileRuleSet, FileEntry
from protocol.utils import Logging
from protocol.hashing import checksum

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

from uuid import uuid4
class GenerateEncryptedFilePathError(Exception):
    pass


class ChangeTheSamePassword(Exception):
    pass


class InvalidFolder(Exception):
    pass


DEFAULT_RULES = b"""ignore: name eq .Trashes
ignore: name eq .fseventsd
ignore: name eq Thumb.db
ignore: name eq node_modules
ignore: name eq .sass-cache
ignore: name eq .idea
ignore: name eq .git
ignore: name eq .svn
ignore: name eq .hg
ignore: name eq .cvs
ignore: name match *.pyc
ignore: name match *.class
ignore: name match .*TemporaryItems
ignore: name match .*DS_Store
ignore: name match *.swp
ignore: name match *.swo"""

from pprint import pprint

class Syncrypto(Logging):

    def __init__(self, client, crypto, plain_folder,
                 plain_tree=None, snapshot_tree=None,
                 rule_set=None, rule_file=None, debug=False):

        super(Syncrypto, self).__init__('Syncrypto')

        self.client = client
        self.crypto = crypto
        self.plain_folder = plain_folder
        self.plain_tree = plain_tree
        self.snapshot_tree = snapshot_tree
        self.rule_set = rule_set

        if debug == 2:
            self._trees_debug = True
        else:
            self._trees_debug = False
        self._debug = debug

        self._encrypted_new = False
        self._trash_name = self._generate_trash_name()
        self._snapshot_tree_name = '.filetree'
        self._encrypted_filetree_entry = None

        if plain_folder is not None:
            if not os.path.isdir(self.plain_folder):
                if os.path.exists(self.plain_folder):
                    raise InvalidFolder(
                        "Plaintext folder path is not correct: " +
                        self.plain_folder)
                else:
                    os.makedirs(self.plain_folder)

            if self.rule_set is None:
                self.rule_set = FileRuleSet()

            if rule_file is None:
                rule_file = self._plain_rule_path()
                if not os.path.exists(rule_file):
                    with open(rule_file, "wb") as f:
                        f.write(DEFAULT_RULES)

            if os.path.exists(rule_file):
                with open(rule_file, 'rb') as f:
                    for line in f:
                        line = line.strip()
                        if line == b"" or line[0] == b'#':
                            continue
                        self.rule_set.add_rule_by_string(line.decode("ascii"))

    @staticmethod
    def _generate_trash_name():
        return datetime.now().isoformat().replace(':', '_')

    # def _generate_encrypted_path(self, encrypted_file):
    #     dirname, name = encrypted_file.split()
    #     digest = checksum(name)
    #     i = 2
    #     while True:
    #         if dirname == '':
    #             fs_pathname = digest[:i]
    #         else:
    #             parent = self.encrypted_tree.get(dirname)
    #             if parent is None:
    #                 self.error("Can not find file entry for %s" %
    #                            dirname)
    #                 raise GenerateEncryptedFilePathError()
    #             fs_pathname = parent.fs_pathname + '/' + digest[:i]
    #         if not self.encrypted_tree.has_fs_pathname(fs_pathname):
    #             encrypted_file.fs_pathname = fs_pathname
    #             return
    #         i += 1
    #     raise GenerateEncryptedFilePathError()

    def _generate_random_name(self, entry=None):
        rand = str(uuid4())
        if entry:
            if entry.digest:
                return rand + '-' + str(entry.digest.hex())
        return rand + '-' + checksum(rand)

    def _encrypt_file(self, pathname):
        plain_file = self.plain_tree.get(pathname)
        plain_path = plain_file.fs_path(self.plain_folder)
        encrypted_file = self.encrypted_tree.get(pathname)

        if not os.path.exists(plain_path):
            self.error("%s not exists!" % plain_path)
            return encrypted_file

        if encrypted_file is None:
            encrypted_file = plain_file.clone()
            if pathname.startswith(".syncrypto/"):
                encrypted_file.fs_pathname = '_'+plain_file.fs_pathname[1:]
            else:
                encrypted_file.fs_pathname = self._generate_random_name(encrypted_file)

        if plain_file.isdir:
            encrypted_file.copy_attr_from(plain_file)
            return encrypted_file

        else:
            encrypted_fd = self.client.post_file(encrypted_file.fs_pathname)
            plain_fd = open(plain_path, 'rb')
            # Encryption
            self.crypto.encrypt_fd(plain_fd, encrypted_fd, plain_file)
            plain_fd.close()
            encrypted_fd.close()
            return encrypted_file

    def _decrypt_file(self, pathname):
        encrypted_file = self.encrypted_tree.get(pathname)
        plain_file = self.plain_tree.get(pathname)
        if plain_file is None:
            plain_file = encrypted_file.clone()
            plain_file.fs_pathname = plain_file.pathname
        plain_path = plain_file.fs_path(self.plain_folder)
        mtime = encrypted_file.mtime

        if encrypted_file.isdir:
            if not os.path.exists(plain_path):
                os.makedirs(plain_path)
            if encrypted_file.mode is not None:
                os.chmod(plain_path, encrypted_file.mode | S_IWUSR | S_IRUSR)
            os.utime(plain_path, (mtime, mtime))
            plain_file.copy_attr_from(encrypted_file)
            # encrypted_file.close()
            return plain_file
        if os.path.exists(plain_path):
            self._delete_file(plain_file, False)

        directory = os.path.dirname(plain_path)
        if not os.path.isdir(directory):
            os.makedirs(directory)

        plain_fd = open(plain_path, 'wb')
        encrypted_fd = self.client.get_file(encrypted_file.fs_pathname)
        encr_buf = BytesIO(encrypted_fd.read())
        encrypted_fd.close()

        self.crypto.decrypt_fd(encr_buf, plain_fd)
        plain_file.copy_attr_from(encrypted_file)
        plain_fd.close()
        if encrypted_file.mode is not None:
            os.chmod(plain_path, encrypted_file.mode)
        os.utime(plain_path, (mtime, mtime))
        return plain_file

    @staticmethod
    def _conflict_path(path):
        dirname = os.path.dirname(path)
        filename = os.path.basename(path)
        dot_pos = filename.rfind(".")
        if dot_pos > 0:
            name = filename[:dot_pos]
            ext = filename[dot_pos:]
        else:
            name = filename
            ext = ""
        name += ".conflict"
        conflict_path = os.path.join(dirname, name+ext)
        i = 1
        if os.path.exists(conflict_path):
            conflict_path = \
                os.path.join(dirname, name+"."+str(i)+ext)
            i += 1
        return conflict_path

    def _is_ignore(self, plain_file, encrypted_file):
        return (self.rule_set.test(plain_file) != 'include' or
                self.rule_set.test(encrypted_file) != 'include')

    @staticmethod
    def _is_equal(file_entry, file_entry_compare):
        if file_entry is None or file_entry_compare is None:
            return False
        if file_entry.isdir and file_entry_compare.isdir:
            return True
        if file_entry.digest is not None \
                and file_entry_compare.digest is not None:
            return file_entry.digest == file_entry_compare.digest
        return \
            file_entry.size == file_entry_compare.size and \
            int(file_entry.mtime) == int(file_entry_compare.mtime)

    def _compare_file(self, encrypted_file, plain_file, snapshot_file):
        if self._is_ignore(plain_file, encrypted_file):
            return "ignore"
        if self._encrypted_new:
            return "encrypt"
        if self._is_equal(plain_file, encrypted_file):
            return 'same'
        plain_file_changed = not self._is_equal(plain_file, snapshot_file)
        encrypted_file_changed = not self._is_equal(encrypted_file,
                                                    snapshot_file)
        if plain_file is not None and encrypted_file is not None:
            if plain_file_changed and not encrypted_file_changed:
                return "encrypt"
            elif encrypted_file_changed and not plain_file_changed:
                return "decrypt"
            elif not encrypted_file_changed and not plain_file_changed:
                return "same"
            else:
                return 'conflict'
        elif plain_file is not None:
            if plain_file_changed:
                return "encrypt"
            else:
                return "remove plain"
        elif encrypted_file is not None:
            if encrypted_file_changed:
                return "decrypt"
            else:
                return "remove encrypted"
        return None

    def _plain_rule_path(self):
        return self._plain_folder_path("rules")

    def _snapshot_tree_path(self):
        return self._plain_folder_path('.filetree')

    def _plain_folder_path(self, sub_file):
        filename = ".syncrypto"
        path = os.path.join(self.plain_folder, filename, sub_file)
        self._ensure_dir(path)
        return path

    def _save_trees(self):
        self._save_encrypted_tree()
        self.debug('Encrypted tree sent to server')
        self._save_snapshot_tree()
        self.debug('Snapshot saved')

    def _save_encrypted_tree(self):
        fp = self.client.post_tree()
        tree_dict = self.encrypted_tree.to_dict()
        tree_dict["snapshot_tree_name"] = self._snapshot_tree_name
        self.crypto.encrypt_fd(BytesIO(json.dumps(tree_dict).encode("utf-8")),
                               fp, self._encrypted_filetree_entry,
                               Crypto.COMPRESS)
        fp.close()

    def _load_encrypted_tree(self):
        # TODO: Redifine to work with server
        tree = self.client.get_tree()
        if not tree:
            self.debug('Init new encrypted tree')
            self.encrypted_tree = FileTree()
            self._encrypted_new = True
            snapshot_tree_path = \
                os.path.join(self.plain_folder, ".syncrypto",
                             self._snapshot_tree_name)

            if not os.path.exists(snapshot_tree_path):
                self._snapshot_tree_name = '.filetree'

            print(snapshot_tree_path)
        else:
            try:
                tree_buf = BytesIO(tree.read())
                tree_fd = BytesIO()
                self._encrypted_filetree_entry = \
                    self.crypto.decrypt_fd(tree_buf, tree_fd)
                tree_fd.seek(0)
                tree_dict = json.loads(tree_fd.getvalue().decode("utf-8"))
                if "snapshot_tree_name" in tree_dict:
                    self._snapshot_tree_name = tree_dict["snapshot_tree_name"]
                self.encrypted_tree = FileTree.from_dict(tree_dict)
            finally:
                tree.close()

        if self._trees_debug:
            pprint(self.encrypted_tree.to_dict())

    def _save_snapshot_tree(self):
        # TODO: Redifine to send to server
        fp = open(self._snapshot_tree_path(), 'wb')
        snapshot_tree_dict = self.snapshot_tree.to_dict()
        self.crypto.compress_fd(
            BytesIO(json.dumps(snapshot_tree_dict).encode("utf-8")), fp)
        fp.close()

    def _load_plain_tree(self):
        self.plain_tree = FileTree.from_fs(self.plain_folder,
                                           rule_set=self.rule_set)
        if self._trees_debug:
            pprint(self.plain_tree.to_dict())


    def _load_snapshot_tree(self):
        snapshot_tree_path = self._snapshot_tree_path()
        if not os.path.exists(snapshot_tree_path):
            self.snapshot_tree = FileTree()
        else:
            fp = open(snapshot_tree_path, "rb")
            try:
                tree_fd = BytesIO()
                self.crypto.decompress_fd(fp, tree_fd)
                tree_fd.seek(0)
                snapshot_tree_dict = \
                    json.loads(tree_fd.getvalue().decode("utf-8"))
                self.snapshot_tree = FileTree.from_dict(snapshot_tree_dict)
            finally:
                fp.close()

        if self._trees_debug:
            pprint(self.snapshot_tree.to_dict())

    @staticmethod
    def _ensure_dir(path):
        target_dir = os.path.dirname(path)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)


    def _delete_file(self, pathname, is_in_encrypted_folder):
        tree, root, target = None, None, None
        if is_in_encrypted_folder:
            tree = self.encrypted_tree
            file_entry = tree.get(pathname)
            self._delete_encr(file_entry)
            self.info('Delete file {0} on encrypted drive'.format(file_entry))

        else:
            tree = self.plain_tree
            root = self.plain_folder
            file_entry = tree.get(pathname)

            fs_path = file_entry.fs_path(root)
            if os.path.isdir(fs_path):
                shutil.rmtree(fs_path)

            elif os.path.exists(fs_path):
                self._delete_plain(file_entry)
            self.info('Delete local file {0}'.format(file_entry))

        tree.remove(pathname)

    def _delete_encr(self, entry):
        self.client.delete_file(entry.fs_pathname)

    def _delete_plain(self, entry):
        path = entry.fs_path(self.plain_folder)
        os.remove(path)

    @staticmethod
    def _revise_folder(tree, root):
        for entry in tree.folders():
            fs_path = entry.fs_path(root)
            os.utime(fs_path, (entry.mtime, entry.mtime))

    def _do_sync_folder(self):

        if self.plain_folder is None:
            raise Exception("please specify the plaintext folder to sync files")

        pathnames = list(set(self.plain_tree.pathnames() +
                             self.encrypted_tree.pathnames()))
        pathnames.sort()
        encrypted_remove_list = []
        plain_remove_list = []
        ignore_prefix = None
        for pathname in pathnames:
            if ignore_prefix is not None \
                    and pathname.startswith(ignore_prefix):
                self.plain_tree.remove(pathname)
                self.encrypted_tree.remove(pathname)
            encrypted_file = self.encrypted_tree.get(pathname)
            plain_file = self.plain_tree.get(pathname)
            action = self._compare_file(encrypted_file, plain_file,
                                        self.snapshot_tree.get(pathname))

            self.debug('"{2}" : l:{0}/r:{1}'.format(encrypted_file, plain_file, action))
            if action == "remove encrypted":
                encrypted_remove_list.append(pathname)
            elif action == "remove plain":
                plain_remove_list.append(pathname)
            elif action == "encrypt":
                encrypted_file = self._encrypt_file(pathname)
                if encrypted_file is None:
                    continue
                self.encrypted_tree.set(pathname, encrypted_file)
                if not encrypted_file.isdir:
                    self.info("Encrypt {0} to {1}".format(plain_file.fs_pathname, encrypted_file.fs_pathname[:8]))

            elif action == "decrypt":
                plain_file = self._decrypt_file(pathname)
                if plain_file is None:
                    continue
                self.plain_tree.set(pathname, plain_file)
                if not plain_file.isdir:
                    self.info("Decrypt {0} to {1}".format(encrypted_file.fs_pathname[:8],plain_file.fs_pathname))
            elif action == "same":
                if not encrypted_file.isdir:
                    self.debug("{0} is not changed ".format(plain_file.fs_pathname))
            elif action == 'conflict':
                if plain_file.isdir and encrypted_file.isdir:
                    continue
                plain_path = plain_file.fs_path(self.plain_folder)
                shutil.move(plain_path, self._conflict_path(plain_path))
                if plain_file.isdir:
                    ignore_prefix = pathname
                plain_file = self._decrypt_file(pathname)
                self.plain_tree.set(pathname, plain_file)
                self.info("{0} has conflict!".format(plain_file.fs_pathname))
            elif action == 'ignore':
                if encrypted_file is not None:
                    encrypted_remove_list.append(pathname)
                if (plain_file is not None and plain_file.isdir) \
                        or \
                        (encrypted_file is not None and encrypted_file.isdir):
                    ignore_prefix = pathname+'/'

        for pathname in encrypted_remove_list:
            self._delete_file(pathname, True)
        for pathname in plain_remove_list:
            self._delete_file(pathname, False)

        self._revise_folder(self.plain_tree, self.plain_folder)
        self.snapshot_tree = self.encrypted_tree

        self._save_trees()
        self.info(("Finished sync for folder '%s'") % (
            self.plain_folder
        ))

    def retry_sync_folder(self, retries=3):
        for _ in range(0, 3):
            try:
                self.sync_folder()
            except Exception as e:
                self.critical('Catched on sync {0}'.format(e))
                continue
            else:
                break

    def sync_folder(self, reload_tree=True):
            if reload_tree:
                self.debug("Collecting remote tree")
                self._load_encrypted_tree()
                self.debug("Generating local tree")
                self._load_plain_tree()
                self.debug("Collecting snapshot tree")
                self._load_snapshot_tree()

            if self.snapshot_tree is None:
                self._load_snapshot_tree()

            self.debug("Processing sync")
            self._do_sync_folder()
