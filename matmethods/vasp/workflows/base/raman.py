# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

"""
This module defines the workflow to compute the Raman susceptibility tensor.
"""

from fireworks import Firework, Workflow

from matmethods.utils.utils import get_logger
from matmethods.vasp.fireworks.core import OptimizeFW, LepsFW
from matmethods.vasp.firetasks.parse_outputs import RamanSusceptibilityTensorToDbTask

from pymatgen.io.vasp.sets import MPRelaxSet

__author__ = 'Kiran Mathew'
__email__ = 'kmathew@lbl.gov'

logger = get_logger(__name__)


def get_wf_raman_spectra(structure, modes=None, step_size=0.005, vasp_cmd="vasp", db_file=None):
    """
    Raman susceptibility tensor workflow:
        Calculation of phonon normal modes followed by the computation of dielectric tensor for
        structures displaced along the normal modes. Finally the dielectric tensors corresponding
        to each mode are used to compute the Raman susceptibility tensor using finite difference(
        central difference scheme).

    Args:
        structure (Structure): Input structure.
        modes (tuple/list): list of modes for which the Raman spectra need to be calculated.
            The default is to use all the 3N modes.
        step_size (float): site displacement along the normal mode in Angstroms. Used to compute
            the finite difference(central difference scheme) first derivative of the dielectric
            constant along the normal modes.
        vasp_cmd (str): vasp command to run.
        db_file (str): path to file containing the database credentials.

    Returns:
        Workflow
    """
    modes = modes or range(3*len(structure))
    vis = MPRelaxSet(structure, force_gamma=True)
    # displacements in + and - direction along the normal mode so that the central difference scheme
    # can be used for the evaluation of Raman tensor (derivative of epsilon wrt displacement)
    displacements = [-step_size, step_size]

    fws = []

    # Structure optimization
    fw_opt = OptimizeFW(structure=structure, vasp_input_set=vis,  ediffg=-0.05, vasp_cmd=vasp_cmd,
                        db_file=db_file)
    fws.append(fw_opt)

    # Static run: compute the normal modes and pass
    fw_leps = LepsFW(structure=structure, vasp_cmd=vasp_cmd, db_file=db_file, parents=fw_opt, phonon=True)
    fws.append(fw_leps)

    # Static runs to compute epsilon for each mode and displacement along that mode.
    fws_nm_disp = []
    for mode in modes:
        for disp in displacements:
            fws_nm_disp.append(LepsFW(structure, parents=fw_leps, vasp_cmd=vasp_cmd, db_file=db_file,
                                      phonon=True, mode=mode, displacement=disp))
    fws.extend(fws_nm_disp)

    # Compute the Raman susceptibility tensor
    fw_analysis = Firework(RamanSusceptibilityTensorToDbTask(db_file=db_file), parents=fws_nm_disp,
                           name="{}-{}".format(structure.composition.reduced_formula, "raman analysis"))
    fws.append(fw_analysis)

    wfname = "{}:{}".format(structure.composition.reduced_formula, "raman spectra")
    return Workflow(fws, name=wfname)


if __name__ == "__main__":
    from pymatgen.util.testing import PymatgenTest

    Si = PymatgenTest.get_structure("Si")
    wf = get_wf_raman_spectra(Si)
