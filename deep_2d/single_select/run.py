## ---------------------------------------------------------------------------
##    Copyright (c) 2019 Structura Biotechnology Inc. All rights reserved. 
##         Do not reproduce or redistribute, in whole or in part.
##      Use of this code is permitted only under licence from Structura.
##                   Contact us at info@structura.bio.
## ---------------------------------------------------------------------------

# This is a self contained Flask app.
# interactive job
#   threaded so each request can do blocking IO or compute as needed
#   number of concurrent requests should be small enough that 1 thread per request is okay
#

from builtins import str
import os, sys
from flask import Flask, request
import json
import datetime
import logging

import socket
from threading import RLock

app = Flask('single_select')
locks = {'test' : RLock() }

# This disables logging for every HTTP request.
# Flask will still automatically log when there are errors, but JSONRPC won't.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

import numpy as n
from .. import runcommon as rc

from ...blobio import mrc
from ... import plotutil

from ... import particles

cli = rc.cli
_job = None

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, n.integer):
            return int(obj)
        elif isinstance(obj, n.floating):
            if not n.isfinite(obj):
                return float(0.0)
            return float(obj)
        elif isinstance(obj, n.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)

def extern(func):
    def wrapper(*args, **kwargs):
        kwargs.update(request.get_json(force=True))
        res = func(*args, **kwargs)
        return json.dumps(res, cls=NumpyEncoder)
    wrapper.__name__ = func.__name__
    return app.route('/'+func.__name__, methods=['POST'])(wrapper)

# ============================================================================

state = {}

