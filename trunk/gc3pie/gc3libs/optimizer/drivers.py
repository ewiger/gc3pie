#! /usr/bin/env python
#
"""
Drivers to perform global optimization.

Global optimizations can be performed sequentially on
a local machine using :class:`LocalDriver`.
To make use of parallelization, :class:`GridDriver` allows submission of
jobs to gc3pie ressources.

Drivers use an algorithm instance that conforms to
:class:`gc3libs.optimizer.EvolutionaryAlgorithm` to generate new
populations.
"""
# Copyright (C) 2011, 2012, 2013 University of Zurich. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
__version__ = '$Revision$'
__author__ = 'Benjamin Jonen <benjamin.jonen@bf.uzh.ch>'
__docformat__ = 'reStructuredText'

import os
import sys
import logging
import datetime

import numpy as np
from prettytable import PrettyTable

import gc3libs
from gc3libs.workflow import SequentialTaskCollection, ParallelTaskCollection



class LocalDriver(object):
    """Drives an optimization using `opt_algorithm` on the local machine.

    The user-supplied :func:`target_fun` computes target values for the
    populations generated by `opt_algorithm`.

    :param opt_algorithm: Evolutionary algorithm instance that conforms to
                         :class:`gc3libs.optimizer.EvolutionaryAlgorithm`.
    :param target_fn: Function to evaluate a population and return the corresponding values.
    :param path_to_stage_dir: Directory in which to perform the optimization.
    :param cur_pop_file: Filename under which the population is stored in the
                         current iteration dir. The population is discarded
                         if no file is specified.
    :param logger: Configured logger to use.
    :param str fmt: ``%``-format string to use (e.g., ``%12.8f``) to print values at each step of the algorithm.  If `None` (default), this verbose report is not generated, as it might be time-consuming for large population sizes.
    """

    def __init__(self, opt_algorithm, target_fn, path_to_stage_dir = os.getcwd(), cur_pop_file=None, logger=None, fmt=None):
        self.path_to_stage_dir = path_to_stage_dir
        self.opt_algorithm = opt_algorithm
        self.target_fn = target_fn
        self.cur_pop_file = cur_pop_file
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger('gc3.gc3libs')
        self.fmt = fmt


    def de_opt(self):
        '''
        Drives optimization until convergence or `itermax` is reached.
        '''
        self.logger.debug('entering de_opt')
        new_pop = self.opt_algorithm.pop
        has_converged = False
        while not has_converged and self.opt_algorithm.cur_iter <= self.opt_algorithm.itermax:
            # Save current population
            self.iteration_folder = os.path.join(self.path_to_stage_dir, 'iter_' + str(self.opt_algorithm.cur_iter))
            if self.cur_pop_file:
                if not os.path.isdir(self.iteration_folder):
                    os.mkdir(self.iteration_folder)
                np.savetxt(os.path.join(self.iteration_folder, self.cur_pop_file),
                           new_pop, delimiter = ' ')
            # EVALUATE TARGET #
            new_vals = self.target_fn(new_pop)
            if self.fmt:
                self.logger.info(
                    "*** Population (X's) and values (Y) at iteration %d: ***",
                    self.opt_algorithm.cur_iter)
                tb = PrettyTable()
                for i in range(new_pop.shape[1]):
                    tb.add_column(("X_%d" % i), [(self.fmt % x) for x in new_pop[:,i]])
                tb.add_column("Y", [(self.fmt % y) for y in new_vals])
                for line in tb.get_string().split('\n'):
                    self.logger.info(line)
            #if __debug__:
                #self.logger.debug('x -> f(x)')
                #for x, fx in zip(new_pop, new_vals):
                    #self.logger.debug('%s -> %s' % (x.tolist(), fx))
            self.opt_algorithm.update_opt_state(new_pop, new_vals)
            # create output
            has_converged = self.opt_algorithm.has_converged()
            new_pop = self.opt_algorithm.evolve()
        self.logger.debug('exiting ' + __name__)



