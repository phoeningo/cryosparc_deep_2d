## ---------------------------------------------------------------------------
##    Copyright (c) 2019 Structura Biotechnology Inc. All rights reserved. 
##         Do not reproduce or redistribute, in whole or in part.
##      Use of this code is permitted only under licence from Structura.
##                   Contact us at info@structura.bio.
## ---------------------------------------------------------------------------

from .. import buildcommon as bc

class builder(bc.builderbase):
    def initialize_params_and_inputs(job):
        """ required. all setup for this type """
        job['type'] = 'single_select' 
        job['run_on_master_direct'] = True
        job['interactive'] = True

        job.add_input_slot_group(name='particles', type='particle', count_min=0, count_max=1, title='Particles', desc='Particles')
        job.add_input_slot(name='blob', group_name='particles', type='particle.blob', title='Particle raw data')
        job.add_input_slot(name='alignments2D', group_name='particles', type='particle.alignments2D', title='Particle 2D alignments')
        job.add_input_slot_group(name='templates', type='template', count_min=1, count_max=1, title='2D Class Averages', desc='Class averages')
        job.add_input_slot(name='blob', group_name='templates', type='template.blob', title='Template raw data')
        
        job.param_add_section('general_settings', title='General Settings', desc='')
        job.param_add('general_settings', 'transpose_templates',            base_value=False,   title='Transpose templates',                                                param_type='boolean',   hidden=True,   advanced=True)
        job.param_add('general_settings', 'selected_templates',             base_value=None,    title='Selected templates (comma sep)',                                     param_type='string',    hidden=True,   advanced=True)
        
        job.param_add_section('settings', title='Auto Thresholds', desc='Automatically apply thresholds and skip the interactive process')
        job.param_add('settings', 'class_idx',          base_value=None,    title='Specific class id',       param_type='number',    hidden=False,   advanced=False)
        job.param_add('settings', 'particle_count_above',            base_value=None,    title='Classes where particle count higher than',   param_type='number',    hidden=False,   advanced=False)
        job.param_add('settings', 'other_param',            base_value=None,    title='guess what',   param_type='number',    hidden=False,   advanced=True)
      

    def validate_params(job, changes=None):
        """ optional, override. Call bc version explicitly if you want """
        # changes is a list of param names that have changed. If None, then this is first time val
        bc.builderbase.validate_params(job, changes) # checks that basic types are correct
        pass
            
    def validate_inputs(job, changes=None):
        """ optional, override. Call bc version explicitly if you want """
        particles_connections = bc.com.query(job['input_slot_groups'], lambda g: g['name'] == 'particles')['connections']
        templates_connections = bc.com.query(job['input_slot_groups'], lambda g: g['name'] == 'templates')['connections']
        if len(particles_connections) > 0 and len(templates_connections) > 0:
            if particles_connections[0]['job_uid'] != templates_connections[0]['job_uid']:
                print("BUILDER WARN SELECT2D")
                job.error_input('templates', None, "particles and class averages connected should both be outputs of the same class_2D job!", warning=True) 
        bc.builderbase.validate_inputs(job, changes)

    def regenerate_outputs(job):
        """ required. should have no side effects and should overwrite the outputs based on params and inputs """
        params = bc.com.get_merged_params(job)
        job.clear_outputs()

        if bc.com.is_input_slot_connected(job, 'particles', 'blob'):
            job.add_output_result_group('particles_selected', 'particle', title='Particles selected')
            job.add_output_result('blob', 'particles_selected', 'particle.blob', title='Particle raw data')
            job.add_output_result('alignments2D', 'particles_selected', 'particle.alignments2D', title='Particle 2D alignments')
            job.passthrough_outputs('particles_selected', 'particles') # pass through anything that came with the particles input
        job.add_output_result_group('templates_selected', 'template', title='Templates selected')
        job.add_output_result('blob', 'templates_selected', 'template.blob', title='Template raw data')

        if bc.com.is_input_slot_connected(job, 'particles', 'blob'):
            job.add_output_result_group('particles_excluded', 'particle', title='Particles excluded')
            job.add_output_result('blob', 'particles_excluded', 'particle.blob', title='Particle raw data')
            job.add_output_result('alignments2D', 'particles_excluded', 'particle.alignments2D', title='Particle 2D alignments')
            job.passthrough_outputs('particles_excluded', 'particles') # pass through anything that came with the particles input
        job.add_output_result_group('templates_excluded', 'template', title='Templates excluded')
        job.add_output_result('blob', 'templates_excluded', 'template.blob', title='Template raw data')

        job['ui_tile_height'] = 1
        job['ui_tile_width'] = 2
        pass

    def recompute_resources(job):
        """ required. should have no side effects and should overwrite the resources based on params and inputs """
        pass
