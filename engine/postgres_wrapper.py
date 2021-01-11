import psycopg2
import logging
logger = logging.getLogger(__name__)


class PostgresData:
    """
    Interact with postgres data using DB host and password
    """
    def __init__(self, DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT=5432):
        try:
            self.conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
            self.cursor = self.conn.cursor()
        except Exception as e:
            logger.error("ERROR: Cannot connect to the postgres!!")
            logger.exception(e)
            raise e

    def execute_and_return_data(self, query):
        try:
            result = []
            self.cursor.execute(query)
            raw = self.cursor.fetchall()

            for line in raw:
                result.append(line)
            return result
        except Exception as e:
            logger.exception(e)
            self.conn.close()
            raise e

    def execute_command(self, query, params):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
        except Exception as e:
            logger.exception(e)
            self.conn.close()
            raise e

    def is_ec2_postgres_instance_primary(self):
        """
        Hit the postgres query and find out if that
        postgres instance is primary or secondary
        """
        try:
            query = "select pg_is_in_recovery()"
            resp = self.execute_and_return_data(query)
            # in recovery means its a backup server
            # or a read replica
            if resp[0][0]:
                return False
            return True
        except Exception as e:
            logger.exception(e)
            self.conn.close()
            raise e

    def get_all_slave_servers(self):
        """
        Hit the postgres query to find out all the slave
        server IP addresses
        """
        try:
            query = "select * from pg_stat_replication"
            all_ips = []
            for x in self.execute_and_return_data(query):
                all_ips.append(x[4])
            return all_ips
        except Exception as e:
            logger.exception(e)
            self.conn.close()
            raise e

    def get_replication_lag(self):
        """
        TODO Ask about this ?
        """
        pass

    def close(self):
        self.cursor.close()
        self.conn.close()