def run(job):
    global _job
    _job = job
    print("INTERACTIVE JOB STARTED === ", datetime.datetime.now(), " ==========================")
    sys.stdout.flush()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    cli.update_job(job['project_uid'], job['uid'], {
        'interactive_port' : port
        })

    # get job info
    proj_dir_abs = rc.get_project_dir_abs()
    job_dir_rel = job['job_dir']
    job_dir_abs = os.path.join(proj_dir_abs, job_dir_rel)
    puid = job['project_uid']
    juid = job['uid']

    # load params
    params = rc.com.get_merged_params(job)
    
    # load inputs
    templates_dset = rc.load_input_group(input_group_name='templates', slot_names=['blob']) 
    rc.log('Loaded info for %d classes ' % (len(templates_dset)))
    template_classes = templates_dset.data['blob/idx']
    
    has_particles = rc.com.is_input_slot_connected(job, 'particles', 'blob')
    if has_particles:
        particles_dset = rc.load_input_group(input_group_name='particles', slot_names=['blob', 'alignments2D']) 
        num_particles = len(particles_dset)
        rc.log('Loaded info for %d particles' % (num_particles))
        class_assignments = particles_dset.data['alignments2D/class']

    all_mrcs = list(set(templates_dset.data['blob/path']))
    assert len(all_mrcs) == 1, "Templates in multiple MRC not supported yet"
    mrc_path_abs = os.path.join(proj_dir_abs, all_mrcs[0])
    _, template_mrc = mrc.read_mrc(mrc_path_abs)
    template_mrc = template_mrc[templates_dset.data['blob/idx']] # slice out only the indicated ones
    
    if params['transpose_templates']:
        # go back to C order from accidental F-order
        template_mrc = template_mrc.ravel().reshape(template_mrc.shape, order='F')
    
    # upload all images of templates ahead of time
    template_imgs_stringio = plotutil.plot_2D_classes_return_images(template_mrc)
    template_imgs_fileid = { class_idx : str(rc.upload_file(template_imgs_stringio[index], filename="class2D_%d.png" % class_idx)) for index, class_idx in enumerate(template_classes) }

    if has_particles:
        class_info = [ {
            'class_idx' : class_idx,
            'fileid' : template_imgs_fileid[class_idx],
            'selected' : False,
            'num_particles_total' : n.sum(class_assignments==class_idx),
            'num_particles_selected' : 0,
            'res_A' : templates_dset.data['blob/res_A'][index],
            'mean_prob' : n.mean(particles_dset.data['alignments2D/class_posterior'][class_assignments==class_idx]),
            'class_ess' : n.mean(particles_dset.data['alignments2D/class_ess'][class_assignments==class_idx])
            } 
        for index, class_idx in enumerate(template_classes) ]
        prob_thresh = 0.0 # default to taking all matches
        prob_hist_data, prob_hist_bins = n.histogram(particles_dset.data['alignments2D/class_posterior'], 100, range=(0,1))
        prob_sum_data = num_particles - n.cumsum(prob_hist_data)
    else:
        class_info = [ {
            'class_idx' : class_idx,
            'fileid' : template_imgs_fileid[class_idx],
            'selected' : False,
            'num_particles_total' : 0,
            'num_particles_selected' : 0,
            'res_A' : templates_dset.data['blob/res_A'][index],
            'mean_prob' : 1,
            'class_ess' : 0
            } 
        for index, class_idx in enumerate(template_classes) ]

    state.update(locals())

    has_res_threshold = params['class_idx'] is not None
    has_count_threshold = params['particle_count_above'] is not None

    if params['selected_templates']:
        cli.set_job_status(job['project_uid'], job['uid'], 'running')
        selected_idxs = [int(v) for v in params['selected_templates'].strip().split(',')]
        for temp in class_info:
            temp['selected'] = temp['class_idx'] in selected_idxs
    elif has_res_threshold or has_count_threshold:
        rc.log("Threshold parameters are set- skipping interactive web server")
        rc.log("This output was added by kongfang for test ++++++++++++++++++++++++++++++++++++++++++")
        cli.set_job_status(job['project_uid'], job['uid'], 'running')
        if has_res_threshold and has_count_threshold:
            for class_dict in class_info:
                rc.log(class_dict)
                if (class_dict['class_idx']==params['class_idx']) and (class_dict['num_particles_total'] > params['particle_count_above']) :
                    class_dict['selected']=True
    '''
    else:
        rc.log('Interactive job running on port %d' % port)
        cli.set_job_status(job['project_uid'], job['uid'], 'waiting')
        app.run(host="0.0.0.0", port=port, threaded=False)
        cli.set_job_status(job['project_uid'], job['uid'], 'running')
    '''    
    
    rc.log('Outputting selection..')
    # Finish and make outputs code
    templates_selection_state = n.array([v['class_idx'] for v in class_info if v['selected']])
    templates_selection_mask = n.in1d(templates_dset.data['blob/idx'], templates_selection_state)
    templates_include_idx = n.where(templates_selection_mask)[0]
    templates_exclude_idx = n.where(~templates_selection_mask)[0]
    templates_dset_include = templates_dset.subset_idxs(templates_include_idx)
    templates_dset_exclude = templates_dset.subset_idxs(templates_exclude_idx)
    rc.log('Templates selected : %d' % (len(templates_dset_include)))
    rc.log('Templates excluded : %d' % (len(templates_dset_exclude)))

    if len(templates_include_idx) > 0:
        outpath_rel = os.path.join(job_dir_rel, 'templates_selected.cs')
        templates_dset_include.filter_prefix('blob').to_file(os.path.join(proj_dir_abs, outpath_rel))
        rc.output('templates_selected', 'blob', outpath_rel, 0, len(templates_dset_include))
        
        fig = plotutil.plot_2D_classes(template_mrc[templates_include_idx],
                                    rows = int(n.ceil(len(templates_include_idx) / 10.0)), cols = 10,
                                    figsize_each=1.0)
        rc.log_plot(fig, 'Selected %d classes:' % len(templates_include_idx))

        figgroup = plotutil.plot_2D_classes(template_mrc[templates_include_idx],
                                    rows = 3, cols = 3,
                                    figsize_each=0.6)
        rc.set_output_group_image('templates_selected', figgroup)
        
        figtile = plotutil.plot_2D_classes(template_mrc[templates_include_idx],
                                    rows = 3, cols = 6,
                                    figsize_each=0.6)
        
        if len(template_mrc[templates_include_idx]) == 1:                            
            rc.set_tile_image('templates_selected', figtile, 1, 1)
        else:
            rc.set_tile_image('templates_selected', figtile, 1, 2)

    if len(templates_exclude_idx) > 0:
        outpath_rel = os.path.join(job_dir_rel, 'templates_excluded.cs')
        templates_dset_exclude.filter_prefix('blob').to_file(os.path.join(proj_dir_abs, outpath_rel))
        rc.output('templates_excluded', 'blob', outpath_rel, 0, len(templates_dset_exclude))
        
        fig = plotutil.plot_2D_classes(template_mrc[templates_exclude_idx],
                                        rows = int(n.ceil(len(templates_exclude_idx) / 10.0)), cols = 10,
                                        figsize_each=1.0)
        rc.log_plot(fig, 'Excluded %d classes:' % len(templates_exclude_idx))

        figgroup = plotutil.plot_2D_classes(template_mrc[templates_exclude_idx],
                                       rows = 3, cols = 3,
                                       figsize_each=0.6)
        rc.set_output_group_image('templates_excluded', figgroup)

    if has_particles:
        particle_selection_mask = n.in1d(particles_dset.data['alignments2D/class'], templates_selection_state)
        particle_selection_mask = n.logical_and(particle_selection_mask, particles_dset.data['alignments2D/class_posterior'] > prob_thresh)
        particle_include_idxs = n.where(particle_selection_mask)[0]
        particle_exclude_idxs = n.where(~particle_selection_mask)[0]
        particles_dset_include = particles_dset.subset_idxs(particle_include_idxs)
        particles_dset_exclude = particles_dset.subset_idxs(particle_exclude_idxs)
        rc.log('Particles selected : %d' % (len(particles_dset_include)))
        rc.log('Particles excluded : %d' % (len(particles_dset_exclude)))
    
        if len(particle_include_idxs) > 0:
            outpath_rel = os.path.join(job_dir_rel, 'particles_selected.cs')
            particles_dset_include.filter_prefixes(['blob', 'alignments2D']).to_file(os.path.join(proj_dir_abs, outpath_rel))
            rc.output('particles_selected', 'blob', outpath_rel, 0, len(particles_dset_include))
            rc.output('particles_selected', 'alignments2D', outpath_rel, 0, len(particles_dset_include))

            pset = particles.ParticleStack()
            pset.init(particles_dset_include.subset_range(0,9))
            pset.read_blobs(proj_dir_abs, do_cache=False)
            particle_data = [p.get_original_real_data() for p in pset.get_items()]
            
            fig_group_included = plotutil.plot_images_simple(particle_data, rows=3, cols=3, radwn=6, figscale=0.6)
            rc.set_output_group_image('particles_selected', fig_group_included)

        if len(particle_exclude_idxs) > 0:
            outpath_rel = os.path.join(job_dir_rel, 'particles_excluded.cs')
            particles_dset_exclude.filter_prefixes(['blob', 'alignments2D']).to_file(os.path.join(proj_dir_abs, outpath_rel))
            rc.output('particles_excluded', 'blob', outpath_rel, 0, len(particles_dset_exclude))
            rc.output('particles_excluded', 'alignments2D', outpath_rel, 0, len(particles_dset_exclude))
            
            pset = particles.ParticleStack()
            pset.init(particles_dset_exclude.subset_range(0,9))
            pset.read_blobs(proj_dir_abs, do_cache=False)
            particle_data = [p.get_original_real_data() for p in pset.get_items()]

            fig_group_excluded = plotutil.plot_images_simple(particle_data, rows=3, cols=3, radwn=6, figscale=0.6)
            rc.set_output_group_image('particles_excluded', fig_group_excluded)

    rc.log('Done.')
    rc.log('Interactive backend shutting down.')

