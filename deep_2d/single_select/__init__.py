## ---------------------------------------------------------------------------
##    Copyright (c) 2019 Structura Biotechnology Inc. All rights reserved. 
##         Do not reproduce or redistribute, in whole or in part.
##      Use of this code is permitted only under licence from Structura.
##                   Contact us at info@structura.bio.
## ---------------------------------------------------------------------------

from . import build
from .. import jobregister

jobregister.register(
        job_type           = 'single_select', 
        title              = 'Single select 2D', 
        shorttitle         = 'single', 
        desc               = 'Select one class.', 
        develop_only       = False,
        builder_class      = build.builder, 
        run_module_name    = 'single_select.run', 
        run_function_name  = 'run',
        is_interactive     = False,
)