class GridDriver(SequentialTaskCollection):
    """Drives an optimization using `opt_algorithm` on the grid.

    At each iteration an instance of :class:`ComputeTargetVals` uses
    :func:`task_constructor` to generate :class:`gc3libs.Application` instances to be
    executed in parallel. When all jobs are complete, the output is analyzed
    with the user-supplied function :func:`extract_value_fn`. This function
    returns the function value for all analyzed input vectors.

    :param str jobname:       string that labels this optimization case.

    :param path_to_stage_dir: directory in which to perform the optimization.

    :param opt_algorithm:    Evolutionary algorithm instance that conforms
                             to :class:`gc3libs.optimizer.EvolutionaryAlgorithm`.

    :param task_constructor: A function that takes a list of x vectors
                             and the path to the current iteration
                             directory, and returns Application
                             instances that can be executed on the
                             grid.

    :param extract_value_fn: Takes an `Application`:class: instance returns
                             the function value computed in that task.
                             The default implementation just looks for a
                             `.value` attribute on the application instance.

    :param cur_pop_file:     Filename under which the population is stored
                             in the current iteration dir. The
                             population is discarded if no file is
                             specified.

    """

    def __init__(self, jobname = '', path_to_stage_dir = '',
                 opt_algorithm = None, task_constructor = None,
                 extract_value_fn = (lambda app: app.value),
                 cur_pop_file = '',
                 **extra_args ):

        gc3libs.log.debug('entering GridOptimizer.__init__')

        # Set up initial variables and set the correct methods.
        self.jobname = jobname
        self.path_to_stage_dir = path_to_stage_dir
        self.opt_algorithm = opt_algorithm
        self.extract_value_fn = extract_value_fn
        self.task_constructor = task_constructor
        self.cur_pop_file = cur_pop_file
        self.extra_args = extra_args

        self.new_pop = self.opt_algorithm.pop
        initial_task = ComputeTargetVals(
            self.opt_algorithm.pop, self.jobname, self.opt_algorithm.cur_iter,
            path_to_stage_dir, self.cur_pop_file, task_constructor)

        SequentialTaskCollection.__init__(self,  [initial_task], **extra_args)

    def next(self, done):
        gc3libs.log.debug('entering GridOptimizer.next(%d)', done)

        # feed back results from the evaluation just completed
        new_pop = self.new_pop
        new_vals = [ self.extract_value_fn(task) for task in self.tasks[done].tasks ]
        self.opt_algorithm.update_opt_state(new_pop, new_vals)

        self.changed = True

        if self.opt_algorithm.cur_iter > self.opt_algorithm.itermax:
            # maximum number of iterations exceeded
            # XXX: what return code is appropriate here?
            self.execution.exitcode = os.EX_TEMPFAIL
            return gc3libs.Run.State.TERMINATED

        # still within allowed number of iterations, check convergence
        if self.opt_algorithm.has_converged():
            # report success of sequential task
            self.execution.returncode = 0
            return gc3libs.Run.State.TERMINATED
        else:
            # prepare next evaluation
            self.new_pop = self.opt_algorithm.evolve()
            self.add(
                    ComputeTargetVals(
                    self.new_pop, self.jobname, self.opt_algorithm.cur_iter,
                    self.path_to_stage_dir, self.cur_pop_file, self.task_constructor))
            return gc3libs.Run.State.RUNNING


    def __str__(self):
        return self.jobname

    # Adjustments for pickling
    # def __getstate__(self):
    #     state = Task.__getstate__(self)
    #     # Check that there are no functions in state.
    #     #for attr in ['opt_algorithm']:
    #         ## 'task_constructor', 'extract_value_fn', 'tasks',
    #         #del state[attr]
    #    # state = None
    #     return state

    # def __setstate__(self, state):
    #     # restore _grid, etc.
    #     Task.__setstate__(self, state)
    #     # restore loggers
    #     #self._setup_logging()

class ComputeTargetVals(ParallelTaskCollection):
    """
    :class:`gc3libs.workflow.ParallelTaskCollection` to evaluate the current
    `pop` using the user-supplied :func:`task_constructor`.

    :param list pop: Population to evaluate.

    :param str jobname: Name of :class:`GridDriver` instance driving the
     optimization.

    :param int iteration: Current iteration number.

    :param str path_to_stage_dir: Path to directory in which optimization takes
                                  place.

    :param str cur_pop_file: Filename under which the population is stored in the
    current iteration dir. The population is discarded if no file is
    specified. :param task_constructor: Takes a list of x vectors and the
    path to the current iteration directory. Returns Application instances
    that can be executed on the grid.
    """

    def __str__(self):
        return self.jobname


    def __init__(self, pop, jobname, iteration, path_to_stage_dir,
                 cur_pop_file, task_constructor, **extra_args):

        gc3libs.log.debug('entering ComputeTargetVals.__init__')

        # Set up initial variables and set the correct methods.
        self.jobname = jobname + '-' + 'compute_target_vals' + '-' + str(iteration)
        self.iteration = iteration

        self.path_to_stage_dir = path_to_stage_dir
        # ComputeTargetVals produces no output.
        # But attribute needs to be specified.
        self.output_dir = path_to_stage_dir
        self.cur_pop_file = cur_pop_file
        self.verbosity = 'DEBUG'
        self.extra_args = extra_args

        # Log activity
        cDate = datetime.date.today()
        cTime = datetime.datetime.time(datetime.datetime.now())
        date_string = '%04d--%02d--%02d--%02d--%02d--%02d' % (cDate.year,
                                                cDate.month, cDate.day, cTime.hour,
                                                cTime.minute, cTime.second)
        gc3libs.log.debug('Establishing parallel task on %s', date_string)

        # Enter an iteration specific folder
        self.iteration_folder = os.path.join(self.path_to_stage_dir,
                                            'Iteration-' + str(self.iteration))
        try:
            os.mkdir(self.iteration_folder)
        except OSError:
            print '%s already exists' % self.iteration_folder

        # save pop to file
        if cur_pop_file:
            np.savetxt(os.path.join(self.iteration_folder, cur_pop_file),
                       pop, delimiter = ' ')

        self.tasks = [
            task_constructor(pop_mem, self.iteration_folder) for pop_mem in pop
        ]
        ParallelTaskCollection.__init__(self, self.tasks, **extra_args)
