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
from subprocess import PIPE, run
from os import devnull
from CGRtools import SDFWrite
from CGRtools.files._mdl.mol import common_isotopes

#isinstance()

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
from collections import namedtuple
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

calc_result = namedtuple('calc_result', ['data', 'min_energy', 'log'])
atom2numbers = {v: k for k, v in enumerate(common_isotopes, 1)}
numbers2atom = {k: v for k, v in enumerate(common_isotopes, 1)}


def best_conformers(molecules, **kwargs):
    dft = kwargs.get("dft", None)
    result = []
    for n, mol in enumerate(molecules):
        tdir = Path(mkdtemp(prefix='calculation_'))
        tmp = best_conf(mol, tdir, **kwargs)
        if dft:
            tmp = refine_dft(mol, calc_result=tmp, tdir=tdir, **kwargs)
        rmtree(tdir)
        if tmp:
            result.append(tmp)
        else:
            return


def best_conf(molecule, tdir, **kwargs):
    log = kwargs.get("log")
    obabel_fast = kwargs.get("obabel_fast")
    crest_speed = kwargs.get("crest_speed", "mquick")
    multiplicity = 1  # multiplicity fixed for now, no radicals welcome
    charge = int(molecule)
    with SDFWrite(f'{tdir}/molecule.sdf') as f:
        f.write(molecule)
    # 3D coordinates generation
    if obabel_fast:
        # just do it
        task = ['obabel', '-isdf', f'{tdir}/molecule.sdf', '-oxyz', '--gen3d', 'fast']
    else:
        # just do it more carefully
        task = ['obabel', '-isdf', f'{tdir}/molecule.sdf', '-oxyz', '--gen3d']
    with open(devnull, 'w') as silent:
        p = run(task, stdout=PIPE, stderr=silent, cwd=tdir, text=True)
    with open(f'{tdir }/molecule.xyz', "w") as f:
        for i in p.stdout:
            f.write(i)
    with open(devnull, 'w') as silent:
        p = run(['/opt/crest', f'{tdir}/molecule.xyz', f"--T", "1", f"--{crest_speed}",
                 f"--scratch {tdir}/molecule.xyz", "--chrg", f"{charge}", "--uhf", f"{multiplicity}"], stdout=PIPE,
                stderr=silent, cwd=tdir, text=True)
        lines = p.stdout.splitlines()
    if lines[-1] == ' CREST terminated normally.':
        # print(lines[-18])
        flag = False
        min_energy = None
        try:
            min_energy = float(lines[-18].split(':')[1])  # different precision to one read from crest_best.xyz
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


def refine_dft(molecule, calc_result=None, **kwargs):
    dft = kwargs.get('dft', 'priroda')
    log = kwargs.get('log')
    tdir = kwargs.get('tdir', "/tmp/")
    multiplicity = 1  # multiplicity fixed for now, no radicals welcome
    charge = int(molecule)
    if calc_result:
        if dft.lower() == 'priroda':
            refine_priroda(charge, multiplicity, calc_result, tdir=tdir, log=log)
        elif dft.lower() == 'pyscf':
            refine_pyscf(calc_result)
    else:
        raise NotImplemented

def refine_pyscf(calc_result):
    from pyscf import gto, dft
    from pyscf.geomopt.berny_solver import optimize
    mol = gto.M(atom="".join(calc_result.data[2:]), basis='cc-pVDZ')
    mf = dft.RKS(mol)
    mf.xcfun = "SCAN"
    mf.xc = ""
    mol_eq = optimize(mf)
    print(mol_eq.atom_coords())


def refine_priroda(charge, multiplicity, calc_result, tdir, log=None):
    if not tdir:
        tdir="/tmp/"
    coord = [str(atom2numbers[x[:2].strip()]) + " " + x[3:] for x in calc_result.data[2:-1]]
    priroda_input = f'''
    $system mem=1000 disk=-1000 path=/tmp $end
    $control
    task=optimize
    basis= /opt/priroda/basis/3z
    $end
    $grid accur=1e-8 $end
    $optimize
     steps=300
     tol=1e-5
     trust=0.5
    $end
    $molecule
     charge={charge} mult={multiplicity}
     cartesian
    {"    ".join(coord)}
    $end
    '''
    #print(priroda_input)
    with open(f'{tdir}/molecule.inp', "w") as w:
        w.write(priroda_input)
    with open(devnull, 'w') as silent:
        p = run(['/opt/priroda/mpiexec', '-np', '1', '/opt/priroda/p16', f'{tdir}/molecule.inp'], stdout=PIPE,
                stderr=silent, cwd="/tmp/", text=True)
    flag = False
    tmp = []
    for n, i in enumerate(p.stdout.splitlines()):
        if not flag and i.startswith(' OPTIMIZATION CONVERGED'):
            flag = True
        if flag and i.startswith('MOL>'):
            tmp.append(i[5:])
    else:
        if not flag:
            #print(p.stdout.splitlines())
            return
    # coord = tmp[3:-2]
    at_count = len(coord)
    energy = float(tmp[-2].split("=")[1])
    coord = [numbers2atom[int(x.lstrip()[:3].strip())]+x.lstrip()[3:] for x in tmp[3:-2]]
    coord.insert(0, "\n")
    coord.insert(0, f"{at_count}\n")
    if log:
        return calc_result(coord, energy, p.stdout.splitlines())
    else:
        return calc_result(coord, energy, None)


__all__ = ['best_conf']