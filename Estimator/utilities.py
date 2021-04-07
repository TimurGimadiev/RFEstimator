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


def best_conf(molecule, tdir):
    with SDFWrite(f'{tdir}/molecule.sdf') as f:
        f.write(molecule)
    with open(devnull, 'w') as silent:
        p = run(['obabel', '-isdf', f'{tdir }/molecule.sdf', '-oxyz', '--gen3d'],
                  stdout=PIPE, stderr=silent, cwd=tdir, text=True)
    with open(f'{tdir }/molecule.xyz', "w") as f:
        for i in p.stdout:
            #print(i)
            f.write(i)
    with open(devnull, 'w') as silent:
        p = run(['/opt/crest', f'{tdir}/molecule.xyz', f"--T", "1", "--mquick",  f"--scratch {tdir}/molecule.xyz"],
                  stdout=PIPE, stderr=silent, cwd=tdir, text=True)
        lines = p.stdout.splitlines()
    if lines[-1] == ' CREST terminated normally.':
        min_energy = float(lines[-18].split(":")[1])
        with open(f'{tdir}/crest_best.xyz') as f:
            data = f.readlines()
        return data, min_energy
    else:
        return


__all__ = ['best_conf']
