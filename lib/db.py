import logging
import sqlite3
import traceback

from lib import Registry


class DBException(Exception):
    def __init__(self, message, *args):
        self.message = message
        super().__init__(*args)

    def __str__(self):
        return "%s: %s" % (self.__class__, self.message)


class DB:

    def __init__(self):
        self._closed = True
        self._intransaction = False
        #Registry.dbs.append(self)

    def open(self):
        self._sql = sqlite3.connect(Registry.cfg.db)
        self._c = self._sql.cursor()
        self._c.execute("PRAGMA busy_timeout=1000")
        self._closed = False

    def begin(self):
        if self._closed:
            self.open()
        self._c.execute("BEGIN")
        self._intransaction = True

    def commit(self):
        self._c.execute("COMMIT")
        self._intransaction = False
        self.close()

    def execute(self, sql, close=True, select=False):
        if self._closed:
            self.open()
        if select:
            logging.getLogger("db").debug("SELECT(close=%s): %s" % (close, sql))
        else:
            logging.getLogger("db").debug("EXECUTE(close=%s): %s" % (close, sql))
        err = ""
        for i in range(1, 6):
            try:
                data = self._c.execute(sql)
                if not self._intransaction and close:
                    self.close()
                return data
            except sqlite3.OperationalError as e:
                err = str(e)
                logging.getLogger("db").error(e)
                pass
        self.close()
        raise DBException(err)

    def select(self, sql):
        rows = []
        data = self.execute(sql, close=False, select=True)
        for row in data:
            rows.append(row)
        self.close()
        return rows

    def close(self):
        if not self._closed:
            self._c.close()
            self._closed = True

    def create_schema(self):
        self.execute("""
            CREATE table IF NOT EXISTS vdp (
              id varchar NOT NULL PRIMARY KEY,
              version varchar,
              revision bigint,
              tpe varchar,
              data text,
              deleted bool,
              my bool,
              readonly bool,
              expiry int,
              ttl int
            )""")
        self.execute("""
            CREATE table IF NOT EXISTS sessions (
              id varchar NOT NULL PRIMARY KEY,
              data text,
              activated bigint,
              created bigint,
              expires bigint,
              paymentid varchar,
              paid bool,
              gateid varchar,
              spaceid varchar,
              parent varchar,
              price float,
              deleted bool
            )""")

    @classmethod
    def cmp_str_attr(cls, attr, value):
        return 'data LIKE \'%%"%s": "%s"%%\'' % (attr, value)

    @classmethod
    def cmp_number_attr(cls, attr, value):
        return 'data LIKE \'%%"%s": %s%%\'' % (attr, value)

    @classmethod
    def cmp_bool_attr(cls, attr):
        return 'data LIKE \'%%"%s": true%%\'' % attr

    @classmethod
    def parse_ands(cls, ands):
        if len(ands) == 0:
            return ""
        else:
            return " AND " + " AND ".join(ands)

    def __del__(self):
        if not self._closed:
            raise DBException("Unclosed DB handle!")
        else:
            #Registry.dbs.remove(self)
            pass

    def __repr__(self):
        if self._closed:
            state = "closed"
        else:
            state = "OPENED"
        return "DB:[%s, %s]" % (state, self._c)