def update_class_num_selected(class_idx):
    num_selected = 0
    class_dict = get_class_info_idx(class_idx)
    if state['has_particles']:
        if class_dict['selected']:
            num_selected = n.sum(n.logical_and(state['particles_dset'].data['alignments2D/class'] == class_idx, state['particles_dset'].data['alignments2D/class_posterior'] > state['prob_thresh']))
        class_dict['num_particles_selected'] = num_selected
    
@extern
def select_all():
    for class_dict in state['class_info']:
        class_dict['selected'] = True
        update_class_num_selected(class_dict['class_idx'])
    return True

@extern
def select_none():
    for class_dict in state['class_info']:
        class_dict['selected'] = False
        update_class_num_selected(class_dict['class_idx'])
    return True

@extern
def select_invert():
    for class_dict in state['class_info']:
        class_dict['selected'] = not class_dict['selected']
        update_class_num_selected(class_dict['class_idx'])
    return True

@extern
def select_above(class_idx, dimension):
    compare = get_class_info_idx(class_idx)[dimension]
    for class_dict in state['class_info']:
        if class_dict[dimension] > compare:
           class_dict['selected'] = True
           update_class_num_selected(class_dict['class_idx'])
    return True

@extern
def select_below(class_idx, dimension):
    compare = get_class_info_idx(class_idx)[dimension]
    for class_dict in state['class_info']:
        if class_dict[dimension] < compare:
            class_dict['selected'] = True
            update_class_num_selected(class_dict['class_idx'])
    return True

@extern
def set_class_selected(class_idx, selected):
    get_class_info_idx(class_idx)['selected'] = selected
    update_class_num_selected(class_idx)
    return True

@extern
def set_prob_thresh(prob_thresh):
    assert prob_thresh >= 0.0 and prob_thresh <= 1.0
    state['prob_thresh'] = prob_thresh
    for class_idx in state['template_classes']:
        update_class_num_selected(class_idx)
    return True

@extern
def get_class_info(class_idx = None):
    if class_idx is None: 
        return state['class_info']

def get_class_info_idx(class_idx):
    for class_dict in state['class_info']:
        if class_dict['class_idx']==class_idx:
            return class_dict

@extern
def get_prob_thresh():
    return state['prob_thresh']
@extern
def get_hist_data():
    return {'prob_hist_data' : state['prob_hist_data'], 'prob_hist_bins' : state['prob_hist_bins'], 'prob_sum_data' : state['prob_sum_data'],}

@extern
def finish():
    request.environ.get('werkzeug.server.shutdown')()
    return True


# ============================================================================


