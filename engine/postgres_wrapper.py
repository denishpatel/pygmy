import psycopg2
import logging
logger = logging.getLogger(__name__)


class PostgresData:
    """
    Interact with postgres data using DB host and password
    """
    def __init__(self, DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT=5432, expect_errors=False):
        try:
            logger.debug(f"Connecting to Postgres {DB_HOST}/{DB_NAME}")
            if DB_USER and DB_PASS:
                self.conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
            else:
                # Assume libpq will do the needful to find a working username and password, such as with pgpass
                self.conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, port=DB_PORT)
            self.cursor = self.conn.cursor()
        except Exception as e:
            if expect_errors == False:
                logger.error("ERROR: Cannot connect to the postgres db!")
                logger.exception(e)
                raise e
            else:
                logger.info(f"Got not-unexpected error connecting to {DB_HOST}/{DB_NAME}")
                raise e

    def execute_and_return_data(self, query, expect_errors=False):
        if expect_errors == True and self is None:
            return None

        try:
            result = []
            self.cursor.execute(query)
            raw = self.cursor.fetchall()

            for line in raw:
                result.append(line)
            return result
        except Exception as e:
            if self.conn.closed() == False:
                self.conn.close()
            if expect_errors == False:
                logger.exception(e)
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

    def is_alive(self, expect_errors=False):
        """
        A simple check for service
        """
        query = "SELECT 1"
        try:
            result = self.execute_and_return_data(query, expect_errors)[0][0]
            return (str(result) == "1")
        except psycopg2.InterfaceError:
            logger.info(f"Replica not accepting connections: {e}")
            return False
        except Exception as e:
            logger.info(f"Replica doesn't seem to be ready yet: {e}")
            return False

    def get_replication_lag(self):
        """
        Return replication lag in seconds
        ONLY to be hit on REPLICA
        """
        query = "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::INT replica_lag_in_seconds"
        return self.execute_and_return_data(query)[0][0]

    def get_streaming_status(self):
        """
        Return streaming status
        ONLY to be hit on REPLICA
        """
        query = "select status from pg_stat_wal_receiver"
        result = self.execute_and_return_data(query)
        if len(result)==0:
            logger.error("Found no streaming data on replica! Is this replica configured for streaming?")
            return False
        else:
            logger.debug("Result of get streaming status: " + str(result[0][0]))
            return (str(result[0][0]) == "streaming")

    def get_system_load_avg(self):
        """
        Return avg system load in last 15 mins if available
        else return last 10 mins load
        """
        query = "SELECT * FROM pg_sys_load_avg_info()"
        result = self.execute_and_return_data(query)[0][2]
        logger.debug("Result of get system avg load: " + str(result))
        return result

    def count_all_active_connections(self):
        """
        Return number of active connections
        """
        query = "select datname,usename,application_name,state,count(*) as connection_count from pg_stat_activity "\
                "where datname !='postgres' group by 1,2,3,4;"
        result = self.execute_and_return_data(query)
        logger.debug("Result of count all active connections: " + str(result))
        if len(result) > 0:
            return result[0][4]
        else:
            return 0

    def count_specific_active_connections(self, usernames):
        """
        Count user connections for specific users
        """
        user_list = list(map(lambda x: "usename like '{}'".format(x), usernames))
        user_query = " or ".join(user_list)

        query = "SELECT count(*) FROM pg_stat_activity WHERE state in ('active', 'idle in transaction') AND ({})".format(user_query)
        logger.debug("Query for user open connections: " + str(query))

        result = self.execute_and_return_data(query)
        logger.debug("Result of get user open connections: " + str(result))
        if len(result) > 0:
            return result[0][0]
        else:
            return 0

    def close(self):
        self.cursor.close()
        self.conn.close()
