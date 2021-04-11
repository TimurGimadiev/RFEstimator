# -*- coding: utf-8 -*-
#
#  Copyright 2021 Timur Gimadiev <timur.gimadiev@gmail.com>
#  Copyright 2021 Ramil Nugmanov <nougmanoff@protonmail.com>
#  This file is part of OrcaLauncher.
#
#  OrcaLauncher is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <https://www.gnu.org/licenses/>.
#
from .launcher import rq_launch
from redis import Redis
import time
import bigjson
import shelve

keys = ["smi", "crest_speed", "DFT_functional", "DFT_basis"]


def dispatcher(filename, host='redis', queued_tasks=100, queue_check_time=5, job_timeout=24*60*60, result_ttl=24*60*60):
    with open(filename, 'rb') as f, open("/data/loading.logs", "w") as log:
        j = bigjson.load(f)
        qin, qout = rq_launch(Redis(host=host))
        qin.queue.empty()  # reset previous queue
        log.write("number of tasks loaded to queue")
        for n, i in enumerate(j, start=1):  # put tasks into queue
            if not n % queued_tasks:
                log.write(f"{n}\n")
            if n % queued_tasks == 0:
                print("started tasks", n)
            while queued_tasks < qin.queue.count:
                time.sleep(queue_check_time)
            qin.put(**dict(i), index=n, job_timeout=job_timeout, result_ttl=result_ttl)
        log.write(f"""Loading to queue complete, dispatcher stops at this point,\n
                still there are about {qin.queue.count} tasks in Redis queue""")


if __name__ == "__main__":
    dispatcher("/data/input.json")


__all__ = ["dispatcher"]
