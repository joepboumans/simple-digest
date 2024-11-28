#!/usr/bin/python3
import logging
from collections import namedtuple
from math import radians
import random

from ptf import config
import ptf.testutils as testutils
from p4testutils.misc_utils import *
from bfruntime_client_base_tests import BfRuntimeTest
import bfrt_grpc.bfruntime_pb2 as bfruntime_pb2
import bfrt_grpc.client as gc

swports = get_sw_ports()
name = 'simple_digest'
logger = logging.getLogger(name)

if not len(logger.handlers):
    sh = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s - %(name)s - %(funcName)s]: %(message)s')
    sh.setFormatter(formatter)
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)

class SimpleDigest(BfRuntimeTest):
    def setUp(self):
        logger.info("Starting setup")
        client_id = 0
        BfRuntimeTest.setUp(self, client_id)
        logger.info("\tfinished BfRuntimeSetup")

        self.bfrt_info = self.interface.bfrt_info_get(name)
        self.forward = self.bfrt_info.table_get("forward")
        # self.forward.info.key_field_annotation_add("dst_addr", "ipv4")
        self.learn_filter = self.bfrt_info.learn_get("digest")
        self.learn_filter.info.data_field_annotation_add("src_addr", "ipv4")
        self.learn_filter.info.data_field_annotation_add("dst_addr", "ipv4")
        self.target = gc.Target(device_id=0, pipe_id=0xffff)
        logger.info("Finished setup")

    def runTest(self):
        logger.info("Start testing")
        # ig_port = swports[0]
        # eg_port = swports[random.randint(0, len(swports) - 1)]
        ig_port = 132
        eg_port = 148
        target = self.target
        forward = self.forward
        learn_filter = self.learn_filter

        ''' TC:1 Setting up forward'''
        logger.info("Populating forward table...")
        num_entries = 1000
        seed = 1001
        ip_list = self.generate_random_ip_list(num_entries, seed)

        logger.debug(f"\tforward - inserting table entry with port {ig_port} and dst_port {eg_port}")
        key = forward.make_key([gc.KeyTuple('ig_intr_md.ingress_port', ig_port)])
        data = forward.make_data([gc.DataTuple('dst_port', eg_port)], "SwitchIngress.hit")
        forward.entry_add(target, [key], [data])

        # for ip_entry in ip_list:
        #     dst_addr = getattr(ip_entry, "ip")
        #     logger.debug(f"\tforward - inserting table entry with port {ig_port} and dst_addr {dst_addr}")
        #     key = forward.make_key([gc.keytuple('dst_addr', dst_addr)])
        #     data = forward.make_data([gc.datatuple('port', ig_port)], "switchingress.hit")

            # forward.entry_add(target, [key], [data])


        logger.info("Adding entries to forward table")
        ''' TC:2 Send, receive and verify packets'''
        for ip_entry in ip_list:
            dst_addr = getattr(ip_entry, "ip")
            pkt_in = testutils.simple_ip_packet(ip_dst=dst_addr)
            logger.info("Sending simple packet to switch")
            testutils.send_packet(self, ig_port, pkt_in)
            logger.info("Verifying simple packet has been correct...")
            testutils.verify_packet(self, pkt_in, ig_port)
            logger.info("..packet received correctly")

        ''' TC:3 Get data from the digest'''
        total_recv = 0
        digest = self.interface.digest_get()
        while(digest != None):
            data_list = learn_filter.make_data_list(digest)
            logger.info(f"Received {len(data_list)} entries from the digest")
            total_recv += len(data_list)
            for data in data_list:
                data_dict = data.to_dict()
                recv_dst_addr = data_dict["dst_addr"]
                recv_src_addr = data_dict["src_addr"]
                logger.info(f"{recv_src_addr = }:{recv_dst_addr = }")
            try:
                digest = self.interface.digest_get()
            except:
                break;
        assert(total_recv == num_entries)

    def tearDown(self):
        logger.info("Tearing down test")
        self.forward.entry_del(self.target)
        BfRuntimeTest.tearDown(self)
