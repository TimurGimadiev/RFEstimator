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
from.launcher import rq_launch
from redis import Redis
import shelve


def listener(host='redis', filename='/data/results.shelve'):
    qin, qout = rq_launch(Redis(host=host))
    with shelve.open(filename) as w:
        while True:
            try:
                data = qout.get()
            except AttributeError:
                print("qout.get() error met")
                continue
            #print(data)
            w[str(data.index)] = data


if __name__ == "__main__":
    listener(host='redis', filename='/data/results.shelve')

__all__ = ['listener']
