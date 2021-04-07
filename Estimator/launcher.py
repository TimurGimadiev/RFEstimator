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
from collections import deque
from multiprocessing import Process, Queue
from pathlib import Path
from queue import Empty
from redis import Redis
from rq import Queue as RQueue
from shutil import rmtree
from tempfile import mkdtemp
from time import sleep, monotonic
from pyscf import gto, scf
from pyscf.geomopt.berny_solver import optimize
from CGRtools import smiles
from .utilities import best_conf
from collections import namedtuple
from time import time

ReactionComponents = namedtuple('ReactionComponents',
                                ['reactants', 'products', 'energy_dif', 'comments', 'time_s'])

def spend_time(start):
    return time()-start

def run(task, options=None, program='/opt/crest'):
    start = time()
    smi = task  #TO DO: accept RDF as alternative
    reaction = smiles(smi)
    # TO DO: add check for reaction container
    if reaction:
        if not reaction.reactants:
            return ReactionComponents(None, None, None, 'problem: with reactants', spend_time(start))
        elif not reaction.products:
            return ReactionComponents(None, None, None, 'problem: with products', spend_time(start))
        else:
            reactants = []
            products = []
            for n, mol in enumerate(reaction.reactants):
                tdir = Path(mkdtemp(prefix='calculation_'))
                tmp = best_conf(mol, tdir)
                rmtree(tdir)
                if tmp:
                    reactants.append(tmp)
                else:
                    return ReactionComponents(None, None, None, f'anomaly terminated calculations for reactant {n}'
                                              , spend_time(start))
            for n, mol in enumerate(reaction.products):
                tdir = Path(mkdtemp(prefix='calculation_'))
                tmp = best_conf(mol, tdir)
                rmtree(tdir)
                if tmp:
                    products.append(tmp)
                else:
                    return ReactionComponents(None, None, None, f'anomaly terminated calculations for product {n}'
                                              , spend_time(start))
            energy_dif = sum([x[1] for x in products]) - sum([x[1] for x in reactants])
            result = ReactionComponents(reactants, products, energy_dif, 'terminated normally', spend_time(start))
            return result
    else:
        return ReactionComponents(None, None, None, 'problem: reaction smiles empty or incorrect', spend_time(start))



def worker(queue_in, queue_out):
    """
    multiprocess worker.

    :param queue_in: queue of jobs. if None received worker will be killed
    :param queue_out: queue of results of job.
    """
    for job in iter(queue_in.get, None):
        for res in run(*job):
            queue_out.put(res)


def rq_worker(job):
    res = list(run(*job))
    return res


def launch(n_proc):
    """
    launch worker processes.

    :param n_proc: number of workers
    :return: input and output queues for jobs and results
    """
    queue_in, queue_out = Queue(), Queue()

    for _ in range(n_proc):  # start workers
        p = Process(target=worker, args=(queue_in, queue_out))
        p.start()
    return queue_in, queue_out


def rq_launch(redis: Redis, *, name='default'):
    """
    get redis workers queues

    :param redis: redis connection
    :param name: queue name
    :return: input and output queues for jobs and results. Note: these queues is same object.
    """
    q = RQueueWrapper(RQueue(name=name, connection=redis))
    return q, q


class RQueueWrapper:
    def __init__(self, queue: RQueue):
        self.queue = queue
        self.registry = queue.finished_job_registry
        self.buffer = deque()

    def qsize(self):
        """
        number of jobs in queue
        """
        return len(self.registry)

    def put(self, job, *, result_ttl=3600, job_timeout=3600):
        self.queue.enqueue(rq_worker, job, job_timeout=job_timeout, result_ttl=result_ttl)

    def get(self, block=True, timeout=None, *, _sleep=2):
        if self.buffer:
            return self.buffer.popleft()
        if block:
            if timeout is None:
                while True:
                    ids = self.registry.get_job_ids(end=0)
                    if ids:
                        job = self.queue.fetch_job(ids[0])
                        res = job.result
                        job.delete()
                        if len(res) > 1:
                            self.buffer.extend(res[1:])
                            return res[0]
                        elif res:
                            return res[0]
                    sleep(_sleep)
            else:
                deadline = monotonic() + timeout
                while True:
                    ids = self.registry.get_job_ids(end=0)
                    if ids:
                        job = self.queue.fetch_job(ids[0])
                        res = job.result
                        job.delete()
                        if len(res) > 1:
                            self.buffer.extend(res[1:])
                            return res[0]
                        elif res:
                            return res[0]
                    sleep(_sleep)
                    if deadline < monotonic():
                        raise Empty
        else:
            ids = self.registry.get_job_ids(end=0)
            if ids:
                job = self.queue.fetch_job(ids[0])
                res = job.result
                job.delete()
                if len(res) > 1:
                    self.buffer.extend(res[1:])
                    return res[0]
                elif res:
                    return res[0]
            raise Empty


__all__ = ['launch', 'rq_launch', 'ReactionComponents', 'run']