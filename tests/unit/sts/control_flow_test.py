#!/usr/bin/env python

import unittest
import sys
import os
import itertools
from copy import copy
import types
import tempfile

from config.experiment_config_lib import ControllerConfig
from sts.control_flow import Replayer
from sts.topology import FatTree, PatchPanel, MeshTopology
from sts.simulation import Simulation
from pox.lib.recoco.recoco import Scheduler
from sts.entities import Host

sys.path.append(os.path.dirname(__file__) + "/../../..")

class ReplayerTest(unittest.TestCase):
  tmp_basic_superlog = '/tmp/superlog_basic.tmp'
  tmp_controller_superlog = '/tmp/superlog_controller.tmp'
  tmp_dataplane_superlog = '/tmp/superlog_dataplane.tmp'
  tmp_migration_superlog = '/tmp/superlog_migration.tmp'

  # ------------------------------------------ #
  #        Basic Test                          #
  # ------------------------------------------ #

  def write_simple_superlog(self):
    ''' Make sure to delete afterwards! '''
    superlog = open(self.tmp_basic_superlog, 'w')
    e1 = str('''{"dependent_labels": ["e2"], "start_dpid": 8, "class": "LinkFailure",'''
             ''' "start_port_no": 3, "end_dpid": 15, "end_port_no": 2, "label": "e1"}''')
    superlog.write(e1 + '\n')
    e2 = str('''{"dependent_labels": [], "start_dpid": 8, "class": "LinkRecovery",'''
             ''' "start_port_no": 3, "end_dpid": 15, "end_port_no": 2, "label": "e2"}''')
    superlog.write(e2 + '\n')
    e3 = str('''{"dependent_labels": ["e4"], "dpid": 8, "class": "SwitchFailure",'''
             ''' "label": "e3"}''')
    superlog.write(e3 + '\n')
    e4 = str('''{"dependent_labels": [], "dpid": 8, "class": "SwitchRecovery",'''
             ''' "label": "e4"}''')
    superlog.write(e4 + '\n')
    superlog.close()

  def setup_simple_simulation(self):
    controllers = []
    topology_class = FatTree
    topology_params = ""
    patch_panel_class = PatchPanel
    scheduler = Scheduler(daemon=True, useEpoll=False)
    return Simulation(scheduler, controllers, topology_class, topology_params, patch_panel_class)

  def test_basic(self):
    try:
      self.write_simple_superlog()
      replayer = Replayer(self.tmp_basic_superlog)
      simulation = self.setup_simple_simulation()
      replayer.simulate(simulation)
    finally:
      os.unlink(self.tmp_basic_superlog)

  # ------------------------------------------ #
  #        Controller Crash Test               #
  # ------------------------------------------ #

  def write_controller_crash_superlog(self):
    superlog = open(self.tmp_controller_superlog, 'w')
    e1 = str('''{"dependent_labels": ["e2"], "uuid": ["127.0.0.1", 8899],'''
             ''' "class": "ControllerFailure", "label": "e1"}''')
    superlog.write(e1 + '\n')
    e2 = str('''{"dependent_labels": [], "uuid": ["127.0.0.1", 8899],'''
             ''' "class": "ControllerRecovery", "label": "e2"}''')
    superlog.write(e2 + '\n')
    superlog.close()

  def setup_controller_simulation(self):
    cmdline = "./pox/pox.py --no-cli openflow.of_01 --address=__address__ --port=__port__"
    controllers = [ControllerConfig(cmdline=cmdline, address="127.0.0.1", port=8899)]
    topology_class = FatTree
    topology_params = ""
    patch_panel_class = PatchPanel
    scheduler = Scheduler(daemon=True, useEpoll=False)
    return Simulation(scheduler, controllers, topology_class, topology_params, patch_panel_class)

  def test_controller_crash(self):
    try:
      self.write_controller_crash_superlog()
      replayer = Replayer(self.tmp_controller_superlog)
      simulation = self.setup_controller_simulation()
      replayer.simulate(simulation)
    finally:
      os.unlink(self.tmp_controller_superlog)

  # ------------------------------------------ #
  #        Dataplane Trace Test                #
  # ------------------------------------------ #

  def write_dataplane_trace_superlog(self):
    superlog = open(self.tmp_dataplane_superlog, 'w')
    e1 = str('''{"dependent_labels": [],  "class": "TrafficInjection",'''
             ''' "label": "e1"}''')
    superlog.write(e1 + '\n')
    e2 = str('''{"dependent_labels": [],  "class": "TrafficInjection",'''
             ''' "label": "e2"}''')
    superlog.write(e2 + '\n')
    superlog.close()

  def setup_dataplane_simulation(self):
    controllers = []
    topology_class = MeshTopology
    topology_params = "num_switches=2"
    patch_panel_class = PatchPanel
    scheduler = Scheduler(daemon=True, useEpoll=False)
    dataplane_trace_path = "./dataplane_traces/ping_pong_same_subnet.trace"
    return Simulation(scheduler, controllers, topology_class, topology_params,
                      patch_panel_class, dataplane_trace_path=dataplane_trace_path)

  def test_dataplane_injection(self):
    try:
      self.write_dataplane_trace_superlog()
      replayer = Replayer(self.tmp_dataplane_superlog)
      simulation = self.setup_dataplane_simulation()
      replayer.simulate(simulation)
    finally:
      os.unlink(self.tmp_dataplane_superlog)

  # ------------------------------------------ #
  #        Host Migration Test                 #
  # ------------------------------------------ #

  def write_migration_superlog(self):
    superlog = open(self.tmp_migration_superlog, 'w')
    e1 = str('''{"dependent_labels": ["e2"], "old_ingress_dpid": 7, "class": "HostMigration",'''
             ''' "old_ingress_port_no": 1, "new_ingress_dpid": 8, '''
             ''' "new_ingress_port_no": 99, "label": "e1"}''')
    superlog.write(e1 + '\n')
    e2 = str('''{"dependent_labels": [], "old_ingress_dpid": 8, "class": "HostMigration",'''
             ''' "old_ingress_port_no": 99, "new_ingress_dpid": 7, '''
             ''' "new_ingress_port_no": 101, "label": "e2"}''')
    superlog.write(e2 + '\n')
    superlog.close()

  def setup_migration_simulation(self):
    controllers = []
    topology_class = FatTree
    topology_params = ""
    patch_panel_class = PatchPanel
    scheduler = Scheduler(daemon=True, useEpoll=False)
    return Simulation(scheduler, controllers, topology_class, topology_params,
                      patch_panel_class)

  def test_migration(self):
    try:
      self.write_migration_superlog()
      replayer = Replayer(self.tmp_migration_superlog)
      simulation = self.setup_migration_simulation()
      replayer.simulate(simulation)
      latest_switch = simulation.topology.get_switch(7)
      latest_port = latest_switch.ports[101]
      host = simulation.topology.get_connected_port(latest_switch,
                                                    latest_port)
      self.assertTrue(type(host) == Host)
    finally:
      os.unlink(self.tmp_migration_superlog)

if __name__ == '__main__':
  unittest.main()
