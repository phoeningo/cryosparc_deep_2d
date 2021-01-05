## ---------------------------------------------------------------------------
##    Copyright (c) 2019 Structura Biotechnology Inc. All rights reserved. 
##         Do not reproduce or redistribute, in whole or in part.
##      Use of this code is permitted only under licence from Structura.
##                   Contact us at info@structura.bio.
## ---------------------------------------------------------------------------

# ----------------------- AUTO VERSION ------------------------------------------

# Job register. This module maintains the list of available jobs and their builders.
#
# A registered job is:
# a builder class (already imported)
# a module name and function name for importing and running the job
#
# Each job module therefore is laid out like:
# module_name/
#   __init__.py : imports jobregister and the builders and registers
#   build.py    : define the builders for jobs in this module (name not strict)
#   run.py      : a module (could be a dir with __init__) that contains a run function
#                 or more than one. Imports all runtime deps that are not needed at
#                 build time, and actually does all the work. Could be more than one.
#                 The run module might actually be a .so file if precompiled.
#                 The run function has a predefined call signature.



import os
import sys
import inspect
import importlib
import common


# This is the predefined order for UI. Contains all jobs, even those that don't exist yet.
job_sections = [
    {'name' : 'kf',
     'title' : 'Kongfang Packages',
     'description' : 'useful tools.',
     'contains' : [ 
                    'single_select',
                  ]
    },
    {'name' : 'import',
     'title' : 'Imports',
     'description' : 'useful description.',
     'contains' : [ 
                    'import_movies',
                    'import_micrographs',
                    'import_particles',
                    'import_volumes',
                    'import_templates',
                    'import_result_group',
                  ]
    },
    {'name' : 'motion_correction',
     'title' : 'Motion Correction',
     'description' : 'useful description.',
     'contains' : [
                    'rigid_motion_correction',
                    'rigid_motion_correction_multi',
                    'patch_motion_correction_multi',
                    'local_motion_correction',
                    'local_motion_correction_multi',
                    'motion_correction_motioncor2',
                  ]
    },
    {'name' : 'ctf_estimation',
     'title' : 'CTF Estimation',
     'description' : 'useful description.',
     'contains' : [
                    'patch_ctf_estimation_multi',
                    'patch_ctf_extract',
                    'ctf_estimation',
                    'sample_stats_estimation',
                    'ctf_estimation_gctf'
                  ]
    },
    {'name' : 'exposure_curation',
     'title' : 'Exposure Curation',
     'description' : 'useful description.',
     'contains' : [
                    'curate_exposures',
                  ]
    },
    {'name' : 'particle_picking',
     'title' : 'Particle Picking',
     'description' : 'useful description.',
     'contains' : [
                    'manual_picker',
                    'blob_picker_gpu',
                    'template_picker_gpu',
                    'inspect_picks',
                    'inspect_simple',
                    'extract_micrographs_multi',
                    'extract_micrographs',
                    'extract_micrographs_single',
                    'downsample_particles',
                    'extract_movies',
                    'deep_auto_picker',
                    'semiauto_picker',
                    'wrap_gautomatch',
                    'wrap_relion_autopick',
                  ]
    },
    {'name' : 'deep_picker',
     'title' : 'Deep Picker',
     'description' : 'useful description.',
     'contains' : [
                    'topaz_train',
                    'topaz_cross_validation',
                    'topaz_extract',
                    'topaz_denoise',
                    'topaz_particle_convert_dev', # Develop only / not used
                    'create_neg_stain_mics_dev', # Developer only / not used
                  ]
    },
    {'name' : 'particle_curation',
     'title' : 'Particle Curation',
     'description' : 'useful description.',
     'contains' : [
                    'class_2D',
                    'select_2D',
                    'class_probability_filter',
                    'deep_generative_outlier_reject',
                    'reference_based_outlier_reject',
                    'manual_curate_particles',
                    'random_phase_classify',
                    'clean_3D',
                    'create_templates'
                  ]
    },
    {'name' : 'reconstruction',
     'title' : '3D Reconstruction',
     'description' : 'useful description.',
     'contains' : [
                    'homo_abinit',
                    'hetero_abinit',
                    'hetero_search'
                  ]
    },
    {'name' : 'refinement',
     'title' : '3D Refinement',
     'description' : 'useful description.',
     'contains' : [
                    'homo_refine',
                    'homo_refine_new',
                    'hetero_refine',
                    'nonuniform_refine',
                    'clean_refine',
                  ]
    },
    {'name' : 'ctf_refinement',
     'title' : 'CTF Refinement',
     'description' : 'useful description.',
     'contains' : [
                    'ctf_refine_global',
                    'ctf_refine_local',
                    'exposure_groups',
                  ]
    },
    {'name' : 'variability',
     'title' : 'Variability',
     'description' : 'useful description.',
     'contains' : [
                    'var_3D',
                    'var_3D_disp',
                  ]
    },
    {'name' : 'postprocessing',
     'title' : 'Postprocessing',
     'description' : 'useful description.',
     'contains' : [
                    'local_resolution',
                    'local_filter',
                    'align_3D',
                    'reslog',
                    'fsc3D',
                    'phenix_sharpen'
                  ]
    },
    {'name' : 'local_refinement',
     'title' : 'Local Refinement (BETA)',
     'description' : 'useful description.',
     'contains' : [
                    'draw_masks',
                    'create_masks',
                    'naive_local_refine',
                    'particle_subtract',
                    'naice_local_classify',
                    'two_body_refine',
                    'multi_part_refine',
                  ]
    },
    {'name' : 'utilities',
     'title' : 'Utilities',
     'description' : 'Useful utilities to aid in processing.',
     'contains' : [
                    'volume_tools',
                    'sharpen',
                    'validation',
                    'particle_sets',
                    'exposure_sets',
                    'sym_expand',
                    'generate_thumbs',
                    'exposure_tools',
                    'cache_particles',
                  ]
    },
    {'name' : 'simulations',
     'title' : 'Simulations',
     'description' : 'Simulate experimental data.',
     'contains' : [
                    'simulator',
                  ]
    },
    {'name' : 'streaming',
     'title' : 'Streaming (Live)',
     'description' : 'Jobs for cryoSPARC Live',
     'contains' : [
                    'live_session',
                    'rtp_worker',
                    'class_2D_streaming',
                    'homo_refine_streaming',
                  ]
    },

]

