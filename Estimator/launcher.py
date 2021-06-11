# -*- coding: utf-8 -*-
#
#  Copyright 2021 Timur Gimadiev <timur.gimadiev@gmail.com>
#  Copyright 2021 Ramil Nugmanov <nougmanoff@protonmail.com>
#  This file is part of Reaction Feasibility Estimator.
#
#  Reaction Feasibility Estimator is free software; you can redistribute it and/or modify
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
from queue import Empty
from redis import Redis
from rq import Queue as RQueue
from time import sleep, monotonic
from CGRtools import smiles
from .utilities import best_conformers, FailReport
from collections import namedtuple
from time import time

ReactionComponents = namedtuple('ReactionComponents',
                                ['index', 'smi', 'reactants', 'products', 'energy_dif', 'comments', 'time_s'])


def spent_time(start):
    return time()-start


def run(index, smi=None, **kwargs):
    """
    perform calculations for one reaction
    :param index:
        index of the reaction, to keep tracking initial order of tasks
    :param smi:
        Reaction SMILES
    :param crest_speed:
        speed and precision of CREST calculations, possible options :
        - quick
        - squick
        - mquick (default for this project)
    :param dft:
        define to perform
    :return:
        ReactionComponents named tuple
    """
    start = time()
    print(smi)
    if smi:
        reaction = smiles(smi)
    else:
        # TO DO: accept RDF as alternative
        raise NotImplemented
    # TO DO: add check for reaction container
    if reaction:
        if not reaction.reactants:
            return ReactionComponents(index, smi, None, None, None, 'problem: with reactants', spent_time(start))
        elif not reaction.products:
            return ReactionComponents(index, smi, None, None, None, 'problem: with products', spent_time(start))
        else:
            reactants = best_conformers(reaction.reactants, **kwargs)
            if not reactants:
                return ReactionComponents(index, smi, None, None, None,
                                          'anomaly terminated calculations for one of reactants', spent_time(start))
            elif any(isinstance(x, FailReport) for x in reactants):
                return ReactionComponents(index, smi, reactants, None, None,
                                          'anomaly terminated calculations for one of reactants', spent_time(start))
            products = best_conformers(reaction.products, **kwargs)
            if not products:
                ReactionComponents(index, smi, None, None, None,
                                   'anomaly terminated calculations for one of products', spent_time(start))
            elif any(isinstance(x, FailReport) for x in products):
                return ReactionComponents(index, smi, reactants, products, None,
                                          'anomaly terminated calculations for one of products', spent_time(start))
            try:
                energy_dif = sum([x.min_energy for x in products]) - sum([x.min_energy for x in reactants])
            except TypeError:
                return ReactionComponents(index, smi, reactants, products,
                                          None, 'min energy read error', spent_time(start))
            return ReactionComponents(index, smi, reactants, products,
                                      energy_dif, 'terminated normally', spent_time(start))
    else:
        return ReactionComponents(index, smi, None, None, None, 'problem: reaction smiles empty or incorrect',
                                  spent_time(start))


def worker(queue_in, queue_out):
    """
    multiprocess worker.

    :param queue_in: queue of jobs. if None received worker will be killed
    :param queue_out: queue of results of job.
    """
    for job in iter(queue_in.get, None):
        res = run(*job)
        queue_out.put(index=res.index, result=res)


def rq_worker(index, **kwargs):
    res = run(index, **kwargs)
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

    def put(self, index, result_ttl=3600, job_timeout=3600, **kwargs):
        self.queue.enqueue(rq_worker, index, **kwargs, job_timeout=job_timeout, result_ttl=result_ttl)

    def get(self, block=True, timeout=None, *, _sleep=2):
        if block:
            if timeout is None:
                while True:
                    ids = self.registry.get_job_ids(end=0)
                    if ids:
                        job = self.queue.fetch_job(ids[0])
                        res = job.result
                        job.delete()
                        return res
                    sleep(_sleep)
            else:
                deadline = monotonic() + timeout
                while True:
                    ids = self.registry.get_job_ids(end=0)
                    if ids:
                        job = self.queue.fetch_job(ids[0])
                        res = job.result
                        job.delete()
                        return res
                    sleep(_sleep)
                    if deadline < monotonic():
                        raise Empty
        else:
            ids = self.registry.get_job_ids(end=0)
            if ids:
                job = self.queue.fetch_job(ids[0])
                res = job.result
                job.delete()
                return res
            raise Empty


__all__ = ['launch', 'rq_launch', 'ReactionComponents', 'run']