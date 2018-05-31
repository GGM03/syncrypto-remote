from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from datetime import datetime

from protocol import file_digest


DB_PATH = '/home/zloy/PycharmProjects/syncrypto/server.db'

meta = MetaData()
Base = declarative_base(metadata=meta)


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    xfiles = relationship("User", back_populates="files")

    # fils = relationship("User", back_populates='fils')
    path = Column(String, nullable=True)
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=True)
    checksum = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now())

    def __init__(self, filename):
        self.name = filename

    def __repr__(self):
        return "<File ({0} {1})>".format(self.name, sizeof_fmt(self.size))

    def update_from_file(self, filepath):
        self.path = os.path.normpath(filepath)
        self.size = os.path.getsize(self.path)
        self.checksum = file_digest(self.path)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    treefile = Column(String, nullable=False)
    token = Column(String, nullable=False)
    limit = Column(Integer, nullable=False, default=1073741824) #1 GB per user
    used = Column(Integer, nullable=False, default=0)
    files = relationship("File", order_by=File.id)


    def __init__(self, username, password, treefile, directory):
        self.name = username
        self.password = password
        self.treefile = treefile
        self.token = directory

    def __repr__(self):
        return "<User ({0}:{1}, {2}/{3})>".format(self.name, self.password, sizeof_fmt(self.used), sizeof_fmt(self.limit))


def create_session(db_path=DB_PATH):
    engine = create_engine('sqlite:///' + os.path.normpath(db_path), echo=False)
    meta.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


def init_db(db_path=DB_PATH):
    engine = create_engine('sqlite:///' + os.path.normpath(db_path), echo=False)
    meta.create_all(engine)


# session = create_session()

if __name__ == '__main__':
    pass
    # init_db()

    # session.add(User('1','2','3','4'))
    # session.commit()

    # u = session.query(User).filter(User.id==3).first()
    # u.files.append(File('/home/zloy/.fehbg'))
    # session.commit()

    d = session.query(File).filter(User.id==1).filter(User.files.any(File.name=='8e392809-8b52-4e77-8e1f-487c695a6681-a45048c531746b4ef6ad5746cf4e2396')).first()

    print(d)
    # print(d)
    # user = session.query(User).one()
    # print(user.files[0].timestamp)
    # user.files.append(File('/home/zloy/PycharmProjects/syncrypto/test1.py'))
    # session.commit()
    # print(session.query(User).one().files.append(File('/home/zloy/PycharmProjects/syncrypto/test2.py')))
    # session.commit()