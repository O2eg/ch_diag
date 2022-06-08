import sys
from clickhouse_driver import connect
from clickhouse_driver import Client
import threading
import time
import queue
from datetime import datetime
from clickhouse_driver import errors as e1
from clickhouse_driver.dbapi import errors as e2
import json
import os
import argparse


CH_DIAG_VERSION = '0.1'


class TaskQueue:
    tasks = queue.Queue()
    tasks_result = []


class SysConf:
    def __init__(self, args):
        self.current_dir = os.path.dirname(os.path.realpath(__file__))
        self.args = args

        if args.keyfile == '':
            self.conn_params = {
                "host": args.host,
                "database": args.database,
                "port": args.port,
                "user": args.user,
                "password": args.password
            }
        else:
            self.conn_params = {
                "host": args.host,
                "database": args.database,
                "port": args.port,
                "user": args.user,
                "password": args.password,
                "ssl_version": 3,
                "verify": True,
                "ciphers": 'HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5',
                "keyfile": args.keyfile,
                "certfile": args.certfile,
                "secure": True
            }


def worker_func(thread_name, conf, task_queue):
    print('================> Started %s' % thread_name)

    do_work = True
    task = None
    while do_work:
        try:
            task = None
            with connect(**conf.conn_params) as conn:
                while not task_queue.tasks.empty():
                    task = task_queue.tasks.get()
                    columns = None
                    with conn.cursor() as cursor:
                        cursor.execute(task[1])
                        columns = cursor.columns_with_types
                        res = cursor.fetchall()
                    task_queue.tasks_result.append([task[0], columns, res])
                do_work = False
        except (
                EOFError,
                ConnectionAbortedError,
                e1.NetworkError,
                e2.OperationalError
        ) as e:
            if task is not None:
                task_queue.tasks.put(task)
            print('%s: %s' % (thread_name, str(e)))
            time.sleep(1.0)
        except Exception as e:
            # if task is not None:
            #    tasks.put(task)
            print('Unhandled exception in %s: %s' % (thread_name, str(e)))
            time.sleep(1.0)

    print('================> Finished %s' % thread_name)


def build_report(conf, threads_num=1):
    task_queue = TaskQueue()

    with open(os.path.join(conf.current_dir, 'sql', 'report_struct.json')) as f:
        data = f.read()
    report_struct = json.loads(data)

    databases = None

    if databases is None:
        client = Client(**conf.conn_params)
        dbs = client.execute("""
            select
                database
            from clusterAllReplicas(%s, system.databases)
            where database not in ('INFORMATION_SCHEMA', 'information_schema')
            group by database""" % conf.args.cluster_name
        )
        databases = ", ".join(['\'%s\'' % d[0] for d in dbs])

    for k, v in report_struct.items():
        if k == 'description':
            now = datetime.now()

            report_struct['description'] = '<b>Collecting datetime:</b> %s, <b>ch_diag version:</b> %s %s' % (
                now.strftime("%d/%m/%Y %H:%M:%S"),
                CH_DIAG_VERSION,
                "<br><br>" + "".join(
                    [k + " = " + str(v) + "<br>" for k, v in conf.conn_params.items() if k not in ('user', 'password')]
                ) if conf.args.add_params_to_report else ""
            )
        if k == 'sections':
            for section_k, section_v in v.items():
                for report_k, report_v in section_v.items():
                    if report_k == 'reports':
                        for report_i_k, report_i_v in report_v.items():
                            for report_ii_k, report_ii_v in report_i_v.items():
                                if report_ii_k == 'report_sql':
                                    with open(os.path.join(conf.current_dir, 'sql', report_ii_v)) as f:
                                        sql = f.read()
                                    sql = sql.replace('_CLUSTER_NAME', conf.args.cluster_name)
                                    sql = sql.replace('_DB_NAMES', databases)
                                    task_queue.tasks.put([report_ii_v, sql])

    worker_threads = []

    for t_num in range(1, threads_num + 1):
        worker_threads.append(
            threading.Thread(
                target=worker_func,
                args=["thread_%s" % str(t_num), conf, task_queue]
            )
        )
    for thread in worker_threads:
        thread.start()

    alive_count = 1
    live_iteration = 0

    while alive_count > 0:
        alive_count = len([thread for thread in worker_threads if thread.is_alive()])
        if alive_count == 0:
            break
        time.sleep(0.5)
        if live_iteration % (20 * 3) == 0:
            print('Live %s threads' % alive_count)
        live_iteration += 1

    for k, v in report_struct.items():
        if k == 'sections':
            for section_k, section_v in v.items():
                for report_k, report_v in section_v.items():
                    if report_k == 'reports':
                        for report_i_k, report_i_v in report_v.items():
                            for report_ii_k, report_ii_v in list(report_i_v.items()):
                                if report_ii_k == 'report_sql':
                                    # =========================================
                                    for tr in task_queue.tasks_result:
                                        if tr[0] == report_ii_v:
                                            report_i_v["result"] = [tr[1], tr[2]]
                                            break

    report_result = json.dumps(report_struct, default=str, indent=4)
    with open(os.path.join(conf.current_dir, 'template', 'report.html'), 'r') as f:
        data = f.read()
    with open(os.path.join(conf.current_dir, 'output', 'report.html'), 'w') as f:
        data = data.replace('_REPORT_DATA', report_result)
        f.write(data)

    print("Report saved to " + os.path.join(conf.current_dir, 'output', 'report.html'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        help="Show the version number and exit",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "--debug",
        help="Enable debug mode, (default: %(default)s)",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "--add-params-to-report",
        action='store_true',
        default=False
    )
    parser.add_argument(
        "--host",
        type=str,
        default='127.0.0.1'
    )
    parser.add_argument(
        "--port",
        type=str,
        default='9010'
    )
    parser.add_argument(
        "--database",
        type=str,
        default='default'
    )
    parser.add_argument(
        "--user",
        type=str,
        default='default'
    )
    parser.add_argument(
        "--password",
        type=str,
        default='default'
    )
    parser.add_argument(
        "--keyfile",
        type=str,
        default=''
    )
    parser.add_argument(
        "--certfile",
        type=str,
        default=''
    )
    parser.add_argument(
        "--cluster-name",
        type=str,
        default='test_cluster'
    )

    args = parser.parse_args()
    debug_mode = args.debug

    dt = datetime.now().isoformat(' ')
    if debug_mode:
        print('%s %s started' % (dt, os.path.basename(__file__)))
        print("#--------------- Incoming parameters")
        for arg in vars(args):
            print("#   %s = %s" % (arg, getattr(args, arg)))
        print("#-----------------------------------")

    if args.version:
        print("Version %s" % CH_DIAG_VERSION)
        sys.exit(0)

    build_report(SysConf(args), threads_num=1)




