# Copyright 2011-2013 Colin Scott
# Copyright 2011-2013 Andreas Wundsam
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from pox.lib.packet.ethernet import *
from pox.lib.packet.ipv4 import *
from pox.lib.packet.icmp import *
from sts.dataplane_traces.trace import DataplaneEvent
import random
import itertools

class TrafficGenerator (object):
  """
  Generate sensible randomly generated (openflow) events
  """

  def __init__(self, random=random.Random()):
    self.random = random
    self.topology = None
    self._packet_generators = {
      "icmp_ping" : self.icmp_ping
    }

  def set_topology(self, topology):
    self.topology = topology

  def icmp_ping(self, src_interface, dest_interface, payload_content=None):
    e = ethernet()
    e.src = src_interface.hw_addr
    e.dst = dest_interface.hw_addr
    e.type = ethernet.IP_TYPE
    i = ipv4()
    i.protocol = ipv4.ICMP_PROTOCOL
    i.srcip = random.choice(src_interface.ips)
    i.dstip = random.choice(dest_interface.ips)
    ping = icmp()
    ping.type = random.choice([TYPE_ECHO_REQUEST, TYPE_ECHO_REPLY])
    if payload_content == "" or payload_content is None:
      payload_content = "Ping" * 12
    ping.payload = payload_content
    i.payload = ping
    e.payload = i
    return e

  def generate_and_inject(self, packet_type, src_host=None, dest_host=None,
                          send_to_self=False, payload_content=None):
    if packet_type not in self._packet_generators:
      raise AttributeError("Unknown event type %s" % str(packet_type))
    if self.topology is None:
      raise RuntimeError("TrafficGenerator needs access to topology")

    if src_host is None:
      src_host = self._choose_host(self.topology.hosts) 
    src_host = self._validate_host(src_host)
    src_interface = self.random.choice(src_host.interfaces)
  
    if send_to_self:
      dest_host = src_host
      dest_interface = src_interface
    else:
      if dest_host is None:
        dest_host = self._choose_host([h for h in self.topology.hosts if h != src_host])
      dest_host = self._validate_host(dest_host)
      dest_interface = self.random.choice(dest_host.interfaces)
    
    packet = self._packet_generators[packet_type](src_interface, dest_interface,
                                                  payload_content=payload_content)
    src_host.send(src_interface, packet)
    return DataplaneEvent(src_interface, packet)

  def _choose_host(self, hosts):
    if len(hosts) == 0:
      raise RuntimeError("No host to choose from!")  
    return self.random.choice(hosts)

  def _validate_host(self, host):
    if host in self.topology.hid2host.keys():
      host = self.topology.hid2host[host]
    if host not in self.topology.hosts:
      raise RuntimeError("Unknown host: %s" % (str(host)))
    if len(host.interfaces) == 0:
      raise RuntimeError("No interfaces to choose from on host %s!" % (str(host)))
    return host