# this is info about the jobs by name. Only registered jobs show up here.
job_types_info = {}
# this is build/run info about the jobs by name
job_types_modules = {}

def register(job_type, 
             title, shorttitle, desc, develop_only,
             builder_class, run_module_name, run_function_name,
             is_interactive = False):
    b = builder_class(common.create_blank_job())
    b.initialize_params_and_inputs()
    job_types_info[job_type] = {
        'name'         : job_type,
        'title'        : title,
        'shorttitle'   : shorttitle,
        'description'  : desc,
        'develop_only' : develop_only,
        'is_interactive' : is_interactive,
        'input_slot_groups' : b['input_slot_groups'][:],
    }
    job_types_modules[job_type] = {
        'builder'      : builder_class,    # imported builder class that is a subclass of bc.builderbase
        'run_module'   : run_module_name,  # name of a run module
        'run_function' : run_function_name # name of the run function in run module
    }

def check_all_job_modules(walk=False):
    """ Walk through subdirs of this module and try to import them. The __init__ in each will register it. 
    By default, don't walk - just directly import the submodules listed. We can bring back walk when we need 
    plugin architecture. """
    if walk:
        global job_types_info, job_types_modules
        job_types_info = {}
        job_types_modules = {}
        jobs_mod_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        all_submods = [path for path in os.listdir(jobs_mod_dir) if os.path.isdir(os.path.join(jobs_mod_dir, path))]
        for submod in all_submods:
            print "Locating availabile job types..."
            print "  importing", submod, "..."
            try:
                job_module = importlib.import_module(".."+submod, __name__)
                register(**job_module.register()) # even if imported before
            except Exception as e:
                print "  Failed to import ", submod
                print e
    else:
        import imports
        import abinit
        import refine
        import local_resolution
        import class2D
        import testjob
        import local_filter
        import nonuniform_refine
        import reslog
        import align_3D
        import template_picker_gpu
        import ctf
        import select2D
        import manual_picker
        import motioncorrection
        import extract
        import hetero_refine
        import workflows
        import curate_exposures
        import fsc3D
        import local_refine
        # import phenix_sharpen
        import utilities
        import simulator
        import rtp_workers
        import ctf_estimation
        import create_templates
        import var3D
        import topaz
        import ctf_refinement
        import class_probability_filter
        import single_select

def list_job_types():
    return sorted(job_types_info.keys())

def get_available_job_info():
    """ returns a denormalized structure with the sections and their info, plus the jobs and their info """
    struct = []
    for sec in job_sections:
        secinfo = sec.copy()
        secinfo['contains'] = []
        for jobname in sec['contains']:
            if jobname in job_types_info:
                secinfo['contains'].append(job_types_info[jobname])
        if len(secinfo['contains']) > 0:
            struct.append(secinfo)
    return struct

def job_type_exists(job_type):
    return job_type in job_types_modules

def get_builder(job_type):
    return job_types_modules[str(job_type)]['builder']

def get_run_function(job_type):
    modname = job_types_modules[str(job_type)]['run_module']
    funcname = job_types_modules[str(job_type)]['run_function']
    print modname, __name__
    sys.stdout.flush()
    runmod = importlib.import_module(".."+modname, __name__)
    runfunc = getattr(runmod, funcname)
    return runfunc
