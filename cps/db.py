#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019 mutschler, cervinko, ok11, jkrehm, nanu-c, Wineliva,
#                            pjeby, elelay, idalin, Ozzieisaacs
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.
from sqlalchemy import *
from sqlalchemy.orm import *
import os
import re
import unidecode

from cps.models import ub, Base, Books
from cps.models.ub import config

session = None
cc_exceptions = ['datetime', 'comments', 'float', 'composite', 'series']
cc_classes = None
engine = None


# user defined sort function for calibre databases (Series, etc.)
def title_sort(title):
    # calibre sort stuff
    title_pat = re.compile(config.config_title_regex, re.IGNORECASE)
    match = title_pat.search(title)
    if match:
        prep = match.group(1)
        title = title.replace(prep, '') + ', ' + prep
    return title.strip()


def lcase(s):
    return unidecode.unidecode(s.lower())


def ucase(s):
    return s.upper()


def setup_db():
    global engine
    global session
    global cc_classes

    if config.config_calibre_dir is None or config.config_calibre_dir == u'':
        content = ub.session.query(ub.Settings).first()
        content.config_calibre_dir = None
        content.db_configured = False
        ub.session.commit()
        config.load_settings()
        return False

    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
    try:
        if not os.path.exists(dbpath):
            raise
        engine = create_engine('sqlite:///' + dbpath, echo=False, isolation_level="SERIALIZABLE",
                               connect_args={'check_same_thread': False})
        conn = engine.connect()
    except Exception:
        content = ub.session.query(ub.Settings).first()
        content.config_calibre_dir = None
        content.db_configured = False
        ub.session.commit()
        config.load_settings()
        return False
    content = ub.session.query(ub.Settings).first()
    content.db_configured = True
    ub.session.commit()
    config.load_settings()
    conn.connection.create_function('title_sort', 1, title_sort)

    if not cc_classes:
        cc = conn.execute("SELECT id, datatype FROM custom_columns")

        cc_ids = []
        books_custom_column_links = {}
        cc_classes = {}
        for row in cc:
            if row.datatype not in cc_exceptions:
                books_custom_column_links[row.id] = Table('books_custom_column_' + str(row.id) + '_link', Base.metadata,
                                                          Column('book', Integer, ForeignKey('books.id'),
                                                                 primary_key=True),
                                                          Column('value', Integer,
                                                                 ForeignKey('custom_column_' + str(row.id) + '.id'),
                                                                 primary_key=True)
                                                          )
                cc_ids.append([row.id, row.datatype])
                if row.datatype == 'bool':
                    ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                              'id': Column(Integer, primary_key=True),
                              'book': Column(Integer, ForeignKey('books.id')),
                              'value': Column(Boolean)}
                elif row.datatype == 'int':
                    ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                              'id': Column(Integer, primary_key=True),
                              'book': Column(Integer, ForeignKey('books.id')),
                              'value': Column(Integer)}
                else:
                    ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                              'id': Column(Integer, primary_key=True),
                              'value': Column(String)}
                cc_classes[row.id] = type('Custom_Column_' + str(row.id), (Base,), ccdict)

        for cc_id in cc_ids:
            if (cc_id[1] == 'bool') or (cc_id[1] == 'int'):
                setattr(Books, 'custom_column_' + str(cc_id[0]), relationship(cc_classes[cc_id[0]],
                                                                              primaryjoin=(
                                                                                  Books.id == cc_classes[
                                                                                  cc_id[0]].book),
                                                                              backref='books'))
            else:
                setattr(Books, 'custom_column_' + str(cc_id[0]), relationship(cc_classes[cc_id[0]],
                                                                              secondary=books_custom_column_links[
                                                                                  cc_id[0]],
                                                                              backref='books'))

    Session = scoped_session(sessionmaker(autocommit=False,
                                          autoflush=False,
                                          bind=engine))
    session = Session()
    return True
