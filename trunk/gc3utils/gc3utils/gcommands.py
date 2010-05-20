#!/usr/bin/env python
"""
Implementation of the `gcli` command-line front-ends.
"""
__version__="0.4"

__author__="Sergio Maffioletti <sergio.maffioletti@gc3.uzh.ch>, Riccardo Murri <riccardo.murri@uzh.ch>"
__date__="01 May 2010"
__copyright__="Copyright (c) 2009,2010 Grid Computing Competence Center, University of Zurich"

__docformat__='reStructuredText'


import sys
import os
import ConfigParser
from optparse import OptionParser

import gc3utils
import gc3utils.Application
import gc3utils.ArcLRMS
import gc3utils.Default
from gc3utils.Exceptions import *
import gc3utils.Job
import gc3utils.Resource
import gc3utils.SshLRMS
import gc3utils.gcli
import gc3utils.utils


# defaults - XXX: do they belong in ../gcli.py instead?
_homedir = os.path.expandvars('$HOME')
_rcdir = _homedir + "/.gc3"
_default_config_file_location = _rcdir + "/config"
_default_joblist_file = _rcdir + "/.joblist"
_default_joblist_lock = _rcdir + "/.joblist_lock"
_default_job_folder_location = os.getcwd()
_default_wait_time = 3 # XXX: does it really make sense to have a default wall-clock time??
_default_log_file = _homedir + "/.gc3utils.log"


def _get_gcli(options, config_file_path = _default_config_file_location):
    """
    Return a `gc3utils.gcli.Gcli` instance configured by parsing
    the configuration file located at `config_file_path`.
    """
    try:
        (default,resources) = gc3utils.utils.import_config(config_file_path,options)

        gc3utils.log.debug('Creating instance of Gcli')
        return gc3utils.gcli.Gcli(default, resources)
    except:
        gc3utils.log.debug("Failed loading config file from '%s'", config_file_path)
        raise

#====== Main ========

def gsub(*args, **kw):
    """The `gsub` command."""
    # Parse command line arguments
    parser = OptionParser(usage="%prog [options] APPLICATION INPUTFILE")
    parser.add_option("-v", action="count", dest="verbosity", default=0, help="Set verbosity level")
    parser.add_option("-r", "--resource", action="store", dest="resource_name", metavar="STRING", default=None, help='Select resource destination')
    parser.add_option("-d", "--jobdir", action="store", dest="job_local_dir", metavar="STRING", default=gc3utils.Default.JOB_FOLDER_LOCATION, help='Select job local folder location')
    parser.add_option("-c", "--cores", action="store", dest="ncores", metavar="INT", default=0, help='Set number of requested cores')
    parser.add_option("-m", "--memory", action="store", dest="memory_per_core", metavar="INT", default=0, help='Set memory per core request (GB)')
    parser.add_option("-w", "--walltime", action="store", dest="walltime", metavar="INT", default=0, help='Set requested walltime (hours)')
    parser.add_option("-a", "--args", action="store", dest="application_arguments", metavar="STRING", default=None, help='Application arguments')

    (options, args) = parser.parse_args(list(args))
    gc3utils.utils.configure_logger(options.verbosity, _default_log_file)

    if len(args) != 2:
        raise InvalidUsage('Wrong number of arguments: this commands expects exactly two.')

    application_tag = args[0]

    # check input file
    if ( not gc3utils.utils.check_inputfile(args[1]) ):
        gc3utils.log.critical('Cannot find input file: '+args[1])
        raise Exception('invalid input-file argument')
    input_file_name = args[1]

    if not os.path.isabs(input_file_name):
        input_file_name = os.path.realpath(input_file_name)

    # Create Application obj
    application = gc3utils.Application.Application(
        application_tag=application_tag,
        input_file_name=input_file_name,
        job_local_dir=options.job_local_dir,
        requested_memory=options.memory_per_core,
        requested_cores=options.ncores,
        requestd_resource=options.resource_name,
        requested_walltime=options.walltime,
        application_arguments=options.application_arguments
        )

    if not application.is_valid():
        raise Exception('Failed creating application object')

    _gcli = _get_gcli(options)
    job = _gcli.gsub(application)

    if job.is_valid():
        # create persistanc of filesystem
        # gc3utils.utils.create_job_on_filesystem(application_obj.job_local_dir,job.unique_token)
        gc3utils.utils.persist_job_filesystem(job)
        gc3utils.utils.display_job_status([job],0)
        return 0
    else:
        raise Exception('Job object not valid')


def grid_credential_renew(*args, **kw):                                        
    parser = OptionParser(usage="Usage: %prog [options] USERNAME")
    parser.add_option("-v", action="count", dest="verbosity", default=0, help="Set verbosity level")
    (options, args) = parser.parse_args(list(args))
    gc3utils.utils.configure_logger(options.verbosity, _default_log_file)
    
    try:
        _aai_username = args[0]
    except IndexError:
        raise InvalidUsage("Missing required argument USERNAME; this command requires your AAI/SWITCH username.")
        
    gc3utils.log.debug('Checking grid credential')
    _gcli = _get_gcli(options)
    if not _gcli.check_authentication(gc3utils.Default.SMSCG_AUTHENTICATION):
        return _gcli.enable_authentication(gc3utils.Default.SMSCG_AUTHENTICATION)
    else:
        return True


def gstat(*args, **kw):                        
    """The `gstat` command."""
    # FIXME: should accept list of JOBIDs and return status of all of them!
    parser = OptionParser(usage="Usage: %prog [options] JOBID")
    parser.add_option("-v", action="count", dest="verbosity", default=0, help="Set verbosity level")
    parser.add_option("-s", action="store", dest="job_status_filter", metavar="INT", default=0, help="only select jobs whose status is INT")
    (options, args) = parser.parse_args(list(args))
    gc3utils.utils.configure_logger(options.verbosity, _default_log_file)

    try:
        _gcli = _get_gcli(options)
        if len(args) == 0:
            job_list = _gcli.gstat(None)
        elif len(args) == 1:
            unique_token = args[0]
