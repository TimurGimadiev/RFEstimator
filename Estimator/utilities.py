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
from subprocess import Popen, PIPE, run
from os import devnull
from CGRtools import SDFWrite

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
from collections import namedtuple


calc_result = namedtuple('calc_result',
                                ['data', 'min_energy', 'log'])


def best_conf(molecule, tdir, crest_speed="mquick", log=False, obabel_fast=True):
    with SDFWrite(f'{tdir}/molecule.sdf') as f:
        f.write(molecule)
    # 3D coordinates generation
    # just do it
    if obabel_fast:
        task = ['obabel', '-isdf', f'{tdir}/molecule.sdf', '-oxyz', '--gen3d', 'fast']
    # just do it more carefully
    else:
        task = ['obabel', '-isdf', f'{tdir}/molecule.sdf', '-oxyz', '--gen3d']
    with open(devnull, 'w') as silent:
        p = run(task, stdout=PIPE, stderr=silent, cwd=tdir, text=True)
    with open(f'{tdir }/molecule.xyz', "w") as f:
        for i in p.stdout:
            f.write(i)
    with open(devnull, 'w') as silent:
        p = run(['/opt/crest', f'{tdir}/molecule.xyz', f"--T", "1", f"--{crest_speed}",
                 f"--scratch {tdir}/molecule.xyz"], stdout=PIPE, stderr=silent, cwd=tdir, text=True)
        lines = p.stdout.splitlines()
    if lines[-1] == ' CREST terminated normally.':
        print(lines[-18])
        flag = False
        min_energy = None
        try:
            min_energy = float(lines[-18].split(':')[1])
        except ValueError:
            flag = True
        with open(f'{tdir}/crest_best.xyz') as f:
            data = f.readlines()
        if flag:
            # ad-hoc for small molecules, first met on HBr, crest_best.xyz file looks different
            try:
                min_energy = float(data[1].split("energy:")[1].split()[0])
            except ValueError:
                print("Unexpected min energy value both in xyz and log")
        print(lines[-18].split(':')[1])
        print(data[1])
        if log:
            return calc_result(data, min_energy, lines)
        else:
            return calc_result(data, min_energy, None)
    else:
        return


__all__ = ['best_conf']
