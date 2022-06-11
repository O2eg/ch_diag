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
from pkg_resources import parse_version as version


CH_DIAG_VERSION = '0.7'


class TaskQueue:
    tasks = queue.Queue()
    tasks_result = []


class SysConf:
    def __init__(self, args):
        self.current_dir = os.path.dirname(os.path.realpath(__file__))
        self.args = args
        self.cluster_version = None

        if args.certfile == '' and args.keyfile == '' and args.ca_certs == '':
            self.conn_params = {
                "host": args.host,
                "database": args.database,
                "port": args.port,
                "user": args.user,
                "password": args.password
            }
        if args.certfile != '' and args.keyfile != '':
            self.conn_params = {
                "host": args.host,
                "database": args.database,
                "port": args.port,
                "user": args.user,
                "password": args.password,
                # "ssl_version": 3,
                "verify": True,
                # "ciphers": 'HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5',
                "keyfile": args.keyfile,
                "certfile": args.certfile,
                "secure": True
            }
        if args.ca_certs != '':
            self.conn_params = {
                "host": args.host,
                "database": args.database,
                "port": args.port,
                "user": args.user,
                "password": args.password,
                # "ssl_version": 3,
                "verify": False,
                # "ciphers": 'HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5',
                "ca_certs": args.ca_certs,
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
                e1.NetworkError
        ) as e:
            if task is not None:
                task_queue.tasks.put(task)
            print('%s: %s' % (thread_name, str(e)))
            time.sleep(1.0)
        except Exception as e:
            print('Unhandled exception in %s, %s: %s' % (thread_name, task[0], str(e)))
            task_queue.tasks_result.append([task[0], [["Exception", "String"]], [[str(e)]]])

    print('================> Finished %s' % thread_name)


def get_specific_sql(cluster_version, items):
    for item in items:
        if item[1] == '+':
            item[1] = '100'

    for item in items:
        if version(item[0]) <= cluster_version < version(item[1]):
            return item[2]


def build_report_for_cluster(conf, cluster_name, report_struct, threads_num=1):
    task_queue = TaskQueue()
    databases = None

    if databases is None:
        client = Client(**conf.conn_params)
        dbs = client.execute("""
            select
                name
            from clusterAllReplicas(%s, system.databases)
            where name not in ('INFORMATION_SCHEMA', 'information_schema')
            group by name""" % cluster_name
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
                            for report_item_k, report_item_v in report_i_v.items():
                                if report_item_k == 'report_sql':
                                    sql_file = None
                                    if isinstance(report_item_v, list):
                                        sql_file = get_specific_sql(conf.cluster_version, report_item_v)
                                    if isinstance(report_item_v, str):
                                        sql_file = report_item_v

                                    with open(os.path.join(conf.current_dir, 'sql', section_k, sql_file)) as f:
                                        sql = f.read()
                                    sql = sql.replace('_CLUSTER_NAME', cluster_name)
                                    sql = sql.replace('_DB_NAMES', databases)
                                    task_queue.tasks.put([report_item_v, sql])

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

    report_struct["header"] += " [%s]" % cluster_name

    for k, v in report_struct.items():
        if k == 'sections':
            for section_k, section_v in v.items():
                for report_k, report_v in section_v.items():
                    if report_k == 'reports':
                        for report_i_k, report_i_v in report_v.items():
                            for report_item_k, report_item_v in list(report_i_v.items()):
                                if report_item_k == 'report_sql':
                                    # =========================================
                                    for tr in task_queue.tasks_result:
                                        if tr[0] == report_item_v:
                                            report_i_v["result"] = [tr[1], tr[2]]
                                            break

    report_result = json.dumps(report_struct, default=str, indent=4)
    with open(os.path.join(conf.current_dir, 'template', 'report.html'), 'r') as f:
        data = f.read()

    if args.use_ts_in_output_file_name:
        report_file_name = "report_" + cluster_name + "_" + str(datetime.now().timestamp()).split('.')[0] + ".html"
    else:
        report_file_name = "report_" + cluster_name + ".html"

    output_file_name = os.path.join(conf.current_dir, 'output', report_file_name)
    with open(output_file_name, 'w') as f:
        data = data.replace('_REPORT_DATA', report_result)
        f.write(data)

    print("Report saved to " + output_file_name)


def build_reports(conf):

    for v in ['output']:
        if not os.path.exists(os.path.join(conf.current_dir, v)):
            os.makedirs(os.path.join(conf.current_dir, v))

    with open(os.path.join(conf.current_dir, 'sql', 'report_struct.json')) as f:
        data = f.read()
    report_struct = json.loads(data)

    clusters = []
    client = Client(**conf.conn_params)

    conf.cluster_version = version(client.execute("select version()")[0][0])

    if conf.args.cluster_name == 'AUTO':
        clusters_res = client.execute(
            """
                select cluster, count(1) as cnt
                from system.clusters
                group by cluster
                order by cnt desc
                limit 1
            """
        )
        clusters = [v[0] for v in clusters_res]
    elif conf.args.cluster_name == 'ALL':
        clusters_res = client.execute(
            """
                select cluster
                from system.clusters
                group by cluster
            """
        )
        clusters = [v[0] for v in clusters_res]
    else:
        clusters.append(conf.args.cluster_name)

    for cluster in clusters:
        build_report_for_cluster(conf, cluster, report_struct, threads_num=1)


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
        "--ca-certs",
        type=str,
        default=''
    )
    parser.add_argument(
        "--cluster-name",
        type=str,
        help="Select specific cluster or AUTO or ALL (default: %(default)s)",
        default='AUTO'
    )
    parser.add_argument(
        "--use-ts-in-output-file-name",
        action='store_true',
        default=False
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

    build_reports(SysConf(args))