#            if not os.path.isdir(unique_token):
#                raise UniqueTokenError("Invalid JOBID: '%s' is not a job status directory." % unique_token)
            # job_list = _gcli.gstat(gc3utils.utils.get_job_from_filesystem(unique_token,default.job_file))
            job_list = _gcli.gstat(gc3utils.utils.get_job(unique_token))
        else:
            raise InvalidUsage("This command requires either one argument or no arguments at all.")
    except Exception, x:
        # FIXME: this `if` can go away once all exceptions do the logging in their ctor.
        if isinstance(x, InvalidUsage):
            raise
        else:
            gc3utils.log.critical('Failed retrieving job status')
            raise

    # Check validity of returned list
    for _job in job_list:
        if not _job.is_valid():
            gc3utils.log.error('Returned job not valid. Removing from list')
            job_list.remove(_job)
        else:
            gc3utils.utils.persist_job_filesystem(_job)
                                        
    try:
        # Print result
        gc3utils.utils.display_job_status(job_list,int(options.job_status_filter))
    except:
        gc3utils.log.error('Failed displaying job status results')
        raise

    return 0


def gget(*args, **kw):
    """ The `gget` command."""
    parser = OptionParser(usage="Usage: %prog [options] JOBID")
    parser.add_option("-v", action="count", dest="verbosity", default=0, help="Set verbosity level")
    (options, args) = parser.parse_args(list(args))
    gc3utils.utils.configure_logger(options.verbosity, _default_log_file)
    
    # FIXME: should take possibly a list of JOBIDs and get files for all of them
    if len(args) != 1:
        raise InvalidUsage("This command requires either one argument (the JOBID) or none.")
    unique_token = args[0]

    _gcli = _get_gcli(options)
    # FIXME: gget should raise exception when something goes wrong; does it indeed?
    job_obj = gc3utils.utils.get_job(unique_token)

    gc3utils.log.debug('job status [%d]',job_obj.status)
    
    if not job_obj.status == gc3utils.Job.JOB_STATE_COMPLETED and (job_obj.status == gc3utils.Job.JOB_STATE_FINISHED or job_obj.status == gc3utils.Job.JOB_STATE_FAILED):
        gc3utils.log.debug('running gcli.gget')
        job_obj = _gcli.gget(job_obj)
        #utils.mark_completed_job(job_obj)

    if job_obj.status == gc3utils.Job.JOB_STATE_COMPLETED:
        sys.stdout.write('Job results successfully retrieved in [ '+job_obj.download_dir+' ]\n')
        sys.stdout.flush
    else:
        raise Exception("job status not COMPLETED")
        #raise
                    

#    retval = _gcli.gget(unique_token)
#    sys.stdout.write('Job results successfully retrieved in directory: '+unique_token+'\n')
#    sys.stdout.flush()


def gkill(*args, **kw):
    """The `gkill` command."""
    parser = OptionParser(usage="%prog [options] unique_token")
    parser.add_option("-v", action="count", dest="verbosity", default=0, help="Set verbosity level")
    (options, args) = parser.parse_args(list(args))
    gc3utils.utils.configure_logger(options.verbosity, _default_log_file)

    shortview = True

    if len(args) != 1:
        raise InvalidUsage("This command expects exactly one argument.")
    unique_token = args[0]

    retval = gcli.gkill(unique_token)
    if (not retval):
        sys.stdout.write('Sent request to kill job ' + unique_token)
        sys.stdout.write('It may take a few moments for the job to finish.')
        sys.stdout.flush()
    else:
        raise Exception("gkill terminated")


def glist(*args, **kw):
    """The `glist` command."""
    parser = OptionParser(usage="Usage: %prog [options] resource_name")
    parser.add_option("-v", action="count", dest="verbosity", default=0, help="Set verbosity level")
    parser.add_option("-s", "--short", action="store_true", dest="shortview", help="Short view.")
    parser.add_option("-l", "--long", action="store_false", dest="shortview", help="Long view.")
    (options, args) = parser.parse_args(list(args))
    gc3utils.utils.configure_logger(options.verbosity, _default_log_file)

    # FIXME: should take possibly a list of resource IDs and get files for all of them
    if len(args) != 1:
        raise InvalidUsage("This command requires exactly one argument: the resource name.")
    resource_name = args[0]

    _gcli = _get_gcli(options)
    # FIXME: gcli.glist should throw exception, we should not check return value here
    (retval,resource_object) = _gcli.glist(resource_name)
    if (not retval):
        if resource_object.__dict__.has_key("resource_name"):
            sys.stdout.write('Resource Name: '+resource_object.__dict__["resource_name"]+'\n')
        if resource_object.__dict__.has_key("total_slots"):
            sys.stdout.write('Total cores: '+str(resource_object.__dict__["total_slots"])+'\n')
        if resource_object.__dict__.has_key("total_runnings"):
            sys.stdout.write('Total runnings: '+str(resource_object.__dict__["total_runnings"])+'\n')
        if resource_object.__dict__.has_key("total_queued"):
            sys.stdout.write('Total queued: '+str(resource_object.__dict__["total_queued"])+'\n')
        if resource_object.__dict__.has_key("memory_per_core"):
            sys.stdout.write('Memory per core: '+str(resource_object.__dict__["memory_per_core"])+'\n')
        sys.stdout.flush()
    else:
        raise Exception("glist terminated")
