import os
import mysql.connector

db_user = os.environ['SAYING_DB_USER']
db_passwd = os.environ['SAYING_DB_PASS']
db_host = os.environ['SAYING_DB_HOST']
db_port = 6033
db_db = os.environ['SAYING_DB_NAME']

def GetSingleRandQuote():

    cnx = mysql.connector.connect(user=db_user, password=db_passwd,
                              host=db_host,
                              database=db_db,port=db_port)
    q_string = ('SELECT quote from sayings order by RAND() limit 1')
    cur = cnx.cursor()
    cur.execute(q_string)
    quote = cur.fetchone()
    cur.close()
    cnx.close()
    quote_t = quote[0]
    # quote_t = quote[0]['quote']
    return (quote_t)